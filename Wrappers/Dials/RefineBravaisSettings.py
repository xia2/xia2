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

      self._experiments_filename = None
      self._indexed_filename = None

      return

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename
      return

    def set_indexed_filename(self, indexed_filename):
      self._indexed_filename = indexed_filename
      return

    def get_bravais_summary(self):
      import copy, os
      bravais_summary = { }
      for k in self._bravais_summary:
        bravais_summary[int(k)] = copy.deepcopy(self._bravais_summary[k])
        bravais_summary[int(k)]['experiments_file'] = os.path.join(
          self.get_working_directory(), 'bravais_setting_%d.json' % int(k))
      return bravais_summary

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.refine_bravais_settings')

      self.clear_command_line()
      self.add_command_line(self._experiments_filename)
      self.add_command_line(self._indexed_filename)

      # some spells to make the refinement work faster...
      
      self.add_command_line('reflections_per_degree=10')
      self.add_command_line('detector.fix=all')
      self.add_command_line('beam.fix=all')
      self.add_command_line('engine=GaussNewtonIterations')
      
      self.start()
      self.close_wait()
      self.check_for_errors()

      from json import loads
      import os
      self._bravais_summary = loads(open(os.path.join(
          self.get_working_directory(), 'bravais_summary.json'), 'r').read())

      return

  return RefineBravaisSettingsWrapper()
