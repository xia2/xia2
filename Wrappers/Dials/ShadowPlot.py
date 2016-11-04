#!/usr/bin/env python
# ShadowPlot.py
#
#   Copyright (C) 2016 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from __future__ import division

import os

from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

def ShadowPlot(DriverType = None):
  '''A factory for ShadowPlotWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ShadowPlotWrapper(DriverInstance.__class__, FrameProcessor):

    def __init__(self):
      super(ShadowPlotWrapper, self).__init__()

      self.set_executable('dials.shadow_plot')

      self._sweep_filename = None
      self._json_filename = None

      return

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename
      return

    def set_json_filename(self, json_filename):
      self._json_filename = json_filename
      return

    def get_json_filename(self):
      return self._json_filename

    def get_results(self):
      assert (self._json_filename is not None and
              os.path.isfile(self._json_filename))
      import json
      with open(self._json_filename, 'rb') as f:
        results = json.load(f)
      return results

    def run(self):

      self.clear_command_line()

      assert self._sweep_filename is not None
      self.add_command_line('%s' %self._sweep_filename)
      if self._json_filename is not None:
        self.add_command_line('json=%s' %self._json_filename)
      self.add_command_line('mode=1d')
      self.start()
      self.close_wait()
      self.check_for_errors()

      return

  return ShadowPlotWrapper()
