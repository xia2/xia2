#!/usr/bin/env python
# PlotMultiplicity.py
#
#   Copyright (C) 2017 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# wrapper for xia2.plot_multiplicity

from __future__ import absolute_import, division
import os

def PlotMultiplicity(DriverType = None):
  '''A factory for PlotMultiplicityWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class PlotMultiplicityWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('xia2.plot_multiplicity')
      self._mtz_filename = None
      self._slice_axis = 'h'
      self._slice_index = 0
      self._show_missing = False
      self._plot_filename = None
      self._json_filename = None
      return

    def set_mtz_filename(self, mtz_filename):
      self._mtz_filename = mtz_filename

    def set_slice_axis(self, axis):
      assert axis in ('h', 'k', 'l')
      self._slice_axis = axis

    def set_slice_index(self, index):
      self._slice_index = index

    def set_show_missing(self, show_missing):
      self._show_missing = show_missing

    def get_plot_filename(self):
      return self._plot_filename

    def get_json_filename(self):
      return self._json_filename

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running xia2.plot_multiplicity')
      assert self._mtz_filename is not None

      self.clear_command_line()

      self.add_command_line(self._mtz_filename)
      self.add_command_line('slice_axis=%s' %self._slice_axis)
      self.add_command_line('slice_index=%s' %self._slice_index)
      self.add_command_line('show_missing=%s' %self._show_missing)
      self.add_command_line('uniform_size=True')
      #self._plot_filename = 'multiplicities_%s_%i.png' %(self._slice_axis, self._slice_index)
      #self.add_command_line('plot.filename=%s' %self._plot_filename)
      self.add_command_line('plot.filename=None')
      self._json_filename = 'multiplicities_%s_%i.json' %(self._slice_axis, self._slice_index)
      self.add_command_line('json.filename=%s' %self._json_filename)
      self.start()
      self.close_wait()
      self.check_for_errors()

      #assert os.path.exists(self._plot_filename)
      return

  return PlotMultiplicityWrapper()
