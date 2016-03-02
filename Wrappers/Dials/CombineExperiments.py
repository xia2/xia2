#!/usr/bin/env python
# CombineExperiments.py
#
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from __future__ import division

import os
from __init__ import _setup_xia2_environ
_setup_xia2_environ()


def CombineExperiments(DriverType = None):
  '''A factory for CombineExperimentsWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class CombineExperimentsWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self._images = []
      self._spot_range = []

      self.set_executable('dials.combine_experiments')

      self._experiments_filenames = []
      self._reflections_filenames = []
      self._combined_experiments_filename = None
      self._combined_reflections_filename = None

      self._same_beam = False
      self._same_crystal = False
      self._same_detector = True
      self._same_goniometer = True

      return

    def add_experiments(self, experiments_filename):
      self._experiments_filenames.append(experiments_filename)
      return

    def get_experiments_filenames(self):
      return self._experiments_filenames

    def add_reflections(self, indexed_filename):
      self._reflections_filenames.append(indexed_filename)
      return

    def get_combined_experiments_filename(self):
      return self._combined_experiments_filename

    def get_combined_reflections_filename(self):
      return self._combined_reflections_filename

    def set_experimental_model(self,
                               same_beam=None,
                               same_crystal=None,
                               same_detector=None,
                               same_goniometer=None):
      if same_beam is not None:
        self._same_beam = same_beam
      if same_crystal is not None:
        self._same_crystal = same_crystal
      if same_detector is not None:
        self._same_detector = same_detector
      if same_goniometer is not None:
        self._same_goniometer = same_goniometer

    def run(self):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.combine_experiments')

      assert len(self._experiments_filenames) > 0
      assert len(self._experiments_filenames) == len(self._reflections_filenames)

      self.clear_command_line()
      for expt in self._experiments_filenames:
        self.add_command_line(expt)
      for f in self._reflections_filenames:
        self.add_command_line(f)
      if self._same_beam:
        self.add_command_line("beam=0")
      if self._same_crystal:
        self.add_command_line("crystal=0")
      if self._same_goniometer:
        self.add_command_line("goniometer=0")
      if self._same_detector:
        self.add_command_line("detector=0")

      self._combined_experiments_filename = os.path.join(
        self.get_working_directory(),
        '%s_combined_experiments.json' % self.get_xpid())
      self.add_command_line(
        'output.experiments_filename=%s' %self._combined_experiments_filename)

      self._combined_reflections_filename = os.path.join(
        self.get_working_directory(),
        '%s_combined_reflections.pickle' % self.get_xpid())
      self.add_command_line(
        'output.reflections_filename=%s' %self._combined_reflections_filename)

      self.start()
      self.close_wait()
      self.check_for_errors()
      return

  return CombineExperimentsWrapper()
