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

        self.params: libtbx.phil.scope_extract = phil_scope.extract()
        self.working_directory = working_directory
        self.output_filename = "merged.mtz"

    def set_d_min(self, d_min: float) -> None:
        self.params.d_min = d_min

    def set_wavelength_tolerance(self, wavelength_tolerance: float) -> None:
        self.params.wavelength_tolerance = wavelength_tolerance

    def set_r_free_params(self, r_free_params: libtbx.phil.scope_extract) -> None:
        self.params.r_free_flags = r_free_params

    def set_assess_space_group(self, assess_space_group: bool) -> None:
        self.params.assess_space_group = assess_space_group

    def set_output_filename(self, filename: str) -> None:
        self.output_filename = filename

    @handle_fail
    def run(self, expts: ExperimentList, refls: flex.reflection_table) -> None:
        xia2_logger.debug("Running dials.merge")
        xpid = _get_number()
        logfile = f"{xpid}_dials.merge.log"

        with (
            run_in_directory(self._working_directory),
            log_to_file(logfile) as dials_logger,
            record_step("dials.merge"),
        ):
            dials_logger.info(diff_phil_from_params_and_scope(self.params, phil_scope))
            mtz_obj = merge.merge_data_to_mtz(self.params, expts, refls)
            mtz_obj.write_to_file(self.output_filename)
