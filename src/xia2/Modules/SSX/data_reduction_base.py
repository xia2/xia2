from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, List

xia2_logger = logging.getLogger(__name__)

from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_programs import FilePair


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
    def __init__(self, main_directory: Path, input_data: List[FilePair]) -> None:
        # General setup, finding which of the input data have already
        # been processed. Then it's up to the specific data reduction algorithms
        # as to how that information should be used.
        self._main_directory = main_directory
        self._input_data = input_data
        self._data_reduction_wd = self._main_directory / "data_reduction"

        self.files_already_processed = []
        self.new_to_process = []

        xia2_logger.notice(banner("Data reduction"))  # type: ignore

        if not Path.is_dir(self._data_reduction_wd):
            Path.mkdir(self._data_reduction_wd)
            self.new_to_process = self._input_data
        # if has been processed already, need to read something from the data
        # reduction dir that says it has been reindexed in a consistent manner
        elif (self._data_reduction_wd / "data_reduction.json").is_file():
            self.files_already_processed = self._load_prepared()
            for fp in self._input_data:
                if fp not in self.files_already_processed:
                    self.new_to_process.append(fp)
        else:
            # perhaps error in processing such that none were successfully
            # processed previously. In this case all should be reprocessed
            self.new_to_process = self._input_data

        if len(self.new_to_process) + len(self.files_already_processed) != len(
            self._input_data
        ):
            raise ValueError(
                f"""Error assessing new and previously processed files:
                new = {self.new_to_process}
                previous = {self.files_already_processed}
                input = {self._input_data}
                new + previous != input"""
            )

        if self.files_already_processed:
            files = "\n".join(
                str(fp.expt) + "\n" + str(fp.refl)
                for fp in self.files_already_processed
            )
            xia2_logger.info(f"Files previously processed:\n{files}")
        new_files = "\n".join(
            str(fp.expt) + "\n" + str(fp.refl) for fp in self.new_to_process
        )
        xia2_logger.info(f"New data to process:\n{new_files}")

    @classmethod
    def from_directories(cls, main_directory: Path, directories_to_process: List[Path]):
        # extract all integrated files from the directories
        new_data = inspect_directories(directories_to_process)
        return cls(main_directory, new_data)

    @classmethod
    def from_files(
        cls,
        main_directory: Path,
        reflection_files: List[Path],
        experiment_files: List[Path],
    ):
        # load and check all integrated files
        try:
            new_data = inspect_files(reflection_files, experiment_files)
        except FileNotFoundError as e:
            raise ValueError(e)
        return cls(main_directory, new_data)

    def _save_as_prepared(self):
        data_reduction_progress = {
            "files_processed": {
                "refls": [os.fspath(fp.refl) for fp in self._input_data],
                "expts": [os.fspath(fp.expt) for fp in self._input_data],
            },
        }
        with (self._data_reduction_wd / "data_reduction.json").open(mode="w") as fp:
            json.dump(data_reduction_progress, fp, indent=2)

    def _load_prepared(self):
        with (self._data_reduction_wd / "data_reduction.json").open(mode="r") as fp:
            previous = json.load(fp)
        prev_refls = previous["files_processed"]["refls"]
        prev_expts = previous["files_processed"]["expts"]
        files_already_processed = [
            FilePair(Path(expt), Path(refl))
            for expt, refl in zip(prev_expts, prev_refls)
        ]
        return files_already_processed

    def run(self, params: Any) -> None:
        pass
