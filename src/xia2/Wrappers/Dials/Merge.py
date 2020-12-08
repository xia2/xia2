import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.Merge")


def DialsMerge(DriverType=None):
    """A factory for DialsMergeWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsMergeWrapper(DriverInstance.__class__):
        """A wrapper for dials.merge"""

        def __init__(self):
            # generic things
            super().__init__()

            self.set_executable("dials.merge")

            # clear all the header junk
            self.reset()

            self._experiments_filename = None
            self._reflections_filename = None
            self._mtz_filename = None
            self._truncate = False
            self._project_name = None
            self._crystal_names = None
            self._dataset_names = None
            self._partiality_threshold = None

        def set_partiality_threshold(self, v):
            self._partiality_threshold = v

        def set_project_name(self, name):
            self._project_name = name

        def set_crystal_names(self, names):
            self._crystal_names = names

        def set_dataset_names(self, names):
            self._dataset_names = names

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def get_experiments_filename(self):
            return self._experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def get_reflections_filename(self):
            return self._reflections_filename

        def set_mtz_filename(self, filename):
            self._mtz_filename = filename

        def get_mtz_filename(self):
            return self._mtz_filename

        def run(self):
            """Run dials.merge"""
            self.clear_command_line()

            assert self._experiments_filename
            assert self._reflections_filename
            self.add_command_line(self._reflections_filename)
            self.add_command_line(self._experiments_filename)

            self.add_command_line("truncate=%s" % self._truncate)

            if self._mtz_filename:
                self.add_command_line("output.mtz=%s" % self._mtz_filename)

            if self._project_name:
                self.add_command_line("output.project_name=%s" % self._project_name)
            if self._crystal_names:
                self.add_command_line("output.crystal_names=%s" % self._crystal_names)
            if self._dataset_names:
                self.add_command_line("output.dataset_names=%s" % self._dataset_names)
            if self._partiality_threshold:
                self.add_command_line(
                    "partiality_threshold=%s" % self._partiality_threshold
                )

            self.start()
            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
            except Exception:
                logger.warning(
                    "dials.merge failed, see log file for more details:\n  %s",
                    self.get_log_file(),
                )
                raise

            logger.debug("dials.merge status: OK")

    return DialsMergeWrapper()
