from __future__ import annotations

import logging
from pathlib import Path

import libtbx.phil
from dials.command_line.stereographic_projection import (
    calculate_projections,
    phil_scope,
    projections_as_json,
)

from xia2.Driver.timing import record_step
from xia2.lib.bits import _get_number
from xia2.Modules.SSX.util import log_to_file, run_in_directory
from xia2.Wrappers.Dials.Functional import diff_phil_from_params_and_scope, handle_fail

xia2_logger = logging.getLogger(__name__)


class StereographicProjection:
    def __init__(self, working_directory: Path | None = None):
        ## Working directory is where any output (logfiles, datafiles) will be saved
        if working_directory:
            self._working_directory = working_directory
        else:
            self._working_directory = Path.cwd()

        self._params: libtbx.phil.scope_extract = phil_scope.extract()

        # Don't set these on the params as not necessary - unless wanted in diff phil.
        self._json_filename: Path | None = None
        self._labels: list[str] | None = None
        self._logfile: Path | None = None

    @property
    def logfile(self) -> Path | None:
        return self._logfile

    @property
    def hkl(self) -> tuple[int, int, int] | None:
        return self._params.hkl[0] if self._params.hkl else None

    @hkl.setter
    def hkl(self, hkl: tuple[int, int, int]) -> None:
        self._params.hkl = [hkl]
        self._json_filename = (
            self._working_directory
            / f"stereographic_projection_{hkl[0]}{hkl[1]}{hkl[2]}.json"
        )

    @property
    def labels(self) -> list[str] | None:
        return self._labels

    @labels.setter
    def labels(self, labels: list[str]) -> None:
        self._labels = labels

    @property
    def json_filename(self) -> Path | None:
        return self._json_filename

    @handle_fail
    def run(self, experiments):
        xia2_logger.debug("Running dials.stereographic_projection")
        if not self._params.hkl:
            raise ValueError(
                "No hkl value set in dials.stereographic_projection wrapper"
            )
        xpid = _get_number()
        self._logfile = (
            self._working_directory / f"{xpid}_dials.stereographic_projection.log"
        )
        self._json_filename = self._json_filename.parent / (
            f"{xpid}_" + self._json_filename.name
        )
        with (
            run_in_directory(self._working_directory),
            record_step("dials.stereographic_projection"),
            log_to_file(self._logfile) as dials_logger,
        ):
            dials_logger.info(diff_phil_from_params_and_scope(self._params, phil_scope))
            projections_all, _ = calculate_projections(experiments, self._params)
            projections_as_json(
                projections_all, filename=self._json_filename, labels=self._labels
            )
