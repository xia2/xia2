#!/usr/bin/env python
# ExportMtz.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Export DIALS integration output in MTZ format.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def ExportMtz(DriverType = None):
  '''A factory for ExportMtzWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ExportMtzWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.export')

      self._experiments_filename = None
      self._reflections_filename = None
      self._mtz_filename = "hklout.mtz"
      self._include_partials = False

      return

    def set_include_partials(self, include_partials):
      self._include_partials = include_partials

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

    def set_mtz_filename(self, mtz_filename):
      self._mtz_filename = mtz_filename
      return

    def get_mtz_filename(self):
      return self._mtz_filename

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.export')

      self.clear_command_line()
      self.add_command_line('experiments=%s' % self._experiments_filename)
      self.add_command_line('reflections=%s' % self._reflections_filename)
      self.add_command_line('mtz.hklout=%s' % self._mtz_filename)
      if self._include_partials:
        self.add_command_line('include_partials=true')
      self.start()
      self.close_wait()
      self.check_for_errors()

      return

  return ExportMtzWrapper()
