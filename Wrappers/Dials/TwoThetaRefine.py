import logging
import os

import iotbx.cif
import iotbx.cif.model
from dxtbx.model.experiment_list import ExperimentListFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Citations import Citations

logger = logging.getLogger("xia2.Wrappers.Dials.TwoThetaRefine")


def TwoThetaRefine(DriverType=None):
    """A factory for RefineWrapper classes."""
    Citations.cite("dials")

    DriverInstance = DriverFactory.Driver(DriverType)

    class RefineWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("dials.two_theta_refine")
            self._reindexing_operators = None
            self._reindexed_experiments = None
            self._reindexed_reflections = None

            self._experiments = []
            self._reflection_files = []
            self._phil_file = None
            self._combine_crystal_models = True

            # The following are set during run() call:
            self._output_cif = None
            self._output_mmcif = None
            self._output_p4p = None
            self._output_correlation_plot = None
            self._output_experiments = None

            self._crystal = None

        def set_experiments(self, experiments):
            self._experiments = experiments

        def get_experiments(self):
            return self._experiments

        def set_reflection_files(self, reflection_files):
            self._reflection_files = reflection_files

        def set_phil_file(self, phil_file):
            self._phil_file = phil_file

        def set_combine_crystal_models(self, combine_crystal_models):
            self._combine_crystal_models = combine_crystal_models

        def get_output_cif(self):
            return self._output_cif

        def get_output_mmcif(self):
            return self._output_mmcif

        def set_output_p4p(self, filename):
            self._output_p4p = filename

        def get_output_experiments(self):
            return self._output_experiments

        def get_reindexed_experiments(self):
            return self._reindexed_experiments

        def get_reindexed_reflections(self):
            return self._reindexed_reflections

        def get_unit_cell(self):
            return self._crystal.get_recalculated_unit_cell().parameters()

        def get_unit_cell_esd(self):
            return self._crystal.get_recalculated_cell_parameter_sd()

        def set_reindex_operators(self, operators):
            assert len(operators) == len(self._experiments)
            self._reindexing_operators = operators

        def run(self):
            if self._reindexing_operators:
                logger.debug("Reindexing sweeps for dials.two_theta_refine")
                from xia2.lib.bits import auto_logfiler
                from xia2.Wrappers.Dials.Reindex import Reindex

                self._reindexed_experiments, self._reindexed_reflections = [], []
                for e, p, op in zip(
                    self._experiments,
                    self._reflection_files,
                    self._reindexing_operators,
                ):
                    reindexer = Reindex()
                    reindexer.set_cb_op(op)
                    reindexer.set_experiments_filename(e)
                    reindexer.set_indexed_filename(p)
                    reindexer.set_working_directory(self.get_working_directory())
                    auto_logfiler(reindexer)
                    reindexer.run()
                    self._reindexed_experiments.append(
                        reindexer.get_reindexed_experiments_filename()
                    )
                    self._reindexed_reflections.append(
                        reindexer.get_reindexed_reflections_filename()
                    )

            logger.debug("Running dials.two_theta_refine")

            self._output_cif = os.path.join(
                self.get_working_directory(),
                "%s_dials.two_theta_refine.cif" % self.get_xpid(),
            )
            self._output_mmcif = os.path.join(
                self.get_working_directory(),
                "%s_dials.two_theta_refine.mmcif" % self.get_xpid(),
            )
            if not self._output_p4p:
                self._output_p4p = os.path.join(
                    self.get_working_directory(),
                    "%s_dials.two_theta_refine.p4p" % self.get_xpid(),
                )
            self._output_correlation_plot = os.path.join(
                self.get_working_directory(),
                "%s_dials.two_theta_refine.png" % self.get_xpid(),
            )
            self._output_experiments = os.path.join(
                self.get_working_directory(), "%s_refined_cell.expt" % self.get_xpid()
            )

            self.clear_command_line()

            if self._reindexing_operators:
                for experiment in self._reindexed_experiments:
                    self.add_command_line(experiment)
                for reflection_file in self._reindexed_reflections:
                    self.add_command_line(reflection_file)
            else:
                for experiment in self._experiments:
                    self.add_command_line(experiment)
                for reflection_file in self._reflection_files:
                    self.add_command_line(reflection_file)
            self.add_command_line(
                "combine_crystal_models=%s" % self._combine_crystal_models
            )
            self.add_command_line("output.cif=%s" % self._output_cif)
            self.add_command_line("output.mmcif=%s" % self._output_mmcif)
            self.add_command_line("output.p4p=%s" % self._output_p4p)
            if self._output_correlation_plot is not None:
                self.add_command_line(
                    "output.correlation_plot.filename=%s"
                    % self._output_correlation_plot
                )
            if self._output_experiments is not None:
                self.add_command_line(
                    "output.experiments=%s" % self._output_experiments
                )
            if self._phil_file is not None:
                self.add_command_line(self._phil_file)

            self.start()
            self.close_wait()

            if not os.path.isfile(self._output_cif):
                logger.warning(
                    "TwoTheta refinement failed, see log file for more details:\n  %s",
                    self.get_log_file(),
                )
                raise RuntimeError("unit cell not refined")

            self.check_for_errors()

            experiments = ExperimentListFactory.from_json_file(
                self.get_output_experiments(), check_format=False
            )
            self._crystal = experiments.crystals()[0]

        def import_cif(self):
            """Import relevant lines from .cif output"""
            cif = iotbx.cif.reader(file_path=self.get_output_cif()).model()
            block = cif["two_theta_refine"]
            subset = {
                k: block[k] for k in block.keys() if k.startswith(("_cell", "_diffrn"))
            }
            return subset

        def import_mmcif(self):
            """Import relevant lines from .mmcif output"""
            if os.path.isfile(self.get_output_mmcif()):
                cif = iotbx.cif.reader(file_path=self.get_output_mmcif()).model()
                block = cif["two_theta_refine"]
            else:
                block = iotbx.cif.model.block()
            subset = {
                k: block[k] for k in block.keys() if k.startswith(("_cell", "_diffrn"))
            }
            return subset

    return RefineWrapper()
