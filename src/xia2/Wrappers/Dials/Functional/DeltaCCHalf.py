from __future__ import annotations

from pathlib import Path
from typing import Any

import libtbx.phil
from dials.algorithms.statistics.cc_half_algorithm import CCHalfFromDials
from dials.array_family import flex
from dials.command_line.compute_delta_cchalf import phil_scope
from dxtbx.model import ExperimentList

from xia2.Driver.timing import record_step
from xia2.lib.bits import _get_number
from xia2.Modules.DeltaCcHalf import DeltaCcHalf as xia2DeltaCcHalf
from xia2.Modules.SSX.util import log_to_file, run_in_directory
from xia2.Wrappers.Dials.Functional import diff_phil_from_params_and_scope


class DeltaCCHalf:
    def __init__(self, working_directory: Path | None = None):
        ## Working directory is where any output (logfiles, datafiles) will be saved
        if working_directory:
            self._working_directory = working_directory
        else:
            self._working_directory = Path.cwd()

        self.params: libtbx.phil.scope_extract = phil_scope.extract()
        ## Set any defaults

        ## Define outputs which are not part of params
        self._delta_cc_half_graphs: dict[str, dict[str, Any]] = {}
        self._delta_cc_half_table: list[list[str]] = []

    @property
    def delta_cc_half_graphs(self) -> dict[str, dict[str, Any]]:
        return self._delta_cc_half_graphs

    @property
    def delta_cc_half_table(self) -> list[list[str]]:
        return self._delta_cc_half_table

    def run(
        self,
        experiments: ExperimentList,
        reflections: flex.reflection_table,
        log: bool = False,
    ) -> None:
        xpid = _get_number()
        logfile = f"{xpid}_dials.compute_delta_cchalf.log"
        with (
            run_in_directory(self._working_directory),
            record_step("dials.compute_delta_cchalf"),
            log_to_file(logfile) as dials_logger,
        ):
            diff_phil = diff_phil_from_params_and_scope(self.params, phil_scope)
            dials_logger.info(diff_phil)
            runner = CCHalfFromDials(
                self.params,
                experiments,
                reflections,
            )
            runner.algorithm.run()  # Runs the analysis but not any filtering
            self._delta_cc_half_table = runner.get_table(html=True)
            # Calculate normalised values for generating the plots.
            delta_cc_half = flex.double(list(runner.algorithm.cchalf_i.values()))
            mav = flex.mean_and_variance(delta_cc_half)
            normalised = (
                mav.mean() - delta_cc_half
            ) / mav.unweighted_sample_standard_deviation()
            self._delta_cc_half_graphs.update(
                xia2DeltaCcHalf.generate_histogram(normalised)
            )
            self._delta_cc_half_graphs.update(
                xia2DeltaCcHalf.generate_normalised_scores_plot(normalised)
            )
