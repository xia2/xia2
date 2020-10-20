import json
import os

from xia2.Driver.DriverFactory import DriverFactory


def DetectBlanks(DriverType=None):
    """A factory for DetectBlanksWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DetectBlanksWrapper(DriverInstance.__class__):
        def __init__(self):
            super().__init__()

            self.set_executable("dials.detect_blanks")

            self._sweep_filename = None
            self._experiments_filename = None
            self._reflections_filename = None
            self._json_filename = None
            self._phi_step = None
            self._counts_fractional_loss = None
            self._misigma_fractional_loss = None
            self._results = None

        def set_sweep_filename(self, sweep_filename):
            self._sweep_filename = sweep_filename

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def set_json_filename(self, json_filename):
            self._json_filename = json_filename

        def get_json_filename(self):
            return self._json_filename

        def set_phi_step(self, phi_step):
            self._phi_step = phi_step

        def set_counts_fractional_loss(self, counts_fractional_loss):
            self._counts_fractional_loss = counts_fractional_loss

        def set_misigma_fractional_loss(self, misigma_fractional_loss):
            self._misigma_fractional_loss = misigma_fractional_loss

        def get_results(self):
            return self._results

        def run(self):
            self.clear_command_line()

            if self._sweep_filename is not None:
                self.add_command_line(self._sweep_filename)
            if self._experiments_filename is not None:
                self.add_command_line(self._experiments_filename)
            assert self._reflections_filename is not None
            self.add_command_line(self._reflections_filename)
            if self._json_filename is None:
                self._json_filename = os.path.join(
                    self.get_working_directory(), "%s_blanks.json" % self.get_xpid()
                )
            self.add_command_line("json=%s" % self._json_filename)
            if self._phi_step is not None:
                self.add_command_line("phi_step=%s" % self._phi_step)
            if self._counts_fractional_loss is not None:
                self.add_command_line(
                    "counts_fractional_loss=%s" % self._counts_fractional_loss
                )
            if self._misigma_fractional_loss is not None:
                self.add_command_line(
                    "misigma_fractional_loss=%s" % self._misigma_fractional_loss
                )
            self.start()
            self.close_wait()
            self.check_for_errors()

            assert os.path.exists(self._json_filename), self._json_filename
            with open(self._json_filename) as fh:
                self._results = json.load(fh)

    return DetectBlanksWrapper()
