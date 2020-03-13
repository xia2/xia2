from __future__ import absolute_import, division, print_function
import logging

logger = logging.getLogger("xia2.Wrappers.Dials.EstimateResolutionLimit")


def EstimateResolutionLimit(DriverType=None):
    """A factory for EstimateResolutionLimitWrapper classes."""

    from xia2.Driver.DriverFactory import DriverFactory

    DriverInstance = DriverFactory.Driver(DriverType)

    class EstimateResolutionLimitWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.estimate_resolution_limit")

            self._experiments_filename = None
            self._reflections_filename = None
            self._estimated_d_min = None

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def run(self):
            logger.debug("Running dials.estimate_resolution_limit")

            self.clear_command_line()
            self.add_command_line(self._experiments_filename)
            self.add_command_line(self._reflections_filename)

            self.start()
            self.close_wait()
            self.check_for_errors()

            for line in self.get_all_output():
                if line.startswith("estimated d_min:"):
                    self._estimated_d_min = float(line.split(":")[1])

            return self._estimated_d_min

    return EstimateResolutionLimitWrapper()
