from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List

xia2_logger = logging.getLogger(__name__)

from xia2.Handlers.Streams import banner


class BaseDataReduction(object):
    def __init__(
        self,
        main_directory: Path,
        batch_directories: List[Path],
    ) -> None:
        # General setup, finding which of the batch directories have already
        # been processed. Then it's up to the specific data reduction algorithms
        # as to how that information should be used.
        self._main_directory = main_directory
        self._batch_directories = batch_directories

        data_reduction_dir = self._main_directory / "data_reduction"
        directories_already_processed = []
        new_to_process = []

        xia2_logger.notice(banner("Data reduction"))  # type: ignore

        if not Path.is_dir(data_reduction_dir):
            Path.mkdir(data_reduction_dir)
            new_to_process = self._batch_directories

        # if has been processed already, need to read something from the
        # data reduction dir that says it has been reindexed in a consistent
        # manner
        elif (data_reduction_dir / "data_reduction.json").is_file():
            previous = json.load((data_reduction_dir / "data_reduction.json").open())
            directories_already_processed = [
                Path(i) for i in previous["directories_processed"]
            ]

            for d in self._batch_directories:
                if d not in directories_already_processed:
                    new_to_process.append(d)
        else:
            # perhaps error in processing such that none were successfully
            # processed previously. In this case all should be reprocessed
            new_to_process = self._batch_directories

        if not (len(new_to_process) + len(directories_already_processed)) == len(
            self._batch_directories
        ):
            raise ValueError(
                f"""Error assessing new and previous directories:
                new = {new_to_process}
                previous = {directories_already_processed}
                input = {self._batch_directories}
                new + previous != input"""
            )

        self._new_directories_to_process = new_to_process
        self._directories_previously_processed = directories_already_processed
        if self._directories_previously_processed:
            dirs = "\n".join(str(i) for i in self._directories_previously_processed)
            xia2_logger.info(f"Directories previously processed:\n{dirs}")
        dirs = "\n".join(f"  {str(i)}" for i in self._new_directories_to_process)
        xia2_logger.info(f"New directories to process:\n{dirs}")

    def run(self, params: Any) -> None:
        pass
