import logging
import os

from dials.util.masking import phil_scope
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

logger = logging.getLogger("xia2.Wrappers.Dials.GenerateMask")


def GenerateMask(DriverType=None):
    """A factory for GenerateMaskWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class GenerateMaskWrapper(DriverInstance.__class__, FrameProcessor):
        def __init__(self):
            super().__init__()

            self.set_executable("dials.generate_mask")

            self._input_experiments_filename = None
            self._output_experiments_filename = None
            self._output_mask_filename = None
            self._params = None

        def set_input_experiments(self, experiments_filename):
            self._input_experiments_filename = experiments_filename

        def set_output_experiments(self, experiments_filename):
            self._output_experiments_filename = experiments_filename

        def set_params(self, params):
            self._params = params

        def run(self):
            logger.debug("Running dials.generate_mask")

            self.clear_command_line()

            assert self._params is not None

            working_phil = phil_scope.format(self._params)
            diff_phil = phil_scope.fetch_diff(source=working_phil)
            phil_filename = os.path.join(
                self.get_working_directory(), "%s_mask.phil" % self.get_xpid()
            )
            with open(phil_filename, "w") as f:
                f.write(diff_phil.as_str())
                f.write(
                    os.linesep
                )  # temporarily required for https://github.com/dials/dials/issues/522

            self.add_command_line(
                "input.experiments=%s" % self._input_experiments_filename
            )
            if self._output_mask_filename is None:
                self._output_mask_filename = os.path.join(
                    self.get_working_directory(), "%s_pixels.mask" % self.get_xpid()
                )
            if self._output_experiments_filename is None:
                self._output_experiments_filename = os.path.join(
                    self.get_working_directory(), "%s_masked.expt" % self.get_xpid()
                )
            self.add_command_line("output.mask=%s" % self._output_mask_filename)
            self.add_command_line(
                "output.experiments=%s" % self._output_experiments_filename
            )
            self.add_command_line(phil_filename)
            self.start()
            self.close_wait()
            self.check_for_errors()
            assert os.path.exists(
                self._output_mask_filename
            ), self._output_mask_filename
            assert os.path.exists(
                self._output_experiments_filename
            ), self._output_experiments_filename
            return self._output_experiments_filename, self._output_mask_filename

    return GenerateMaskWrapper()
