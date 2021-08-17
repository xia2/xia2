import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.ExportXDSASCII")


def ExportXDSASCII(DriverType=None):
    """A factory for ExportXDSASCIISWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class ExportXDSASCIISWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.export")

            self._experiments_filename = None
            self._reflections_filename = None
            self._hkl_filename = "DIALS.HKL"

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def set_hkl_filename(self, hkl_filename):
            self._hkl_filename = hkl_filename

        def get_hkl_filename(self):
            return self._hkl_filename

        def run(self):
            logger.debug("Running dials.export")

            assert self._experiments_filename is not None
            assert self._reflections_filename is not None

            self.clear_command_line()
            self.add_command_line(self._experiments_filename)
            self.add_command_line(self._reflections_filename)
            if self._hkl_filename is not None:
                self.add_command_line("xds_ascii.hklout=%s" % self._hkl_filename)
            self.add_command_line("format=xds_ascii")
            self.start()
            self.close_wait()
            self.check_for_errors()

    return ExportXDSASCIISWrapper()
