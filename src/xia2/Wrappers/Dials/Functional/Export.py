from __future__ import annotations

import logging
from pathlib import Path

import libtbx.phil
from dials.array_family import flex
from dials.command_line.export import export_shelx, phil_scope
from dxtbx.model import ExperimentList
from libtbx import Auto

from xia2.Driver.timing import record_step
from xia2.lib.bits import _get_number
from xia2.Modules.SSX.util import log_to_file, run_in_directory
from xia2.Wrappers.Dials.Functional import diff_phil_from_params_and_scope, handle_fail

xia2_logger = logging.getLogger(__name__)


class Export:
    def __init__(self, working_directory: Path | None = None) -> None:
        if working_directory:
            self._working_directory = working_directory
        else:
            self._working_directory = Path.cwd()

        self._params: libtbx.phil.scope_extract = phil_scope.extract()

        # Default params

        self._params.shelx.hklout = "dials.hkl"
        self._params.shelx.ins = "dials.ins"
        self._params.shelx.composition = "CH"
        self._params.format = "shelx"
        self._params.intensity = ["auto"]
        self._use_xpid = True
        self._unscaled_behaviour = ["profile"]

    def set_output_names(self, output_name: str) -> None:
        self._params.shelx.hklout = output_name + ".hkl"
        self._params.shelx.ins = output_name + ".ins"

    def set_composition(self, composition: str) -> None:
        self._params.shelx.composition = composition

    def set_intensity(self, intensity: list) -> None:
        self._params.intensity = intensity

    @property
    def use_xpid(self) -> bool:
        return self._use_xpid

    @use_xpid.setter
    def use_xpid(self, xpid: bool) -> None:
        self._use_xpid = xpid

    @property
    def unscaled_behaviour(self) -> list[str]:
        return self._unscaled_behaviour

    @unscaled_behaviour.setter
    def unscaled_behaviour(self, intensity: str) -> None:
        self._unscaled_behaviour = [intensity]

    @handle_fail
    def run(self, expts: ExperimentList, refls: flex.reflection_table) -> None:
        xia2_logger.debug("Running dials.export")
        if self._use_xpid:
            self._xpid = _get_number()
            logfile = f"{self._xpid}_dials.export.log"
        else:
            logfile = "dials.export.log"

        with (
            run_in_directory(self._working_directory),
            log_to_file(logfile) as dials_logger,
            record_step("dials.export"),
        ):
            dials_logger.info(diff_phil_from_params_and_scope(self._params, phil_scope))
            # do auto interpreting of intensity choice:
            # note that this may still fail certain checks further down the processing,
            # but these are the defaults to try

            # Note that for shelx output, can only have ONE option - therefore slightly alter this logic from dials.command_line.export

            if self._params.intensity in ([None], [Auto], ["auto"], Auto) and [refls]:
                if ("intensity.scale.value" in [refls][0]) and (
                    "intensity.scale.variance" in [refls][0]
                ):
                    self._params.intensity = ["scale"]
                    dials_logger.info(
                        "Data appears to be scaled, setting intensity = scale"
                    )
                else:
                    self._params.intensity = []
                    if (
                        "intensity.sum.value" in [refls][0]
                        and "intensity.prf.value" in [refls][0]
                    ):
                        self._params.intensity = self.unscaled_behaviour
                    elif "intensity.sum.value" in [refls][0]:
                        self._params.intensity.append("sum")
                    elif "intensity.prf.value" in [refls][0]:
                        self._params.intensity.append("profile")
                    dials_logger.info(
                        f"Data appears to be unscaled, setting intensity = {self._params.intensity[0]}"
                    )
            export_shelx(self._params, expts, [refls])
