import logging
import os

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.Reindex")


def Reindex(DriverType=None):
    """A factory for ReindexWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class ReindexWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.reindex")

            self._experiments_filename = None
            self._indexed_filename = None
            self._reference_filename = None
            self._reference_reflections = None
            self._space_group = None
            self._cb_op = None
            self._hkl_offset = None
            self._reindexed_experiments_filename = None
            self._reindexed_reflections_filename = None

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def set_indexed_filename(self, indexed_filename):
            self._indexed_filename = indexed_filename

        def set_reference_filename(self, reference_filename):
            self._reference_filename = reference_filename

        def set_reference_reflections(self, reference_reflections):
            self._reference_reflections = reference_reflections

        def set_space_group(self, space_group):
            self._space_group = space_group

        def set_cb_op(self, cb_op):
            self._cb_op = cb_op

        def set_hkl_offset(self, hkl_offset):
            assert len(hkl_offset) == 3
            self._hkl_offset = hkl_offset

        def get_reindexed_experiments_filename(self):
            return self._reindexed_experiments_filename

        def get_reindexed_reflections_filename(self):
            return self._reindexed_reflections_filename

        def run(self):
            logger.debug("Running dials.reindex")

            wd = self.get_working_directory()

            self.clear_command_line()
            if self._experiments_filename is not None:
                self.add_command_line(self._experiments_filename)
                if not self._reindexed_experiments_filename:
                    self._reindexed_experiments_filename = os.path.join(
                        wd, "%d_reindexed.expt" % self.get_xpid()
                    )
                self.add_command_line(
                    "output.experiments=%s" % self._reindexed_experiments_filename
                )
            if self._indexed_filename is not None:
                self.add_command_line(self._indexed_filename)
                if not self._reindexed_reflections_filename:
                    self._reindexed_reflections_filename = os.path.join(
                        wd, "%d_reindexed.refl" % self.get_xpid()
                    )
                self.add_command_line(
                    "output.reflections=%s" % self._reindexed_reflections_filename
                )
            if self._reference_filename is not None:
                self.add_command_line(
                    "reference.experiments=%s" % self._reference_filename
                )
            if self._reference_reflections is not None:
                self.add_command_line(
                    "reference.reflections=%s" % self._reference_reflections
                )
            if self._cb_op:
                self.add_command_line("change_of_basis_op=%s" % self._cb_op)
            if self._space_group:
                self.add_command_line("space_group=%s" % self._space_group)
            if self._hkl_offset is not None:
                self.add_command_line("hkl_offset=%i,%i,%i" % self._hkl_offset)

            self.start()
            self.close_wait()
            self.check_for_errors()

    return ReindexWrapper()
