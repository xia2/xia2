#!/usr/bin/env python
# ExportBest.py
#
#   Copyright (C) 2016 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Export DIALS integration output in MTZ format.

from __future__ import division

from xia2.Handlers.Flags import Flags

def ExportBest(DriverType = None):
  '''A factory for ExportMtzWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ExportBestWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.export')

      self._experiments_filename = None
      self._reflections_filename = None
      self._prefix = 'best'
      return

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename
      return

    def get_experiments_filename(self):
      return self._experiments_filename

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filename = reflections_filename
      return

    def get_reflections_filename(self):
      return self._reflections_filename

    def set_prefix(self, prefix):
      self._prefix = prefix

    def get_prefix(self):
      return self._prefix

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.export')

      self.clear_command_line()
      self.add_command_line('experiments=%s' % self._experiments_filename)
      self.add_command_line('reflections=%s' % self._reflections_filename)
      self.add_command_line('format=best')
      self.add_command_line('best.prefix=%s' %self._prefix)
      self.start()
      self.close_wait()
      self.check_for_errors()

      return

  return ExportBestWrapper()

