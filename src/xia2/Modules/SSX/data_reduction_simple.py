from __future__ import annotations

import logging
from pathlib import Path

from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    FilePair,
    cosym_reindex,
    parallel_cosym,
    scale_on_batches,
    scale_on_files,
)

xia2_logger = logging.getLogger(__name__)


class SimpleDataReduction(BaseDataReduction):
    def _reindex(self) -> None:
        # First do parallel reindexing of each batch
        reindexed_new_files = parallel_cosym(
            self._reindex_wd,
            self._filtered_batches_to_process,
            self._reduction_params,
            nproc=self._reduction_params.nproc,
        )
        files_to_scale = reindexed_new_files
        if len(files_to_scale) > 1:
            # Reindex all batches together.
            files_to_scale = cosym_reindex(
                self._reindex_wd,
                files_to_scale,
                self._reduction_params.d_min,
                self._reduction_params.lattice_symmetry_max_delta,
                self._reduction_params.partiality_threshold,
            )
            xia2_logger.info(
                f"Consistently reindexed {len(reindexed_new_files)} batches"
            )
        self._files_to_scale = files_to_scale

    def _scale(self) -> None:

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)
        if self._batches_to_scale:
            result = scale_on_batches(
                self._scale_wd, self._batches_to_scale, self._reduction_params
            )
        else:
            result = scale_on_files(
                self._scale_wd, self._files_to_scale, self._reduction_params
            )
        xia2_logger.info("Completed scaling of all data")
        self._files_to_merge = [FilePair(result.exptfile, result.reflfile)]
        FileHandler.record_data_file(result.exptfile)
        FileHandler.record_data_file(result.reflfile)
        FileHandler.record_log_file(result.logfile.name.rstrip(".log"), result.logfile)
