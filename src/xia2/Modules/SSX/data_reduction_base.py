from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import iotbx.phil
from cctbx import crystal, sgtbx, uctbx
from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Handlers.Streams import banner

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


def assess_for_indexing_ambiguities(
    space_group: sgtbx.space_group_info, unit_cell: uctbx.unit_cell
) -> bool:
    # if lattice symmetry higher than space group symmetry, then need to
    # assess for indexing ambiguity.
    cs = crystal.symmetry(unit_cell=unit_cell, space_group=sgtbx.space_group())
    # Get cell reduction operator
    cb_op_inp_minimum = cs.change_of_basis_op_to_minimum_cell()
    # New symmetry object with changed basis
    minimum_symmetry = cs.change_basis(cb_op_inp_minimum)

    # Get highest symmetry compatible with lattice
    lattice_group = sgtbx.lattice_symmetry_group(
        minimum_symmetry.unit_cell(),
        max_delta=5,
        enforce_max_delta_for_generated_two_folds=True,
    )
    need_to_assess = lattice_group.order_z() > space_group.group().order_z()
    human_readable = {True: "yes", False: "no"}
    xia2_logger.info(
        "Indexing ambiguity assessment:\n"
        f"  Lattice group: {str(lattice_group.info())}, Space group: {str(space_group)}\n"
        f"  Potential indexing ambiguities: {human_readable[need_to_assess]}"
    )
    return need_to_assess


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
        #    self._filter_wd, self._integrated_data, self._reduction_params
        # )

        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group, best_unit_cell
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
        raise NotImplementedError

    def _reindex(self) -> None:
        raise NotImplementedError

    def _prepare_for_scaling(self) -> None:
        raise NotImplementedError

    def _scale_and_merge(self) -> None:
        raise NotImplementedError
