import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.SplitExperiments")


def SplitExperiments(DriverType=None):
    """A factory for CombineExperimentsWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class SplitExperimentsWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("dials.split_experiments")

            self._experiments_filename = []
            self._reflections_filename = []
            self._experiments_prefix = None
            self._reflections_prefix = None
            self._by_wavelength = False

        def add_experiments(self, experiments_filename):
            self._experiments_filename.append(experiments_filename)

        def add_reflections(self, reflections_filename):
            self._reflections_filename.append(reflections_filename)

        def get_experiments_filename(self):
            return self._experiments_filename

        def get_reflections_filename(self):
            return self._experiments_filename

        def set_by_wavelength(self, boolean):
            self._by_wavelength = boolean

        def run(self):
            logger.debug("Running dials.split_experiments")

            self.clear_command_line()
            assert len(self._experiments_filename) == 1
            assert len(self._experiments_filename) == len(self._reflections_filename)

            self.add_command_line(self._experiments_filename)
            self.add_command_line(self._reflections_filename)

            if not self._experiments_prefix:
                self._experiments_prefix = "split"
            self.add_command_line(
                "output.experiments_prefix=%s" % self._experiments_prefix
            )

            if not self._reflections_prefix:
                self._reflections_prefix = "split"
            self.add_command_line(
                "output.reflections_prefix=%s" % self._reflections_prefix
            )
            if self._by_wavelength:
                self.add_command_line("by_wavelength=True")

            self.start()
            self.close_wait()
            self.check_for_errors()

    return SplitExperimentsWrapper()
