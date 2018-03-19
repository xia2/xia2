#!/usr/bin/env python
# ExportMtz.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Export DIALS integration output in MTZ format.

from __future__ import absolute_import, division, print_function

def ExportMtz(DriverType = None):
  '''A factory for ExportMtzWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ExportMtzWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.export')

      self._experiments_filename = None
      self._reflections_filename = None
      self._mtz_filename = "hklout.mtz"
      self._include_partials = False
      self._keep_partials = False
      self._scale_partials = True

    def set_include_partials(self, include_partials):
      self._include_partials = include_partials

    def set_keep_partials(self, keep_partials):
      self._keep_partials = keep_partials

    def set_scale_partials(self, scale_partials):
      self._scale_partials = scale_partials

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename

    def get_experiments_filename(self):
      return self._experiments_filename

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filename = reflections_filename

    def get_reflections_filename(self):
      return self._reflections_filename

    def set_mtz_filename(self, mtz_filename):
      self._mtz_filename = mtz_filename

    def get_mtz_filename(self):
      return self._mtz_filename

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.export')

      self.clear_command_line()
      self.add_command_line('experiments=%s' % self._experiments_filename)
      self.add_command_line('reflections=%s' % self._reflections_filename)
      self.add_command_line('mtz.hklout=%s' % self._mtz_filename)
      if self._include_partials:
        self.add_command_line('include_partials=true')
      if self._keep_partials:
        self.add_command_line('keep_partials=true')
      self.add_command_line('scale_partials=%s' %self._scale_partials)
      self.add_command_line('ignore_panels=true')
      self.start()
      self.close_wait()
      self.check_for_errors()

  return ExportMtzWrapper()
