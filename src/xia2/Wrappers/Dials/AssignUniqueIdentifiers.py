import os
from xia2.Driver.DriverFactory import DriverFactory


def DialsAssignIdentifiers(DriverType=None):
    """A factory for DialsSymmetryWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsAssignIdentifiersWrapper(DriverInstance.__class__):
        """A wrapper for dials.symmetry"""

        def __init__(self):
            # generic things
            super().__init__()

            self.set_executable("dials.assign_experiment_identifiers")
            self._experiments_filenames = []
            self._reflections_filenames = []
            self._output_experiments_filename = None
            self._output_reflections_filename = None

        def add_experiments(self, experiments):
            self._experiments_filenames.append(experiments)

        def add_reflections(self, reflections):
            self._reflections_filenames.append(reflections)

        def set_output_experiments_filename(self, experiments_filename):
            self._output_experiments_filename = experiments_filename

        def set_output_reflections_filename(self, reflections_filename):
            self._output_reflections_filename = reflections_filename

        def get_output_reflections_filename(self):
            return self._output_reflections_filename

        def get_output_experiments_filename(self):
            return self._output_experiments_filename

        def assign_identifiers(self):

            self.clear_command_line()
            assert self._experiments_filenames
            assert self._reflections_filenames
            for exp in self._experiments_filenames:
                self.add_command_line(exp)
            for refl in self._reflections_filenames:
                self.add_command_line(refl)

            if not self._output_experiments_filename:
                self._output_experiments_filename = os.path.join(
                    self.get_working_directory(), "%d_assigned.expt" % self.get_xpid()
                )
            if not self._output_reflections_filename:
                self._output_reflections_filename = os.path.join(
                    self.get_working_directory(), "%d_assigned.refl" % self.get_xpid()
                )

            self.add_command_line(
                "output.experiments=%s" % self._output_experiments_filename
            )
            self.add_command_line(
                "output.reflections=%s" % self._output_reflections_filename
            )

            self.start()

            self.close_wait()

            # check for errors
            self.check_for_errors()

            return

    return DialsAssignIdentifiersWrapper()
