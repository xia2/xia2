from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import iotbx.phil
from cctbx import sgtbx, uctbx
from dials.array_family import flex
from dxtbx.serialize import load

xia2_logger = logging.getLogger(__name__)


@dataclass(eq=False)
class FilePair:
    expt: Path
    refl: Path

    def check(self):
        if not self.expt.is_file():
            raise FileNotFoundError(f"File {self.expt} does not exist")
        if not self.refl.is_file():
            raise FileNotFoundError(f"File {self.refl} does not exist")

    def validate(self):
        expt = load.experiment_list(self.expt, check_format=False)
        refls = flex.reflection_table.from_file(self.refl)
        refls.assert_experiment_identifiers_are_consistent(expt)

    def __eq__(self, other):
        if self.expt == other.expt and self.refl == other.refl:
            return True
        return False


FilesDict = Dict[int, FilePair]
# FilesDict: A dict where the keys are an index, corresponding to a filepair


@dataclass
class ReductionParams:
    space_group: sgtbx.space_group
    batch_size: int = 1000
    nproc: int = 1
    d_min: Optional[float] = None
    anomalous: bool = False
    cluster_threshold: float = 1000.0
    absolute_angle_tolerance: float = 0.5
    absolute_length_tolerance: float = 0.2
    central_unit_cell: Optional[uctbx.unit_cell] = None
    model: Optional[Path] = None
    cosym_phil: Optional[Path] = None

    @classmethod
    def from_phil(cls, params: iotbx.phil.scope_extract):
        """Construct from xia2.cli.ssx phil_scope."""
        model = None
        cosym_phil = None
        if params.scaling.model:
            model = Path(params.scaling.model).resolve()
        if params.clustering.central_unit_cell and params.clustering.threshold:
            raise ValueError(
                "Only one of clustering.central_unit_cell and clustering.threshold can be specified"
            )
        if params.symmetry.phil:
            cosym_phil = Path(params.symmetry.phil).resolve()
        return cls(
            params.symmetry.space_group,
            params.batch_size,
            params.multiprocessing.nproc,
            params.d_min,
            params.scaling.anomalous,
            params.clustering.threshold,
            params.clustering.absolute_angle_tolerance,
            params.clustering.absolute_length_tolerance,
            params.clustering.central_unit_cell,
            model,
            cosym_phil,
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
        pass
