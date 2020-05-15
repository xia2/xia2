import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.AlignCrystal")


def AlignCrystal(DriverType=None):
    """A factory for AlignCrystalWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class AlignCrystalWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.align_crystal")

            self._experiments_filename = None
            self._json_filename = "align_crystal.json"

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def get_experiments_filename(self):
            return self._experiments_filename

        def set_json_filename(self, json_filename):
            self._json_filename = json_filename

        def get_json_filename(self):
            return self._json_filename

        def run(self):
            logger.debug("Running dials.align_crystal")

            self.clear_command_line()
            self.add_command_line("experiments=%s" % self._experiments_filename)
            self.add_command_line("output.json=%s" % self._json_filename)
            self.start()
            self.close_wait()
            self.check_for_errors()

    return AlignCrystalWrapper()
