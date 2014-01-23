#!/usr/bin/env python
# RefineBravaisSettings.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Refine result of P1 DIALS indexing in all possible settings; publish results.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

def RefineBravaisSettings(DriverType = None):
  '''A factory for RefineBravaisSettingsWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class RefineBravaisSettingsWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.refine_bravais_settings')

      self._sweep_filename = None
      self._crystal_filename = None
      self._indexed_filename = None

      return

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename
      return

    def set_crystal_filename(self, crystal_filename):
      self._crystal_filename = crystal_filename
      return

    def set_indexed_filename(self, indexed_filename):
      self._indexed_filename = indexed_filename
      return

    def get_bravais_summary(self):
      return self._bravais_summary
    
    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.refine_bravais_settings')

      self.clear_command_line()
      self.add_command_line(self._sweep_filename)
      self.add_command_line(self._crystal_filename)
      self.add_command_line(self._indexed_filename)
      self.start()
      self.close_wait()
      self.check_for_errors()

      from json import loads
      self._bravais_summary = loads(open('bravais_summary.json', 'r').read())

      for solution in sorted(self._bravais_summary):
        print solution, self._bravais_summary[solution]
      
      return

  return RefineBravaisSettingsWrapper()

