from xia2.Driver.DriverFactory import DriverFactory
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor


def EstimateGain(DriverType=None):
    """A factory for EstimateGainWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class EstimateGainWrapper(DriverInstance.__class__, FrameProcessor):
        def __init__(self):
            super().__init__()

            self.set_executable("dials.estimate_gain")

            self._sweep_filename = None
            self._kernel_size = None
            self._gain = None

        def set_sweep_filename(self, sweep_filename):
            self._sweep_filename = sweep_filename

        def set_kernel_size(self, kernel_size):
            self._kernel_size = kernel_size

        def get_gain(self):
            return self._gain

        def run(self):
            self.clear_command_line()

            assert self._sweep_filename is not None
            self.add_command_line(self._sweep_filename)
            if self._kernel_size is not None:
                self.add_command_line("kernel_size=%i,%i" % self._kernel_size)
            self.start()
            self.close_wait()
            self.check_for_errors()

            for line in self.get_all_output():
                if "Estimated gain:" in line:
                    self._gain = float(line.split(":")[-1].strip())

    return EstimateGainWrapper()
