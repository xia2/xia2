from __future__ import absolute_import, division, print_function
import os
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Streams import Chatter, Debug


def DialsSpaceGroup(DriverType=None):
    """A factory for DialsSpaceGroupWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsSpaceGroupWrapper(DriverInstance.__class__):
        """A wrapper for dials.space_group"""

        def __init__(self):
            # generic things
            super(DialsSpaceGroupWrapper, self).__init__()

            self.set_executable("dials.space_group")

            # clear all the header junk
            self.reset()

            self._experiments_filename = None
            self._reflections_filename = None
            self._symmetrized_experiments = None

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def get_experiments_filename(self):
            return self._experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def get_reflections_filename(self):
            return self._reflections_filename

        def set_symmetrized_experiments(self, filepath):
            self._symmetrized_experiments = filepath

        def get_symmetrized_experiments(self):
            return self._symmetrized_experiments

        def run(self):
            """Run dials.space_group"""
            self.clear_command_line()

            assert self._experiments_filename
            assert self._reflections_filename
            self.add_command_line(self._reflections_filename)
            self.add_command_line(self._experiments_filename)

            if not self._symmetrized_experiments:
                self._symmetrized_experiments = os.path.join(
                    self.get_working_directory(),
                    "%i_symmetrized.expt" % self.get_xpid(),
                )
            self.add_command_line(
                "output.experiments=%s" % self._symmetrized_experiments
            )

            self.start()
            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
            except Exception:
                Chatter.write(
                    "dials.space_group failed, see log file for more details:\n  %s"
                    % self.get_log_file()
                )
                raise

            Debug.write("dials.space_group status: OK")

    return DialsSpaceGroupWrapper()
