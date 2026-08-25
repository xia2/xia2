from __future__ import annotations

import collections
import errno
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import iotbx.phil
from cctbx import sgtbx, uctbx
from dials.array_family import flex
from dxtbx.serialize import load


@dataclass(eq=False)
class FilePair:
    _expt: Optional[Path] = None
    _refl: Optional[Path] = None

    def check(self):
        if not self.expt.is_file():
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(self.expt)
            )
        if not self.refl.is_file():
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(self.refl)
            )

    def validate(self):
        expt = load.experiment_list(self.expt, check_format=False)
        refls = flex.reflection_table.from_file(self.refl)
        refls.assert_experiment_identifiers_are_consistent(expt)

    def __eq__(self, other):
        if self.expt == other.expt and self.refl == other.refl:
            return True
        return False

    def __hash__(self):
        return hash((str(self._expt), str(self._refl)))

    @property
    def expt(self):
        return self._expt

    @property
    def refl(self):
        return self._refl


def _parse_series_repeat_names(series_repeat: list[str]) -> list[str]:
    """Interpret the series_repeat phil option as a list of group names.

    Phil does not split multi-word values, so the names may be given as a
    comma-separated list (series_repeat=first,second,last) or as a quoted,
    whitespace-separated list (series_repeat='first second last').

    A name may be repeated, in which case each occurrence is numbered in
    order, e.g. series_repeat=dose,dose,apo gives the names
    dose_1, dose_2, apo.
    """
    names: list[str] = []
    for item in series_repeat:
        names.extend(name for name in item.replace(",", " ").split() if name)
    if len(names) < 2:
        raise ValueError(
            "At least two names must be given for series_repeat, "
            "e.g. series_repeat=first,second,last"
        )
    for name in names:
        if name != Path(name).name or name in (".", ".."):
            raise ValueError(
                f"Invalid name given for series_repeat: {name}\n"
                "Names are used as file/directory names, so must not contain"
                " path separators"
            )
    return _number_repeated_names(names)


def _number_repeated_names(names: list[str]) -> list[str]:
    """Append a count to any name that is given more than once, zero-padded
    to the number of digits needed for that name, e.g. two occurrences of
    'dose' become dose_1, dose_2, while twelve become dose_01 ... dose_12."""
    counts = collections.Counter(names)
    seen: dict[str, int] = collections.defaultdict(int)
    numbered: list[str] = []
    for name in names:
        n = counts[name]
        if n == 1:
            numbered.append(name)
        else:
            seen[name] += 1
            numbered.append(f"{name}_{seen[name]:0{len(str(n))}d}")
    duplicates = [n for n, c in collections.Counter(numbered).items() if c > 1]
    if duplicates:
        raise ValueError(
            f"Names given for series_repeat are ambiguous: {names}\n"
            + f"Numbering repeated names gives duplicate names: {duplicates}"
        )
    return numbered


@dataclass
class ReductionParams:
    space_group: sgtbx.space_group
    batch_size: int = 1000
    nproc: int = 1
    d_min: float | None = None
    d_max: float | None = None
    anomalous: bool = False
    lattice_symmetry_max_delta: float = 0.5
    cluster_threshold: float = 1000.0
    absolute_angle_tolerance: float = 0.5
    absolute_length_tolerance: float = 0.2
    central_unit_cell: uctbx.unit_cell | None = None
    reference: Path | None = None
    cosym_phil: Path | None = None
    scaling_phil: Path | None = None
    grouping: Path | None = None
    dose_series_repeat: int | None = None
    series_repeat_names: list[str] | None = None
    steps: list[str] = field(default_factory=lambda: ["scale", "merge"])
    reference_ksol: float = 0.35
    reference_bsol: float = 46.0
    partiality_threshold: float = 0.25
    mean_i_over_sigma_threshold: float | None = None
    remove_filtered_reflections: bool = True
    deltacchalf: bool = False
    stdcutoff: float = 4.0

    @classmethod
    def from_phil(cls, params: iotbx.phil.scope_extract):
        """Construct from xia2.cli.ssx phil_scope."""
        reference = None
        cosym_phil = None
        scaling_phil = None
        grouping = None
        if params.reference:
            reference = Path(params.reference).resolve()
            if not reference.is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(reference)
                )
        elif params.scaling.model:
            reference = Path(params.scaling.model).resolve()
            if not reference.is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(reference)
                )
        if params.clustering.central_unit_cell and params.clustering.threshold:
            raise ValueError(
                "Only one of clustering.central_unit_cell and clustering.threshold can be specified"
            )
        if params.symmetry.phil:
            cosym_phil = Path(params.symmetry.phil).resolve()
            if not cosym_phil.is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(cosym_phil)
                )
        if params.scaling.phil:
            scaling_phil = Path(params.scaling.phil).resolve()
            if not scaling_phil.is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(scaling_phil)
                )
        if params.grouping:
            grouping = Path(params.grouping).resolve()
            if not grouping.is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(grouping)
                )
        dose_series_repeat = params.dose_series_repeat
        series_repeat_names = None
        if params.series_repeat:
            if dose_series_repeat:
                raise ValueError(
                    "Only one of dose_series_repeat and series_repeat can be specified"
                )
            series_repeat_names = _parse_series_repeat_names(params.series_repeat)
            dose_series_repeat = len(series_repeat_names)
        deltacchalf = False
        mean_i_over_sigma_threshold = None
        if params.filtering.method:
            if "deltacchalf" in params.filtering.method:
                deltacchalf = True
            if "Isigma" in params.filtering.method:
                mean_i_over_sigma_threshold = (
                    params.filtering.mean_i_over_sigma_threshold
                )

        return cls(
            params.symmetry.space_group,
            params.reduction_batch_size,
            params.multiprocessing.nproc,
            params.d_min,
            params.d_max,
            params.scaling.anomalous,
            params.symmetry.lattice_symmetry_max_delta,
            params.clustering.threshold,
            params.clustering.absolute_angle_tolerance,
            params.clustering.absolute_length_tolerance,
            params.clustering.central_unit_cell,
            reference,
            cosym_phil,
            scaling_phil,
            grouping,
            dose_series_repeat,
            series_repeat_names,
            params.workflow.steps,
            params.reference_model.k_sol,
            params.reference_model.b_sol,
            params.partiality_threshold,
            mean_i_over_sigma_threshold,
            params.filtering.remove_filtered_reflections,
            deltacchalf,
            params.filtering.stdcutoff,
        )
