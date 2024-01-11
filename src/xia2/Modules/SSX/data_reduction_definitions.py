from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import iotbx.phil
from cctbx import sgtbx, uctbx
from dials.array_family import flex
from dxtbx.serialize import load


@dataclass(eq=False)
class FilePair:
    _expt: Path
    _refl: Path

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

    def __hash__(self):
        return hash((str(self._expt), str(self._refl)))

    @property
    def expt(self):
        return self._expt

    @property
    def refl(self):
        return self._refl


@dataclass
class ReductionParams:
    space_group: sgtbx.space_group
    batch_size: int = 1000
    nproc: int = 1
    d_min: Optional[float] = None
    anomalous: bool = False
    lattice_symmetry_max_delta: float = 0.5
    cluster_threshold: float = 1000.0
    absolute_angle_tolerance: float = 0.5
    absolute_length_tolerance: float = 0.2
    central_unit_cell: Optional[uctbx.unit_cell] = None
    reference: Optional[Path] = None
    cosym_phil: Optional[Path] = None
    scaling_phil: Optional[Path] = None
    grouping: Optional[Path] = None
    dose_series_repeat: Optional[int] = None
    steps: List[str] = field(default_factory=lambda: ["scale", "merge"])
    reference_ksol: float = 0.35
    reference_bsol: float = 46.0
    partiality_threshold: float = 0.25
    cc_half_limit: Optional[float] = 0.3
    misigma_limit: Optional[float] = 1.0

    @classmethod
    def from_phil(cls, params: iotbx.phil.scope_extract):
        """Construct from xia2.cli.ssx phil_scope."""
        reference = None
        cosym_phil = None
        scaling_phil = None
        grouping = None
        if params.reference:
            reference = Path(params.reference).resolve()
        elif params.scaling.model:
            reference = Path(params.scaling.model).resolve()
        if params.clustering.central_unit_cell and params.clustering.threshold:
            raise ValueError(
                "Only one of clustering.central_unit_cell and clustering.threshold can be specified"
            )
        if params.symmetry.phil:
            cosym_phil = Path(params.symmetry.phil).resolve()
        if params.scaling.phil:
            scaling_phil = Path(params.scaling.phil).resolve()
        if params.grouping:
            grouping = Path(params.grouping).resolve()
        return cls(
            params.symmetry.space_group,
            params.reduction_batch_size,
            params.multiprocessing.nproc,
            params.resolution.d_min,
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
            params.dose_series_repeat,
            params.workflow.steps,
            params.reference_model.k_sol,
            params.reference_model.b_sol,
            params.partiality_threshold,
            params.resolution.cc_half,
            params.resolution.misigma,
        )
