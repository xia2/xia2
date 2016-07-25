#!/usr/bin/env python
# MultiCrystalAnalysis.py
#
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# wrapper for xia2 MultiCrystalAnalysis module

from __future__ import division
import os

def MultiCrystalAnalysis(DriverType = None):
  '''A factory for MultiCrystalAnalysisWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class MultiCrystalAnalysisWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('cctbx.python')
      self._argv = []
      self._nproc = None
      self._njob = None
      self._mp_mode = None
      self._phil_file = None
      self._clusters = None
      return

    def add_command_line_args(self, args):
      self._argv.extend(args)

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running MultiCrystalAnalysis.py')

      self.clear_command_line()

      from xia2.Modules import MultiCrystalAnalysis as mca_module
      self.add_command_line(mca_module.__file__)

      for arg in self._argv:
        self.add_command_line(arg)
      self.start()
      self.close_wait()
      self.check_for_errors()

      self._clusters_json = os.path.join(
        self.get_working_directory(), 'intensity_clusters.json')
      assert os.path.exists(self._clusters_json)
      import json
      with open(self._clusters_json, 'rb') as f:
        self._dict = json.load(f)
      self._clusters = self._dict['clusters']

      return

    def get_clusters(self):
      return self._clusters

    def get_dict(self):
      return self._dict

  return MultiCrystalAnalysisWrapper()
