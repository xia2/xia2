from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

import numpy as np

from cctbx import sgtbx, uctbx

from xia2.Handlers.Streams import banner

xia2_logger = logging.getLogger(__name__)

import concurrent.futures

from dials.array_family import flex
from dials.util import tabulate
from dials.util.image_grouping import ParsedYAML
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_definitions import FilePair, ReductionParams
from xia2.Modules.SSX.data_reduction_programs import (
    CrystalsDict,
    MergeResult,
    ProcessingBatch,
    assess_for_indexing_ambiguities,
    cosym_reindex,
    create_merge_group_summary,
    filter_,
    merge,
    parallel_cosym,
    prepare_scaled_array,
    scale_parallel_batches,
    split_integrated_data,
)
from xia2.Modules.SSX.yml_handling import (
    apply_scaled_array_to_all_files,
    dose_series_repeat_to_groupings,
    yml_to_merged_filesdict,
)


def inspect_directories(
    directories_to_process: List[Path], validate: bool = False
) -> List[FilePair]:
    """
    Inspect the directories and match up integrated .expt and .refl files
    by name.
    """
    new_data: List[FilePair] = []
    for d in directories_to_process:
        expts_this, refls_this = ([], [])
        for file_ in list(d.glob("integrated*.expt")):
            expts_this.append(file_)
        for file_ in list(d.glob("integrated*.refl")):
            refls_this.append(file_)
        if len(expts_this) != len(refls_this):
            raise ValueError(
                f"Unequal number of experiments ({len(expts_this)}) "
                + f"and reflections ({len(refls_this)}) files found in {d}"
            )
        for expt, refl in zip(sorted(expts_this), sorted(refls_this)):
            fp = FilePair(expt, refl)
            if validate:
                try:
                    fp.validate()
                except AssertionError:
                    raise ValueError(
                        f"Files {fp.expt} & {fp.refl} not consistent, please check input data"
                    )
            new_data.append(fp)
        if not expts_this:
            xia2_logger.warning(f"No integrated data files found in {str(d)}")
    if not new_data:
        raise ValueError("No integrated datafiles found in directories")
    return new_data


def validate(expt: Path, refl: Path):
    fp = FilePair(expt, refl)
    try:
        fp.validate()
    except AssertionError:
        raise ValueError(
            f"Files {fp.expt} & {fp.refl} not consistent, please check input data"
        )
    else:
        return fp


def inspect_files(
    reflection_files: List[Path], experiment_files: List[Path], validate: bool = False
) -> List[FilePair]:
    """Inspect the input data, matching by the order of input."""
    new_data: List[FilePair] = []
    for refl_file, expt_file in zip(reflection_files, experiment_files):
        fp = FilePair(expt_file, refl_file)
        fp.check()
        if validate:
            try:
                fp.validate()
            except AssertionError:
                raise ValueError(
                    f"Files {fp.expt} & {fp.refl} not consistent, please check input order"
                )
        new_data.append(fp)
    return new_data


def record_merge_files(merge_results_dict):
    for mergeresult in merge_results_dict.values():
        FileHandler.record_data_file(mergeresult.merge_file)
        FileHandler.record_log_file(mergeresult.logfile.stem, mergeresult.logfile)
        FileHandler.record_more_log_file(
            mergeresult.jsonfile.stem, mergeresult.jsonfile
        )
        FileHandler.record_html_file(mergeresult.htmlfile.stem, mergeresult.htmlfile)


class BaseDataReduction(object):

    _no_input_error_msg = (
        "No input data, (experiments+reflections files or integrated directories)\n"
        + "have been found in the input. Please provide at least some integrated/scaled data or\n"
        + "a directory of data integrated with xia2.ssx/dials.ssx_integrate\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated/scaled data files.\n"
        + " - Use steps=merge to remerge already scaled data\n"
    )

    def __init__(
        self,
        main_directory: Path,
        data: List[FilePair],
        reduction_params,
    ):

        self._main_directory: Path = main_directory
        self._reduction_params: ReductionParams = reduction_params

        self._data_reduction_wd: Path = self._main_directory / "data_reduction"
        self._filter_wd = self._data_reduction_wd / "prefilter"
        self._reindex_wd = self._data_reduction_wd / "reindex"
        self._scale_wd = self._data_reduction_wd / "scale"
        self._merge_wd = self._data_reduction_wd / "merge"

        self._integrated_data: List[FilePair] = []
        self._filtered_batches_to_process: List[ProcessingBatch] = []
        # self._files_to_scale: List[FilePair] = []
        self._batches_to_scale: List[ProcessingBatch] = []
        self._files_to_merge: List[FilePair] = []

        if not data:
            raise ValueError(self._no_input_error_msg)

        # set up the directory structures
        if not Path.is_dir(self._data_reduction_wd):
            Path.mkdir(self._data_reduction_wd)

        if "scale" in self._reduction_params.steps:
            self._integrated_data.extend(data)
            if not Path(self._scale_wd).is_dir():
                Path.mkdir(self._scale_wd)
        else:
            # just merge
            self._files_to_merge.extend(data)

        if not Path(self._merge_wd).is_dir():
            Path.mkdir(self._merge_wd)

        self._parsed_grouping = None
        if self._reduction_params.grouping or self._reduction_params.dose_series_repeat:
            if self._reduction_params.dose_series_repeat:
                expts = []
                for fp in self._integrated_data + self._files_to_merge:
                    expts.append(load.experiment_list(fp.expt, check_format=False))
                try:
                    self._parsed_grouping = dose_series_repeat_to_groupings(
                        expts, self._reduction_params.dose_series_repeat
                    )
                except Exception as e:
                    xia2_logger.warning(
                        "Unable to automatically deduce groupings from input data and dose_series_repeat option."
                        + f"\nSpecific exception encountered: {e}"
                    )
                else:
                    xia2_logger.info(
                        f"Assigning dose groups using: image_no modulo {self._reduction_params.dose_series_repeat} = dose_point"
                    )
            if not self._parsed_grouping and self._reduction_params.grouping:
                try:
                    self._parsed_grouping = ParsedYAML(self._reduction_params.grouping)
                except Exception as e:
                    xia2_logger.warning(
                        f"Error parsing {self._reduction_params.grouping}\n"
                        + f"as a valid grouping yaml file, check input. Exception encountered:\n{e}"
                    )

    @classmethod
    def from_directories(
        cls,
        main_directory: Path,
        directories_to_process: List[Path],
        reduction_params,
        validate=False,
    ):
        new_data = inspect_directories(directories_to_process, validate)
        return cls(main_directory, new_data, reduction_params)

    @classmethod
    def from_files(
        cls,
        main_directory: Path,
        reflection_files: List[Path],
        experiment_files: List[Path],
        reduction_params,
        validate=False,
    ):
        # load and check all integrated files
        try:
            new_data = inspect_files(reflection_files, experiment_files, validate)
        except FileNotFoundError as e:
            raise ValueError(e)
        return cls(main_directory, new_data, reduction_params)

    def run(self) -> None:

        if not self._integrated_data:
            xia2_logger.notice(banner("Merging"))  # type: ignore
            self._merge()
            return

        # first filter the data based on unit cells.
        xia2_logger.notice(banner("Filtering"))  # type: ignore
        good_crystals_data, best_unit_cell, space_group = self._filter()

        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group,
            best_unit_cell,
            self._reduction_params.lattice_symmetry_max_delta,
        )

        if sym_requires_reindex:
            # split good crystals based on batchsize
            xia2_logger.notice(banner("Reindexing"))  # type: ignore
            self._split_data_for_reindex(good_crystals_data)
            self._reindex()
        else:
            self._prepare_for_scaling(good_crystals_data)

        xia2_logger.notice(banner("Scaling"))  # type: ignore
        self._scale()
        xia2_logger.notice(banner("Merging"))  # type: ignore
        self._merge()

    def _split_data_for_reindex(self, good_crystals_data):

        self._filtered_batches_to_process = split_integrated_data(
            good_crystals_data,
            self._integrated_data,
            self._reduction_params,
        )

    def _filter(self) -> Tuple[CrystalsDict, uctbx.unit_cell, sgtbx.space_group_info]:
        return filter_(self._filter_wd, self._integrated_data, self._reduction_params)

    def _reindex(self) -> None:
        reindexed_new_batches = parallel_cosym(
            self._reindex_wd,
            self._filtered_batches_to_process,
            self._reduction_params,
            nproc=self._reduction_params.nproc,
        )
        batches_to_scale = reindexed_new_batches
        if len(batches_to_scale) > 1:
            # first scale each batch
            batches_to_scale, dmins = scale_parallel_batches(
                self._reindex_wd, batches_to_scale, self._reduction_params
            )
            user_dmin = self._reduction_params.d_min
            if not user_dmin:
                dmins = np.array([d for d in dmins if d])
                if len(dmins):
                    self._reduction_params.d_min = np.mean(dmins)
            # Reindex all batches together.
            batches_to_scale = cosym_reindex(
                self._reindex_wd,
                batches_to_scale,
                self._reduction_params.d_min,
                self._reduction_params.lattice_symmetry_max_delta,
                self._reduction_params.partiality_threshold,
                reference=self._reduction_params.reference,
            )
            if not user_dmin:
                self._reduction_params.d_min = None
            xia2_logger.info(f"Consistently reindexed {len( batches_to_scale)} batches")
        self._batches_to_scale = batches_to_scale

    def _prepare_for_scaling(self, good_crystals_data) -> None:
        self._batches_to_scale = split_integrated_data(
            good_crystals_data,
            self._integrated_data,
            self._reduction_params,
        )

    def _scale(self) -> None:
        raise NotImplementedError

    def _merge(self) -> None:
        scaled_results = self._files_to_merge

        uc_params = [flex.double() for _ in range(6)]
        for fp in scaled_results:
            expts = load.experiment_list(fp.expt, check_format=False)
            for c in expts.crystals():
                unit_cell = c.get_recalculated_unit_cell() or c.get_unit_cell()
                for i, p in enumerate(unit_cell.parameters()):
                    uc_params[i].append(p)
        self._reduction_params.space_group = c.get_space_group().info()
        best_unit_cell = uctbx.unit_cell(parameters=[flex.median(p) for p in uc_params])
        self._reduction_params.central_unit_cell = best_unit_cell
        n_final = len(uc_params[0])
        uc_str = ", ".join(str(round(i, 3)) for i in best_unit_cell.parameters())
        xia2_logger.info(
            f"{n_final} crystals in total scaled in space group {self._reduction_params.space_group}\nMedian cell: {uc_str}"
        )
        merge_input = {}
        merge_wds = {}
        n_groups: int = 1
        if self._parsed_grouping:
            if "merge_by" in self._parsed_grouping._groupings:
                groups_for_merge, metadata_groups = yml_to_merged_filesdict(
                    self._merge_wd,
                    self._parsed_grouping,
                    scaled_results,
                    self._reduction_params,
                    grouping="merge_by",
                )
                if self._reduction_params.dose_series_repeat:
                    # Not essential, but nicer to be named dose rather than generic 'group'
                    for name in list(groups_for_merge.keys()):
                        groups_for_merge[
                            name.replace("group", "dose")
                        ] = groups_for_merge.pop(name)

                # move the data into subdirs
                for g, flist in groups_for_merge.items():
                    if flist:
                        new_files = []
                        if not Path(self._merge_wd / g).is_dir():
                            Path.mkdir(self._merge_wd / g)
                        for f in flist:
                            new_expt = f.expt.parent / g / f.expt.name
                            new_refl = f.refl.parent / g / f.refl.name
                            f.expt.rename(new_expt)
                            f.refl.rename(new_refl)
                            new_files.append(FilePair(new_expt, new_refl))
                        groups_for_merge[g] = new_files
                for g, flist in groups_for_merge.items():
                    if flist:
                        merge_input[f"{g}"] = flist
                        merge_wds[f"{g}"] = flist[0].expt.parent
                n_groups = len(groups_for_merge)
                if n_groups == 1:
                    xia2_logger.info(
                        f"All data within a single merge group based on metadata items: {', '.join(self._parsed_grouping.groupings['merge_by'].metadata_names)}"
                    )
                else:
                    xia2_logger.info(
                        f"Data split into {n_groups} merge groups based on metadata items: {', '.join(self._parsed_grouping.groupings['merge_by'].metadata_names)}"
                    )
                xia2_logger.info(
                    "Group data ranges:\n"
                    + "\n".join(
                        f"  {n}: {g}"
                        for n, g in zip(merge_input.keys(), metadata_groups)
                    )
                )
                if self._reduction_params.dose_series_repeat:
                    xia2_logger.info(
                        f"Dose groups assigned using formula: image_no modulo {self._reduction_params.dose_series_repeat} = dose_point"
                    )

        if not merge_input:  # i.e. no "merge_by" in parsed_grouping
            merge_wds = {"merged": self._data_reduction_wd / "merge" / "all"}
            if not Path(merge_wds["merged"]).is_dir():
                Path.mkdir(merge_wds["merged"])
            # NB at this point, data could be already grouped and filtered or still scaled output
            merge_input = apply_scaled_array_to_all_files(
                merge_wds["merged"], scaled_results, self._reduction_params
            )

        group_names: List[str] = list(merge_input.keys())
        name_to_expts_arr: dict[str, Tuple] = {name: () for name in group_names}

        futures = {}
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            for name, filelist in merge_input.items():
                futures[
                    pool.submit(prepare_scaled_array, filelist, best_unit_cell)
                ] = name
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            name_to_expts_arr[name] = future.result()

        future_list = []
        three_column_summaries: dict[str, str] = {name: "" for name in group_names}
        four_column_summaries: dict[str, str] = {name: "" for name in group_names}
        resolutions: dict[str, float] = {name: 0.0 for name in group_names}
        merge_results_dict: dict[str, MergeResult] = {}

        with record_step(
            "dials.merge (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=min(self._reduction_params.nproc, n_groups)
        ) as pool:
            for name, (scaled_array, elist) in name_to_expts_arr.items():
                future_list.append(
                    pool.submit(
                        merge,
                        merge_wds[name],
                        scaled_array,
                        elist,
                        self._reduction_params.d_min,
                        best_unit_cell,
                        self._reduction_params.partiality_threshold,
                        name,
                        cc_half_limit=self._reduction_params.cc_half_limit,
                        misigma_limit=self._reduction_params.misigma_limit,
                    )
                )

        for mergefuture in concurrent.futures.as_completed(future_list):
            mergeresult: MergeResult = mergefuture.result()
            if n_groups > 1:
                xia2_logger.info(f"Merged {mergeresult.name}")
            merge_results_dict[mergeresult.name] = mergeresult
            if self._reduction_params.d_min:
                three_column_summaries[mergeresult.name] = mergeresult.summary
            elif mergeresult.suggested_resolution:
                four_column_summaries[mergeresult.name] = mergeresult.summary
                resolutions[mergeresult.name] = mergeresult.suggested_resolution
            else:
                three_column_summaries[mergeresult.name] = mergeresult.summary
            # don't save the files yet, as we may want to rename them, depending on if we need to rerun
            # with a resolution cutoff

        def print_summaries(summaries):
            for result in summaries.values():  # always print stats in same order
                if result:
                    xia2_logger.info(result)

        if self._reduction_params.d_min:
            # dmin was applied, so don't try to estimate resolution limit
            # so just record the files, print a summary and finish
            record_merge_files(merge_results_dict)
            print_summaries(three_column_summaries)
            if n_groups > 1:
                xia2_logger.info(
                    "Summary of key statistics for merge groups\n"
                    + create_merge_group_summary(merge_results_dict, name_to_expts_arr)
                )
            return

        # No d_min was specified, see if a resolution cutoff was determined in dials.merge
        suggested_nonzero = sorted(v for v in resolutions.values() if v)
        msg_to_print = (
            f"based on cc_half={self._reduction_params.cc_half_limit}"
            if self._reduction_params.cc_half_limit
            else f"based on misigma={self._reduction_params.misigma_limit}"
        )

        # default was to use cc1/2 to determine suggested cutoff. If this fails for all merge groups,
        # try with misigma
        if (
            self._reduction_params.cc_half_limit
            and not suggested_nonzero
            and self._reduction_params.misigma_limit
        ):
            # try again with the misigma limit
            # will overwrite the previous merge jobs, but that's ok.
            with record_step(
                "dials.merge (parallel)"
            ), concurrent.futures.ProcessPoolExecutor(
                max_workers=min(self._reduction_params.nproc, n_groups)
            ) as pool:
                for name, (scaled_array, elist) in name_to_expts_arr.items():
                    future_list.append(
                        pool.submit(
                            merge,
                            merge_wds[name],
                            scaled_array,
                            elist,
                            self._reduction_params.d_min,
                            best_unit_cell,
                            self._reduction_params.partiality_threshold,
                            name,
                            cc_half_limit=None,
                            misigma_limit=self._reduction_params.misigma_limit,
                        )
                    )
            for mergefuture in concurrent.futures.as_completed(future_list):
                mergeresult_misigma: MergeResult = mergefuture.result()
                name = mergeresult_misigma.name
                merge_results_dict[name] = mergeresult_misigma
                if mergeresult_misigma.suggested_resolution:
                    four_column_summaries[name] = mergeresult_misigma.summary
                    resolutions[name] = mergeresult_misigma.suggested_resolution
                else:
                    three_column_summaries[name] = mergeresult_misigma.summary
            suggested_nonzero = sorted(v for v in resolutions.values() if v)
            msg_to_print = f"based on misigma={self._reduction_params.misigma_limit}"

        if not suggested_nonzero:
            xia2_logger.info("Unable to estimate resolution limit")
            # can't determine a resolution limit, so just use the current merge job as final.
            record_merge_files(merge_results_dict)
            print_summaries(three_column_summaries)
            if n_groups > 1:
                summary_table = create_merge_group_summary(
                    merge_results_dict, name_to_expts_arr
                )
                xia2_logger.info(
                    "Summary of key statistics for merge groups\n" + summary_table
                )
            return

        # At this point we have a resolution cutoff to apply to all merge groups.
        # However, for reporting trends in the case of multiple merging groups, we want to
        # report the suggested resolution per merge group.

        for k in four_column_summaries.keys():
            if not four_column_summaries[
                k
            ]:  # could happen if only some were succesful with cc1/2=0.3 fit
                xia2_logger.info(three_column_summaries[k])
            else:
                xia2_logger.info(four_column_summaries[k])

        # rename the results files with _full appended
        for name, mergeresult in merge_results_dict.items():
            new_file = mergeresult.merge_file.with_stem(
                mergeresult.merge_file.stem + "_full"
            )
            mergeresult.merge_file = mergeresult.merge_file.rename(new_file)
            new_log = mergeresult.logfile.with_stem(mergeresult.logfile.stem + "_full")
            mergeresult.logfile = mergeresult.logfile.rename(new_log)
            new_json = mergeresult.jsonfile.with_stem(
                mergeresult.jsonfile.stem + "_full"
            )
            mergeresult.jsonfile = mergeresult.jsonfile.rename(new_json)
            new_html = mergeresult.htmlfile.with_stem(
                mergeresult.htmlfile.stem + "_full"
            )
            mergeresult.htmlfile = mergeresult.htmlfile.rename(new_html)

        record_merge_files(merge_results_dict)

        suggested = suggested_nonzero[0]
        if n_groups > 1:
            xia2_logger.info(
                f"Applying resolution cut of {suggested}A to all merging groups, {msg_to_print}. \nSome groups may have a lower practical resolution limit."
            )
        else:
            xia2_logger.info(
                f"Applying resolution cut of {suggested}A, {msg_to_print}"
                + "\nData to the full resolution can be found in merged_full.mtz"
            )
        future_list = []
        cut_merge_results_dict: dict[str, MergeResult] = {}
        with record_step(
            "dials.merge (resolution cut, parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=min(self._reduction_params.nproc, n_groups)
        ) as pool:

            for name, (scaled_array, elist) in name_to_expts_arr.items():
                scaled_array, elist = name_to_expts_arr[name]
                scaled_array = scaled_array.resolution_filter(d_min=suggested)
                future_list.append(
                    pool.submit(
                        merge,
                        merge_wds[name],
                        scaled_array,
                        elist,
                        suggested,
                        best_unit_cell,
                        self._reduction_params.partiality_threshold,
                        name,
                    )
                )
        for mergefuture in concurrent.futures.as_completed(future_list):
            mergeresult_suggested: MergeResult = mergefuture.result()
            cut_merge_results_dict[mergeresult_suggested.name] = mergeresult_suggested
        record_merge_files(cut_merge_results_dict)

        if n_groups > 1:
            rows = [[f"{i:.2f}A" for i in resolutions.values()]]
            xia2_logger.info(
                f"\nSuggested resolutions for merge groups ({msg_to_print})\n"
                + tabulate(rows, group_names)
            )
            xia2_logger.info(
                f"\nSummary of key statistics for merge groups (to {suggested}A)\n"
                + create_merge_group_summary(cut_merge_results_dict, name_to_expts_arr)
            )
