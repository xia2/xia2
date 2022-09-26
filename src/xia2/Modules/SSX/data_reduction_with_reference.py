from __future__ import annotations
from collections import defaultdict

import concurrent.futures
import enum
import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from cctbx import sgtbx, uctbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction, FilesDict
from xia2.Modules.SSX.data_reduction_programs import (
    filter_,
    merge,
    parallel_cosym_reference,
    scale_against_reference,
)
from xia2.Modules.SSX.reporting import statistics_output_from_scaled_files
from xia2.Modules.SSX.yml_handling import yml_to_filesdict
from xia2.Modules.SSX.data_reduction_programs import split_integrated_data

xia2_logger = logging.getLogger(__name__)

scaled_cols_to_keep = [
    "miller_index",
    "inverse_scale_factor",
    "intensity.scale.value",
    "intensity.scale.variance",
    "flags",
    "id",
    "partiality",
    "partial_id",
    "d",
    "qe",
    "dqe",
    "lp",
]


def _wrap_extend_expts(first_elist, second_elist):
    try:
        first_elist.extend(second_elist)
    except RuntimeError as e:
        raise ValueError(
            "Unable to combine experiments, check for datafiles containing duplicate experiments.\n"
            + f"  Specific error message encountered:\n  {e}"
        )

def merge_scalegroup(working_directory, scaled_results, reduction_params, name):

    #with record_step("joining for merge"):
    scaled_expts = ExperimentList([])
    scaled_tables = []
    # For merging (a simple program), we don't require much data in the
    # reflection table. So to avoid a large memory spike, just keep the
    # values we know we need for merging and to report statistics
    # first 6 in keep are required in merge, the rest will potentially
    #  be used for filter_reflections call in merge
    for file_pair in scaled_results:#.values():
        expts = load.experiment_list(file_pair.expt, check_format=False)
        _wrap_extend_expts(scaled_expts, expts)
        table = flex.reflection_table.from_file(file_pair.refl)
        for k in list(table.keys()):
            if k not in scaled_cols_to_keep:
                del table[k]
        scaled_tables.append(table)

    # now add any extra data previously scaled
    '''if self._previously_scaled_data:
        (
            prev_scaled_expts,
            prev_scaled_tables,
        ) = self._combine_previously_scaled()
        _wrap_extend_expts(scaled_expts, prev_scaled_expts)
        scaled_table = flex.reflection_table.concat(
            scaled_tables + prev_scaled_tables
        )
    else:'''
    scaled_table = flex.reflection_table.concat(scaled_tables)

    n_final = len(scaled_expts)
    #uc = determine_best_unit_cell(scaled_expts)
    #reduction_params.central_unit_cell = uc
    #uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
    #xia2_logger.info(
    #    f"{n_final} crystals scaled in space group {scaled_expts[0].crystal.get_space_group().info()}\nMedian cell: {uc_str}"
    #)
    '''if self._previously_scaled_data:
        xia2_logger.info(
            "Summary statistics for all input data, including previously scaled"
        )'''
    stats_summary, _ = statistics_output_from_scaled_files(
        scaled_expts, scaled_table, reduction_params.central_unit_cell , reduction_params.d_min
    )

    mergefile = merge(
        working_directory,
        scaled_expts,
        scaled_table,
        reduction_params.d_min,
        reduction_params.central_unit_cell,
        name,
    )
    summary = (
        f"Merged {n_final} crystals in {', '.join(name.split('.'))}\n" +
        f"Merged mtz file: {mergefile}\n" +
        stats_summary
    )
    return summary



class DataReductionWithReference(BaseDataReduction):

    _no_input_error_msg = (
        "No input integrated data, or previously processed scale directories\n"
        + "have been found in the input. Please provide at least some integrated data or\n"
        + "a directory of data previously scaled with xia2.ssx/xia2.ssx_reduce\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated data files.\n"
        + " - Use processed_directory= to specify /data_reduction/scale directories of\n"
        + "   data previously processed with the same PDB model/data file as reference."
    )

    def _combine_previously_scaled(self):
        scaled_expts = ExperimentList([])
        scaled_tables = []
        for file_pair in self._previously_scaled_data:
            prev_expts = load.experiment_list(file_pair.expt, check_format=False)
            _wrap_extend_expts(scaled_expts, prev_expts)
            table = flex.reflection_table.from_file(file_pair.refl)
            for k in list(table.keys()):
                if k not in scaled_cols_to_keep:
                    del table[k]
            scaled_tables.append(table)
        return scaled_expts, scaled_tables

    def _run_only_previously_scaled(self):

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        scaled_expts, scaled_tables = self._combine_previously_scaled()
        scaled_table = flex.reflection_table.concat(scaled_tables)
        n_final = len(scaled_expts)
        uc = determine_best_unit_cell(scaled_expts)
        uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
        xia2_logger.info(
            f"{n_final} crystals scaled in space group {scaled_expts[0].crystal.get_space_group().info()}\nMedian cell: {uc_str}"
        )
        xia2_logger.info("Summary statistics for combined previously scaled data")
        stats_summary, _ = statistics_output_from_scaled_files(
            scaled_expts, scaled_table, uc, self._reduction_params.d_min
        )
        xia2_logger.info(stats_summary)

        merge(
            self._scale_wd,
            scaled_expts,
            scaled_table,
            self._reduction_params.d_min,
            uc,
        )

    def _filter(self) -> Tuple[FilesDict, uctbx.unit_cell, sgtbx.space_group_info]:
        new_files_to_process, best_unit_cell, space_group = filter_(
            self._filter_wd, self._integrated_data, self._reduction_params
        )
        self._reduction_params.central_unit_cell = best_unit_cell  # store the
        # updated value to use in scaling
        return new_files_to_process, best_unit_cell, space_group

    def _prepare_for_scaling(self, good_crystals_data) -> None:
        # FIXME should be if scale_by:
        if self._parsed_yaml:
            if "scale_by" in self._parsed_yaml:
                self._files_to_scale = yml_to_filesdict(
                    self._filter_wd,
                    self._parsed_yaml,
                    self._integrated_data,
                    good_crystals_data,
                )
            else:
                new_files_to_process = split_integrated_data(
                    self._filter_wd,
                    good_crystals_data,
                    self._integrated_data,
                    self._reduction_params,
                )
                self._files_to_scale = {"scalegroup_1" : [i for i in new_files_to_process.values()]}
        else:
            new_files_to_process = split_integrated_data(
                self._filter_wd,
                good_crystals_data,
                self._integrated_data,
                self._reduction_params,
            )
            self._files_to_scale = {"scalegroup_1" : [i for i in new_files_to_process.values()]}



    def _reindex(self) -> None:
        # ideally - reindex each dataset against target
        # on each batch - reindex internally to be consistent
        # then reindex against reference.
        files_to_scale = list(
            parallel_cosym_reference(
                self._reindex_wd,
                self._filtered_files_to_process,
                self._reduction_params,
                nproc=self._reduction_params.nproc,
            ).values()
        )
        if "scale_by" in self._parsed_yaml:
            self._files_to_scale = yml_to_filesdict(
                self._reindex_wd,
                self._parsed_yaml,
                files_to_scale,
            )
        else:
            self._files_to_scale =  {"scalegroup_1" : files_to_scale}

    def _scale_and_merge(self) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        scaled_results = defaultdict(list)
        jobs = {}
        import functools

        for name, filelist in self._files_to_scale.items():
            batch_template = functools.partial(
                "batch_{index:0{maxindexlength:d}d}".format,
                maxindexlength=len(str(len(filelist))),
            )
            for i, fp in enumerate(filelist):
                jobs[f"{name}.{batch_template(index=i+1)}"] = fp
        #print(self._reduction_params)
        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            scale_futures: Dict[Any, int] = {
                pool.submit(
                    scale_against_reference,
                    self._scale_wd,
                    files,
                    self._reduction_params,
                    name,
                ): name
                for name, files in jobs.items()  # .items()
            }
            for future in concurrent.futures.as_completed(scale_futures):
                try:
                    result = future.result()
                    name = scale_futures[future]
                except Exception as e:
                    xia2_logger.warning(f"Unsuccessful scaling of group. Error:\n{e}")
                else:
                    xia2_logger.info(f"Completed scaling of {', '.join(name.split('.'))}")
                    scaled_results[name.split('.')[0]].append(result)
                    FileHandler.record_data_file(result.expt)
                    FileHandler.record_data_file(result.refl)
                    FileHandler.record_log_file(
                        f"dials.scale.{name}", self._scale_wd / f"dials.scale.{name}.log"
                    )
        scaled_results = dict(sorted(scaled_results.items()))

        if not scaled_results:
            raise ValueError("No groups successfully scaled")



        uc_params = [flex.double() for _ in range(6)]
        for filepairs in scaled_results.values():
            for fp in filepairs:
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
        from xia2.Handlers.Streams import banner
        xia2_logger.notice(banner("Merging"))

        merge_input = {}
        if self._parsed_yaml:
            if "merge_by" in self._parsed_yaml:
                for name, scaled_files in scaled_results.items():
                    groups_for_merge = yml_to_filesdict(
                        self._reindex_wd,
                        self._parsed_yaml,
                        scaled_files,
                        grouping="merge_by"
                    )
                    for g, flist in groups_for_merge.items():
                        merge_input[f"{name}.{g}"] = flist
            else:
                merge_input = scaled_results
        else:
            merge_input = scaled_results

        future_list = [] # do it this way to get results in order for consistent printing
        with record_step(
            "dials.merge (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            for name, results in merge_input.items():
                future_list.append(
                    pool.submit(
                        merge_scalegroup,
                        self._merge_wd,
                        results,
                        self._reduction_params,
                        name,
                    )
                )
        for name, future in zip(merge_input.keys(), future_list):
            try:
                summary = future.result()
                xia2_logger.info(summary)
            except Exception as e:
                xia2_logger.warning(f"Unsuccessful merging of {', '.join(name.split('.'))}. Error:\n{e}")
