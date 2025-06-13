from __future__ import annotations

import logging
from pathlib import Path

import libtbx.phil
from dials.array_family import flex
from dials.command_line import merge
from dials.command_line.merge import phil_scope
from dxtbx.model import ExperimentList

from xia2.Driver.timing import record_step
from xia2.lib.bits import _get_number
from xia2.Modules.SSX.util import log_to_file, run_in_directory
from xia2.Wrappers.Dials.Functional import diff_phil_from_params_and_scope, handle_fail

xia2_logger = logging.getLogger(__name__)


class Merge:
    def __init__(self, working_directory: Path | None = None) -> None:
        if working_directory:
            self._working_directory = working_directory
        else:
            self._working_directory = Path.cwd()

        self._params: libtbx.phil.scope_extract = phil_scope.extract()

        # Default params

        self._output_filename = "merged.mtz"
        self._use_xpid = True
        self._params.assess_space_group = False

    def set_d_min(self, d_min: str) -> None:
        self._params.d_min = d_min

    def set_wavelength_tolerance(self, wavelength_tolerance: float) -> None:
        self._params.wavelength_tolerance = wavelength_tolerance

    def set_r_free_params(self, r_free_params: libtbx.phil.scope_extract) -> None:
        self._params.r_free_flags = r_free_params

    def set_assess_space_group(self, assess_space_group: bool) -> None:
        self._params.assess_space_group = assess_space_group

    @property
    def output_filename(self) -> str:
        return self._output_filename

    @output_filename.setter
    def output_filename(self, filename: str) -> None:
        self._output_filename = filename

    @property
    def use_xpid(self) -> bool:
        return self._use_xpid

    @use_xpid.setter
    def use_xpid(self, xpid: bool) -> None:
        self._use_xpid = xpid

    @handle_fail
    def run(self, expts: ExperimentList, refls: flex.reflection_table) -> None:
        xia2_logger.debug("Running dials.merge")
        if self._use_xpid:
            xpid = _get_number()
            logfile = f"{xpid}_dials.merge.log"
        else:
            logfile = "dials.merge.log"

        with (
            run_in_directory(self._working_directory),
            log_to_file(logfile) as dials_logger,
            record_step("dials.merge"),
        ):
            dials_logger.info(diff_phil_from_params_and_scope(self._params, phil_scope))
            mtz_obj = merge.merge_data_to_mtz(self._params, expts, [refls])
            mtz_obj.write_to_file(self.output_filename)
