import logging
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex

logger = logging.getLogger("xia2.Wrappers.Dials.SearchBeamPosition")


def SearchBeamPosition(DriverType=None):
    """A factory for SearchBeamPosition classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class SearchBeamPositionWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.search_beam_position")

            self._sweep_filename = None
            self._spot_filename = None
            self._optimized_filename = None
            self._phil_file = None
            self._image_range = None

        def set_sweep_filename(self, sweep_filename):
            self._sweep_filename = sweep_filename

        def set_spot_filename(self, spot_filename):
            self._spot_filename = spot_filename

        def set_phil_file(self, phil_file):
            self._phil_file = phil_file

        def set_image_range(self, image_range):
            self._image_range = image_range

        def get_optimized_experiments_filename(self):
            return self._optimized_filename

        def run(self):
            logger.debug("Running %s", self.get_executable())

            self.clear_command_line()
            self.add_command_line(self._sweep_filename)
            self.add_command_line(self._spot_filename)
            nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
            self.set_cpu_threads(nproc)
            self.add_command_line("nproc=%i" % nproc)
            if self._image_range:
                self.add_command_line("image_range=%d,%d" % self._image_range)

            if self._phil_file is not None:
                self.add_command_line(self._phil_file)

            self._optimized_filename = os.path.join(
                self.get_working_directory(), "%d_optimised.expt" % self.get_xpid()
            )
            self.add_command_line("output.experiments=%s" % self._optimized_filename)

            self.start()
            self.close_wait()
            self.check_for_errors()

            self.get_all_output()

            assert os.path.exists(self._optimized_filename), self._optimized_filename

    return SearchBeamPositionWrapper()
