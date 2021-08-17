import json
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor


def ShadowPlot(DriverType=None):
    """A factory for ShadowPlotWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShadowPlotWrapper(DriverInstance.__class__, FrameProcessor):
        def __init__(self):
            super().__init__()

            self.set_executable("dials.shadow_plot")

            self._sweep_filename = None
            self._json_filename = None

        def set_sweep_filename(self, sweep_filename):
            self._sweep_filename = sweep_filename

        def set_json_filename(self, json_filename):
            self._json_filename = json_filename

        def get_json_filename(self):
            return self._json_filename

        def get_results(self):
            assert self._json_filename and os.path.isfile(self._json_filename)
            with open(self._json_filename) as fh:
                return json.load(fh)

        def run(self):
            self.clear_command_line()

            assert self._sweep_filename is not None
            self.add_command_line(self._sweep_filename)
            if self._json_filename is not None:
                self.add_command_line("json=%s" % self._json_filename)
            self.add_command_line("mode=1d")
            self.start()
            self.close_wait()
            self.check_for_errors()

    return ShadowPlotWrapper()
