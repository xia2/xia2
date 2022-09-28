from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from cctbx import sgtbx, uctbx

from xia2.Handlers.Streams import banner

xia2_logger = logging.getLogger(__name__)

import concurrent.futures

from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_definitions import FilePair, ReductionParams
from xia2.Modules.SSX.data_reduction_programs import (
    CrystalsDict,
    assess_for_indexing_ambiguities,
    filter_,
    merge_files,
)
from xia2.Modules.SSX.yml_handling import yml_to_filesdict


def inspect_directories(directories_to_process: List[Path]) -> List[FilePair]:
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
            try:
                fp.validate()
            except AssertionError:
                raise ValueError(
                    f"Files {fp.expt} & {fp.refl} not consistent, please check input data"
                )
            else:
                new_data.append(fp)
        if not expts_this:
            xia2_logger.warning(f"No integrated data files found in {str(d)}")
    if not new_data:
        raise ValueError("No integrated datafiles found in directories")
    return new_data


def inspect_scaled_directories(
    directories_to_process: List[Path],
    reduction_params: ReductionParams,
) -> List[FilePair]:
    new_data: List[FilePair] = []
    for d in directories_to_process:
        # if reduction_params.model - check same as for these data.
        expts_this, refls_this = ([], [])
        for file_ in list(d.glob("scale*.expt")):
            expts_this.append(file_)
        for file_ in list(d.glob("scale*.refl")):
            refls_this.append(file_)
        if len(expts_this) != len(refls_this):
            raise ValueError(
                f"Unequal number of experiments ({len(expts_this)}) "
                + f"and reflections ({len(refls_this)}) files found in {d}"
            )
        for expt, refl in zip(sorted(expts_this), sorted(refls_this)):
            fp = FilePair(expt, refl)
            try:
                fp.validate()
            except AssertionError:
                raise ValueError(
                    f"Files {fp.expt} & {fp.refl} not consistent, please check input data"
                )
            else:
                new_data.append(fp)
        if not expts_this:
            xia2_logger.warning(f"No scaled data files found in {str(d)}")
    if not new_data:
        raise ValueError("No scaled datafiles found in directories given")
    return new_data


def inspect_files(
    reflection_files: List[Path], experiment_files: List[Path]
) -> List[FilePair]:
    """Inspect the input data, matching by the order of input."""
    new_data: List[FilePair] = []
    for refl_file, expt_file in zip(reflection_files, experiment_files):
        fp = FilePair(expt_file, refl_file)
        fp.check()
        try:
            fp.validate()
        except AssertionError:
            raise ValueError(
                f"Files {fp.expt} & {fp.refl} not consistent, please check input order"
            )
        else:
            new_data.append(fp)
    return new_data


class BaseDataReduction(object):

    _no_input_error_msg = "No input data found"  # overwritten with more useful
    # messages in derived classes.

    def __init__(
        self,
        main_directory: Path,
        integrated_data: List[FilePair],
        processed_directories: List[Path],
        reduction_params,
    ):
        self._integrated_data: List[FilePair] = integrated_data
        self._main_directory: Path = main_directory
        self._reduction_params: ReductionParams = reduction_params

        self._data_reduction_wd: Path = self._main_directory / "data_reduction"
        self._filter_wd = self._data_reduction_wd / "prefilter"
        self._reindex_wd = self._data_reduction_wd / "reindex"
        self._scale_wd = self._data_reduction_wd / "scale"
        self._merge_wd = self._data_reduction_wd / "merge"

        self._filtered_files_to_process: List[FilePair] = []
        self._files_to_scale: List[FilePair] = []
        self._files_to_merge: List[FilePair] = []

        # load any previously scaled data
        self._previously_scaled_data = []
        if processed_directories:
            self._previously_scaled_data = inspect_scaled_directories(
                processed_directories, reduction_params
            )

        if not (self._integrated_data or self._previously_scaled_data):
            raise ValueError(self._no_input_error_msg)

        if not Path.is_dir(self._data_reduction_wd):
            Path.mkdir(self._data_reduction_wd)
        if not Path(self._merge_wd).is_dir():
            Path.mkdir(self._merge_wd)

        if self._reduction_params.groupby_yaml:
            # verify the grouping yaml and save into the data reduction dir.
            from xia2.Modules.SSX.yml_handling import full_parse

            with open(self._reduction_params.groupby_yaml, "r") as f:
                parsed = full_parse(f)
            self._parsed_yaml = parsed
            from shutil import copyfile

            copyfile(
                self._reduction_params.groupby_yaml,
                self._data_reduction_wd / "groupby.yaml",
            )
        else:
            self._parsed_yaml = None

    @classmethod
    def from_directories(
        cls,
        main_directory: Path,
        directories_to_process: List[Path],
        processed_directories: List[Path],
        reduction_params,
    ):
        new_data = inspect_directories(directories_to_process)
        return cls(
            main_directory,
            new_data,
            processed_directories,
            reduction_params,
        )

    @classmethod
    def from_files(
        cls,
        main_directory: Path,
        reflection_files: List[Path],
        experiment_files: List[Path],
        processed_directories: List[Path],
        reduction_params,
    ):
        # load and check all integrated files
        try:
            new_data = inspect_files(reflection_files, experiment_files)
        except FileNotFoundError as e:
            raise ValueError(e)
        return cls(
            main_directory,
            new_data,
            processed_directories,
            reduction_params,
        )

    @classmethod
    def from_processed_only(
        cls,
        main_directory: Path,
        processed_directories: List[Path],
        reduction_params,
    ):
        return cls(main_directory, [], processed_directories, reduction_params)

    def run(self) -> None:

        if not self._integrated_data:
            self._run_only_previously_scaled()
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
            # split good crystals based on resolve_by + batchsize
            xia2_logger.notice(banner("Reindexing"))  # type: ignore
            self._split_data_for_reindex(good_crystals_data)
            self._reindex()
        else:
            self._prepare_for_scaling(good_crystals_data)

        xia2_logger.notice(banner("Scaling"))  # type: ignore
        self._scale()
        self._prepare_for_merging()
        xia2_logger.notice(banner("Merging"))  # type: ignore
        self._merge()

    def _split_data_for_reindex(self, good_crystals_data):
        from xia2.Modules.SSX.data_reduction_programs import split_integrated_data

        self._filtered_files_to_process = split_integrated_data(
            self._filter_wd,
            good_crystals_data,
            self._integrated_data,
            self._reduction_params,
        )

    def _run_only_previously_scaled(self):
        raise NotImplementedError

    def _filter(self) -> Tuple[CrystalsDict, uctbx.unit_cell, sgtbx.space_group_info]:
        return filter_(self._filter_wd, self._integrated_data, self._reduction_params)

    def _reindex(self) -> None:
        raise NotImplementedError

    def _prepare_for_scaling(self, good_crystals_data) -> None:
        "Inspect filtered files and organise for scaling."
        raise NotImplementedError

    def _scale(self) -> None:
        raise NotImplementedError

    def _prepare_for_merging(self):
        # Chance to do something specific between having scaled results and merging
        # e.g. to add in previously scaled data in reduction with a reference
        pass

    def _merge(self):
        scaled_results = self._files_to_merge

        uc_params = [flex.double() for _ in range(6)]
        for fp in scaled_results:
            expts = load.experiment_list(fp.expt, check_format=False)
            for c in expts.crystals():
                unit_cell = c.get_recalculated_unit_cell() or c.get_unit_cell()
                for i, p in enumerate(unit_cell.parameters()):
                    uc_params[i].append(p)
        best_unit_cell = uctbx.unit_cell(parameters=[flex.median(p) for p in uc_params])
        self._reduction_params.central_unit_cell = best_unit_cell
        n_final = len(uc_params[0])
        uc_str = ", ".join(str(round(i, 3)) for i in best_unit_cell.parameters())
        xia2_logger.info(
            f"{n_final} crystals in total scaled in space group {self._reduction_params.space_group}\nMedian cell: {uc_str}"
        )

        merge_input = {"mergegroup_1": scaled_results}  # default if no 'merge_by'
        if self._parsed_yaml:
            if "merge_by" in self._parsed_yaml._groupings:
                # for name, scaled_files in scaled_results.items():
                merge_input = {}
                print("splitting for merge")
                groups_for_merge = yml_to_filesdict(
                    self._reindex_wd,
                    self._parsed_yaml,
                    scaled_results,
                    grouping="merge_by",
                )
                for g, flist in groups_for_merge.items():
                    merge_input[f"{g}"] = flist
                print("completed splitting for merge")

        future_list = (
            []
        )  # do it this way to get results in order for consistent printing

        with record_step(
            "dials.merge (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            for name, results in merge_input.items():
                future_list.append(
                    pool.submit(
                        merge_files,
                        self._merge_wd,
                        results,
                        self._reduction_params,
                        name,
                    )
                )
        for name, future in zip(merge_input.keys(), future_list):
            try:
                mergeresult = future.result()
            except Exception as e:
                xia2_logger.warning(f"Unsuccessful merging of {name}. Error:\n{e}")
            else:
                xia2_logger.info(mergeresult.summary)
                FileHandler.record_data_file(mergeresult.merge_file)
                FileHandler.record_log_file(
                    mergeresult.logfile.name.rstrip(".log"), mergeresult.logfile
                )
                FileHandler.record_more_log_file(
                    mergeresult.jsonfile.name.rstrip(".json"), mergeresult.jsonfile
                )
                FileHandler.record_html_file(
                    mergeresult.htmlfile.name.rstrip(".html"), mergeresult.htmlfile
                )
