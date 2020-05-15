import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.ExportXDS")


def ExportXDS(DriverType=None):
    """A factory for ExportXDSWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class ExportXDSWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.export")

            self._sweep_filename = None
            self._crystal_filename = None

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def run(self):
            logger.debug("Running dials.export")

            self.clear_command_line()
            self.add_command_line(self._experiments_filename)
            self.add_command_line("format=xds")
            self.start()
            self.close_wait()
            self.check_for_errors()

    return ExportXDSWrapper()
