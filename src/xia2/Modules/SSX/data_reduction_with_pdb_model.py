from __future__ import annotations

import concurrent.futures
import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from cctbx import sgtbx, uctbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction, FilesDict
from xia2.Modules.SSX.data_reduction_programs import filter_, merge, scale_against_model
from xia2.Modules.SSX.reporting import statistics_output_from_scaled_files

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


class DataReductionWithPDBModel(BaseDataReduction):

    _no_input_error_msg = (
        "No input integrated data, or previously processed scale directories\n"
        + "have been found in the input. Please provide at least some integrated data or\n"
        + "a directory of data previously scaled with xia2.ssx/xia2.ssx_reduce\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated data files.\n"
        + " - Use processed_directory= to specify /data_reduction/scale directories of\n"
        + "   data previously processed with the same PDB model as reference."
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
        xia2_logger.info(
            statistics_output_from_scaled_files(scaled_expts, scaled_table, uc)
        )
        merge(
            self._scale_wd,
            scaled_expts,
            scaled_table,
            self._reduction_params.d_min,
            uc,
            suffix="_all",
        )

    def _filter(self) -> Tuple[FilesDict, uctbx.unit_cell, sgtbx.space_group_info]:
        new_files_to_process, best_unit_cell, space_group = filter_(
            self._filter_wd, self._integrated_data, self._reduction_params
        )
        self._reduction_params.central_unit_cell = best_unit_cell  # store the
        # updated value to use in scaling
        return new_files_to_process, best_unit_cell, space_group

    def _prepare_for_scaling(self) -> None:
        self._files_to_scale = list(self._filtered_files_to_process.values())

    def _reindex(self) -> None:
        # ideally - reindex each dataset against target
        # on each batch - reindex internally to be consistent
        # then reindex against pdb model.
        ##FIXME need to implement this in cosym
        assert 0

    def _scale_and_merge(self) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        scaled_results: FilesDict = {}
        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            scale_futures: Dict[Any, int] = {
                pool.submit(
                    scale_against_model,
                    self._scale_wd,
                    files,
                    index,
                    self._reduction_params,
                ): index
                for index, files in enumerate(self._files_to_scale)  # .items()
            }
            for future in concurrent.futures.as_completed(scale_futures):
                try:
                    result = future.result()
                    i = scale_futures[future]
                except Exception as e:
                    xia2_logger.warning(f"Unsuccessful scaling of group. Error:\n{e}")
                else:
                    xia2_logger.info(f"Completed scaling of group {i+1}")
                    scaled_results.update(result)
        if not scaled_results:
            raise ValueError("No groups successfully scaled")

        with record_step("merging"):
            scaled_expts = ExperimentList([])
            scaled_tables = []
            # For merging (a simple program), we don't require much data in the
            # reflection table. So to avoid a large memory spike, just keep the
            # values we know we need for merging and to report statistics
            # first 6 in keep are required in merge, the rest will potentially
            #  be used for filter_reflections call in merge
            for file_pair in scaled_results.values():
                expts = load.experiment_list(file_pair.expt, check_format=False)
                _wrap_extend_expts(scaled_expts, expts)
                table = flex.reflection_table.from_file(file_pair.refl)
                for k in list(table.keys()):
                    if k not in scaled_cols_to_keep:
                        del table[k]
                scaled_tables.append(table)
            scaled_table = flex.reflection_table.concat(scaled_tables)

            n_final = len(scaled_expts)
            uc = determine_best_unit_cell(scaled_expts)
            uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
            xia2_logger.info(
                f"{n_final} crystals scaled in space group {scaled_expts[0].crystal.get_space_group().info()}\nMedian cell: {uc_str}"
            )
            xia2_logger.info(
                statistics_output_from_scaled_files(scaled_expts, scaled_table, uc)
            )
            merge(
                self._scale_wd,
                scaled_expts,
                scaled_table,
                self._reduction_params.d_min,
                uc,
            )

            # FIXME export an unmerged mtz too

            # now add any extra data previously scaled
            if self._previously_scaled_data:
                (
                    prev_scaled_expts,
                    prev_scaled_tables,
                ) = self._combine_previously_scaled()
                _wrap_extend_expts(scaled_expts, prev_scaled_expts)
                scaled_table = flex.reflection_table.concat(
                    scaled_tables + prev_scaled_tables
                )
                uc = determine_best_unit_cell(scaled_expts)
                uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
                xia2_logger.info(
                    "Summary statistics for all input data, including previously scaled"
                )
                xia2_logger.info(
                    statistics_output_from_scaled_files(scaled_expts, scaled_table, uc)
                )
                merge(
                    self._scale_wd,
                    scaled_expts,
                    scaled_table,
                    self._reduction_params.d_min,
                    suffix="_all",
                )
