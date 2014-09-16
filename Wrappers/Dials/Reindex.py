#!/usr/bin/env python
# Reindex.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Reindex indexing results from DIALS

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def Reindex(DriverType = None):
  '''A factory for ReindexWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ReindexWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.reindex')

      self._experiment_filename = None
      self._indexed_spot_filename = None
      self._space_group = None
      self._cb_op = None

      return

    def set_experiment_filename(self, experiment_filename):
      self._experiment_filename = experiment_filename
      return

    def set_indexed_spot_filename(self, indexed_spot_filename):
      self._indexed_spot_filename = indexed_spot_filename
      return

    def set_space_group(self, space_group):
      self._space_group = space_group
      return

    def set_cb_op(self, cb_op):
      self._cb_op = cb_op
      return

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.reindex')

      self.clear_command_line()
      self.add_command_line(self._experiment_filename)
      self.add_command_line(self._indexed_spot_filename)
      if self._cb_op:
        self.add_command_line("change_of_basis_op=%s" % self._cb_op)
      if self._space_group:
        self.add_command_line("space_group=%s" % self._space_group)

      self.start()
      self.close_wait()
      self.check_for_errors()

      wd = self.get_working_directory()

      import os

      return os.path.join(wd, "experiments_reindexed.pickle"), \
        os.path.join(wd, "reflections_reindexed.pickle")

  return ReindexWrapper()
