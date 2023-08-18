from __future__ import annotations

import logging
from pathlib import Path

from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import FilePair, scale_on_batches

xia2_logger = logging.getLogger(__name__)


class SimpleDataReduction(BaseDataReduction):
    def _scale(self) -> None:

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        result = scale_on_batches(
            self._scale_wd, self._batches_to_scale, self._reduction_params
        )
        xia2_logger.info("Completed scaling of all data")
        self._files_to_merge = [FilePair(result.exptfile, result.reflfile)]
        FileHandler.record_data_file(result.exptfile)
        FileHandler.record_data_file(result.reflfile)
        FileHandler.record_log_file(result.logfile.name.rstrip(".log"), result.logfile)
