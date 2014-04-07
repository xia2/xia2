#!/usr/bin/env python
# BrehmDiederichs.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Wrapper for cctbx.brehm_diederichs command.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

def BrehmDiederichs(DriverType = None):
  '''A factory for BrehmDiederichsWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class BrehmDiederichsWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('cctbx.brehm_diederichs')

      self._input_filenames = []
      self._output_filenames = []
      self._reindexing_dict = {}
      return

    def set_input_filenames(self, filenames):
      self._input_filenames = filenames
      return

    def get_output_filenames(self):
      return self._output_filenames

    def get_reindexing_dict(self):
      return self._reindexing_dict

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running cctbx.brehm_diederichs')

      self.clear_command_line()
      self.add_command_line('plot=False')
      for filename in self._input_filenames:
        self.add_command_line(filename)

      self.start()
      self.close_wait()
      self.check_for_errors()

      import os
      results_filename = os.path.join(
          self.get_working_directory(), 'reindex.txt')
      assert os.path.exists(results_filename)
      with open(results_filename, 'rb') as f:
        for line in f.readlines():
          filename, reindex_op = line.strip().rsplit(' ', 1)
          self._reindexing_dict[filename] = reindex_op

      return

  return BrehmDiederichsWrapper()

if __name__ == '__main__':
  import sys
  bd = BrehmDiederichs()
  bd.set_input_filenames(sys.argv[1:])
  bd.run()
  reindexing_dict = bd.get_reindexing_dict()
  for f, cb_op in reindexing_dict.iteritems():
    print f, cb_op
