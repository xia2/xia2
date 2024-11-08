import os
from dials.command_line.cosym import phil_scope as cosym_phil_scope
from dials.command_line.symmetry import phil_scope as symmetry_phil_scope
from dials.util.options import OptionParser
from dials.util.multi_dataset_handling import parse_multiple_datasets
from xia2.Wrappers.Dials.Cosym import DialsCosym
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from __future__ import annotations

import logging
from pathlib import Path

from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import FilePair, scale_on_batches

xia2_logger = logging.getLogger(__name__)


    def _run_symmetry_determination(self) -> None:
        experiments, reflections = parse_multiple_datasets([FilePair(e, r) for e, r in self._batches_to_scale])
        if len(experiments) == 1:
            xia2_logger.info("Only one dataset, using dials.symmetry instead of dials.cosym")
            self._run_dials_symmetry(experiments[0], reflections[0])
        else:
            self._run_dials_cosym(experiments, reflections)

    def _run_dials_symmetry(self, experiments, reflections) -> None:
        symmetry = DialsSymmetry()
        symmetry.set_experiments_filename(experiments)
        symmetry.set_reflections_filename(reflections)
        symmetry.set_working_directory(self._scale_wd)
        auto_logfiler(symmetry)
        symmetry.run()

    def _run_dials_cosym(self, experiments, reflections) -> None:
        cosym = DialsCosym()
        for exp, refl in zip(experiments, reflections):
            cosym.add_experiments_json(exp)
            cosym.add_reflections_file(refl)
        cosym.set_working_directory(self._scale_wd)
        auto_logfiler(cosym)
        cosym.run()

class SimpleDataReduction(BaseDataReduction):
    def _scale(self) -> None:
        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        self._run_symmetry_determination()

        result = scale_on_batches(
            self._scale_wd, self._batches_to_scale, self._reduction_params
        )
        xia2_logger.info("Completed scaling of all data")
        self._files_to_merge = [FilePair(result.exptfile, result.reflfile)]
        FileHandler.record_data_file(result.exptfile)
        FileHandler.record_data_file(result.reflfile)
        FileHandler.record_log_file(result.logfile.name.rstrip(".log"), result.logfile)
