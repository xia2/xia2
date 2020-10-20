import logging
import os

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.CombineExperiments")


def CombineExperiments(DriverType=None):
    """A factory for CombineExperimentsWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class CombineExperimentsWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self._images = []
            self._spot_range = []

            self.set_executable("dials.combine_experiments")

            self._experiments_filenames = []
            self._reflections_filenames = []
            self._combined_experiments_filename = None
            self._combined_reflections_filename = None

            self._same_beam = False
            self._same_crystal = False
            self._same_detector = True
            self._same_goniometer = True

        def add_experiments(self, experiments_filename):
            self._experiments_filenames.append(experiments_filename)

        def add_reflections(self, indexed_filename):
            self._reflections_filenames.append(indexed_filename)

        def get_combined_experiments_filename(self):
            return self._combined_experiments_filename

        def get_combined_reflections_filename(self):
            return self._combined_reflections_filename

        def run(self):
            logger.debug("Running dials.combine_experiments")

            assert len(self._experiments_filenames) > 0
            assert len(self._experiments_filenames) == len(self._reflections_filenames)

            self.clear_command_line()
            for expt in self._experiments_filenames:
                self.add_command_line(expt)
            for f in self._reflections_filenames:
                self.add_command_line(f)
            if self._same_beam:
                self.add_command_line("beam=0")
            if self._same_crystal:
                self.add_command_line("crystal=0")
            if self._same_goniometer:
                self.add_command_line("goniometer=0")
            if self._same_detector:
                self.add_command_line("detector=0")

            if not self._combined_experiments_filename:
                self._combined_experiments_filename = os.path.join(
                    self.get_working_directory(), "%s_combined.expt" % self.get_xpid()
                )
            self.add_command_line(
                "output.experiments_filename=%s" % self._combined_experiments_filename
            )

            if not self._combined_reflections_filename:
                self._combined_reflections_filename = os.path.join(
                    self.get_working_directory(), "%s_combined.refl" % self.get_xpid()
                )
            self.add_command_line(
                "output.reflections_filename=%s" % self._combined_reflections_filename
            )

            self.start()
            self.close_wait()
            self.check_for_errors()

    return CombineExperimentsWrapper()
