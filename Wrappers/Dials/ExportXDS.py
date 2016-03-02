#!/usr/bin/env python
# ExportXDS.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Export DIALS models for XDS processing.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

def ExportXDS(DriverType = None):
  '''A factory for ExportXDSWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ExportXDSWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.export')

      self._sweep_filename = None
      self._crystal_filename = None

      return

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename
      return

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.export')

      self.clear_command_line()
      self.add_command_line(self._experiments_filename)
      self.add_command_line('format=xds')
      self.start()
      self.close_wait()
      self.check_for_errors()

      return

  return ExportXDSWrapper()

