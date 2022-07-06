from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from cctbx import sgtbx, uctbx

from xia2.Handlers.Streams import banner

xia2_logger = logging.getLogger(__name__)

from xia2.Modules.SSX.data_reduction_definitions import (
    FilePair,
    FilesDict,
    ReductionParams,
)
from xia2.Modules.SSX.data_reduction_programs import (
    assess_for_indexing_ambiguities,
    filter_,
)


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
        for file_ in list(d.glob("scaled*.expt")):
            expts_this.append(file_)
        for file_ in list(d.glob("scaled*.refl")):
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

        self._filtered_files_to_process: FilesDict = {}
        self._files_to_scale: List[FilePair] = []

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

        # first filter the data.
        xia2_logger.notice(banner("Filtering"))  # type: ignore
        self._filtered_files_to_process, best_unit_cell, space_group = self._filter()

        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group,
            best_unit_cell,
            self._reduction_params.lattice_symmetry_max_delta,
        )
        if sym_requires_reindex:
            xia2_logger.notice(banner("Reindexing"))  # type: ignore
            self._reindex()
        else:
            self._prepare_for_scaling()

        xia2_logger.notice(banner("Scaling"))  # type: ignore
        self._scale_and_merge()

    def _run_only_previously_scaled(self):
        raise NotImplementedError

    def _filter(self) -> Tuple[FilesDict, uctbx.unit_cell, sgtbx.space_group_info]:
        return filter_(self._filter_wd, self._integrated_data, self._reduction_params)

    def _reindex(self) -> None:
        raise NotImplementedError

    def _prepare_for_scaling(self) -> None:
        raise NotImplementedError

    def _scale_and_merge(self) -> None:
        raise NotImplementedError
