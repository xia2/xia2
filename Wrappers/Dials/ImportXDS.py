#!/usr/bin/env python
# ImportXDS.py
#
#   Copyright (C) 2016 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Import xds files into dxtbx/dials format

from __future__ import division

import os

def ImportXDS(DriverType = None):
  '''A factory for ImportXDSWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class ImportXDSWrapper(DriverInstance.__class__):

    def __init__(self):
      super(ImportXDSWrapper, self).__init__()

      self.set_executable('dials.import_xds')

      self._spot_xds = None

      self._reflection_filename = None

      return

    def set_spot_xds(self, spot_xds):
      self._spot_xds = spot_xds
      return

    def get_reflection_filename(self):
      return self._reflection_filename

    def run(self):

      self.clear_command_line()

      if self._spot_xds is not None:
        self.add_command_line('%s'%self._spot_xds)
        self.add_command_line('method=reflections')

      self._reflection_filename = 'spot_xds.pickle'
      self.start()
      self.close_wait()
      self.check_for_errors()

      assert os.path.exists(self._reflection_filename), self._reflection_filename

      return

  return ImportXDSWrapper()
