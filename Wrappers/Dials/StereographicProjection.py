#!/usr/bin/env python
# StereographicProjection.py
#
#   Copyright (C) 2017 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from __future__ import division

import os
from __init__ import _setup_xia2_environ
_setup_xia2_environ()


def StereographicProjection(DriverType = None):
  '''A factory for StereographicProjectionWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class StereographicProjectionWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self.set_executable('dials.stereographic_projection')

      self._experiments_filenames = []
      self._hkl = None
      return

    def add_experiments(self, experiments_filename):
      self._experiments_filenames.append(experiments_filename)
      return

    def set_hkl(self, hkl):
      assert len(hkl) == 3
      self._hkl = hkl

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.stereographic_projection')

      assert len(self._experiments_filenames) > 0
      assert self._hkl is not None

      self.clear_command_line()
      for expt in self._experiments_filenames:
        self.add_command_line(expt)
      self.add_command_line('frame=laboratory')
      self.add_command_line('plot.show=False')
      self.add_command_line('hkl=%i,%i,%i' %self._hkl)
      self.add_command_line('plot.filename=stereographic_projection_%i%i%i.png' %self._hkl)
      #self.add_command_line('json.filename=stereographic_projection_%i%i%i.json' %self._hkl)

      self.start()
      self.close_wait()
      self.check_for_errors()
      return

  return StereographicProjectionWrapper()
