import logging
import os

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Cctbx.BrehmDiederichs")


def BrehmDiederichs(DriverType=None):
    """A factory for BrehmDiederichsWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class BrehmDiederichsWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("cctbx.brehm_diederichs")

            self._input_filenames = []
            self._asymmetric = None
            self._output_filenames = []
            self._reindexing_dict = {}

        def set_input_filenames(self, filenames):
            self._input_filenames = filenames

        def set_asymmetric(self, asymmetric):
            self._asymmetric = asymmetric

        def get_reindexing_dict(self):
            return self._reindexing_dict

        def run(self):
            logger.debug("Running cctbx.brehm_diederichs")

            self.clear_command_line()
            if self._asymmetric is not None:
                assert isinstance(self._asymmetric, int)
                self.add_command_line("asymmetric=%i" % self._asymmetric)
            self.add_command_line("show_plot=False")
            self.add_command_line("save_plot=True")
            for filename in self._input_filenames:
                self.add_command_line(filename)

            self.start()
            self.close_wait()
            self.check_for_errors()

            results_filename = os.path.join(self.get_working_directory(), "reindex.txt")
            assert os.path.exists(results_filename)
            with open(results_filename, "rb") as f:
                for line in f.readlines():
                    filename, reindex_op = line.strip().rsplit(" ", 1)
                    self._reindexing_dict[os.path.abspath(filename)] = reindex_op

    return BrehmDiederichsWrapper()
