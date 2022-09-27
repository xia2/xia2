from __future__ import annotations

import logging
from pathlib import Path

from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    assess_for_indexing_ambiguities,
    check_consistent_space_group,
    cosym_reindex,
    determine_best_unit_cell_from_crystals,
    load_crystal_data_from_new_expts,
    parallel_cosym,
    scale,
)
from xia2.Modules.SSX.data_reduction_programs import split_integrated_data

xia2_logger = logging.getLogger(__name__)

class SimpleDataReduction(BaseDataReduction):

    _no_input_error_msg = (
        "No input integrated data, or previously processed scale directories\n"
        + "have been found in the input. Please provide at least some integrated data or\n"
        + "a directory of data previously scaled with xia2.ssx/xia2.ssx_reduce\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated data files.\n"
        + " - Use processed_directory= to specify /data_reduction/scale directories of\n"
        + "   data previously processed in a similar manner (without a reference)."
    )

    def _run_only_previously_scaled(self):
        # ok, so want to check all consistent sg, do batch reindex if
        # necessary and then scale

        crystals_data = load_crystal_data_from_new_expts(self._previously_scaled_data)
        space_group = check_consistent_space_group(crystals_data)
        best_unit_cell = determine_best_unit_cell_from_crystals(crystals_data)

        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group,
            best_unit_cell,
            self._reduction_params.lattice_symmetry_max_delta,
        )
        if sym_requires_reindex and len(self._previously_scaled_data) > 1:
            xia2_logger.notice(banner("Reindexing"))
            self._files_to_scale = cosym_reindex(
                self._reindex_wd,
                self._previously_scaled_data,
                self._reduction_params.d_min,
                self._reduction_params.lattice_symmetry_max_delta,
            )
            xia2_logger.info("Consistently reindexed batches of previously scaled data")
        else:
            self._files_to_scale = self._previously_scaled_data
        xia2_logger.notice(banner("Scaling"))
        self._scale()
        self._merge()

    def _reindex(self) -> None:
        # First do parallel reindexing of each batch
        reindexed_new_files = list(
            parallel_cosym(
                self._reindex_wd,
                self._filtered_files_to_process,
                self._reduction_params,
                nproc=self._reduction_params.nproc,
            ).values()
        )
        # At this point, add in any previously scaled data.
        files_to_scale = reindexed_new_files + self._previously_scaled_data
        if len(files_to_scale) > 1:
            # Reindex all batches together.
            files_to_scale = cosym_reindex(
                self._reindex_wd,
                files_to_scale,
                self._reduction_params.d_min,
                self._reduction_params.lattice_symmetry_max_delta,
            )
            if self._previously_scaled_data:
                xia2_logger.info(
                    "Consistently reindexed all batches, including previously scaled data"
                )
            else:
                xia2_logger.info(
                    f"Consistently reindexed {len(reindexed_new_files)} batches"
                )
        self._files_to_scale =  files_to_scale

    def _prepare_for_scaling(self, good_crystals_data) -> None:
        new_files_to_process = split_integrated_data(
            self._filter_wd,
            good_crystals_data,
            self._integrated_data,
            self._reduction_params,
        )
        self._files_to_scale = list(new_files_to_process.values()) + self._previously_scaled_data


    def _scale(self) -> None:

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        result = scale(self._scale_wd, self._files_to_scale, self._reduction_params)
        xia2_logger.info(f"Completed scaling of all data")
        self._files_to_merge = [result]
