from __future__ import absolute_import, division, print_function

import json
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug


def DialsCosym(DriverType=None, decay_correction=None):
    """A factory for DialsScaleWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsCosymWrapper(DriverInstance.__class__):
        """A wrapper for dials.cosym"""

        def __init__(self):
            # generic things
            super(DialsCosymWrapper, self).__init__()

            self.set_executable("dials.cosym")

            # clear all the header junk
            self.reset()

            # input and output files
            self._experiments_json = []
            self._reflection_files = []

            self._space_group = None
            self._json = None

        # getter and setter methods

        def add_experiments_json(self, experiments_json):
            self._experiments_json.append(experiments_json)

        def add_reflections_file(self, reflections_file):
            self._reflection_files.append(reflections_file)

        def get_reindexed_experiments(self):
            return self._reindexed_experiments

        def get_reindexed_reflections(self):
            return self._reindexed_reflections

        def set_space_group(self, space_group):
            self._space_group = space_group

        def set_json(self, json):
            self._json = json

        def run(self):
            assert len(self._experiments_json)
            assert len(self._reflection_files)
            assert len(self._experiments_json) == len(self._reflection_files)

            for f in self._experiments_json + self._reflection_files:
                assert os.path.isfile(f)
                self.add_command_line(f)

            nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
            if isinstance(nproc, int) and nproc > 1:
                self.add_command_line("nproc=%i" % nproc)

            self._reindexed_experiments = os.path.join(
                self.get_working_directory(), "%i_reindexed.expt" % self.get_xpid()
            )
            self._reindexed_reflections = os.path.join(
                self.get_working_directory(), "%i_reindexed.refl" % self.get_xpid()
            )

            self.add_command_line(
                'output.experiments="%s"' % self._reindexed_experiments
            )
            self.add_command_line(
                'output.reflections="%s"' % self._reindexed_reflections
            )
            self.add_command_line("plot_prefix=%s_" % self.get_xpid())
            if self._space_group is not None:
                self.add_command_line(
                    'space_group="%s"' % self._space_group.type().lookup_symbol()
                )

            if not self._json:
                self._json = os.path.join(
                    self.get_working_directory(),
                    "%d_dials_cosym.json" % self.get_xpid(),
                )
            self.add_command_line("output.json='%s'" % self._json)

            self.start()
            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
            except Exception:
                Chatter.write(
                    "dials.cosym failed, see log file for more details:\n  %s"
                    % self.get_log_file()
                )
                raise

            Debug.write("dials.cosym status: OK")

            assert os.path.exists(self._json)
            with open(self._json, "rb") as f:
                d = json.load(f)
            if self._space_group is None:
                self._best_solution = d["subgroup_scores"][0]
            else:
                self._best_solution = None

            return "OK"

        def get_unmerged_reflection_file(self):
            return self._unmerged_reflections

        def get_best_solution(self):
            return self._best_solution

    return DialsCosymWrapper()
