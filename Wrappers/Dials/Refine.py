#!/usr/bin/env python
# Refine.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Assign indices to reflection centroids given a crystal model

from __future__ import division

import os
from __init__ import _setup_xia2_environ
_setup_xia2_environ()

def Refine(DriverType = None):
  '''A factory for RefineWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class RefineWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)

      self._images = []
      self._spot_range = []

      self.set_executable('dials.refine')

      self._experiments_filename = None
      self._indexed_filename = None
      self._refined_experiments_filename = None
      self._scan_varying = False
      self._use_all_reflections = False
      self._fix_beam = False
      self._fix_detector = False
      self._reflections_per_degree = None
      self._interval_width_degrees = None
      self._phil_file = None

      return

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filename = experiments_filename
      return

    def get_experiments_filename(self):
      return self._experiments_filename

    def set_indexed_filename(self, indexed_filename):
      self._indexed_filename = indexed_filename
      return

    def set_refined_filename(self, refined_filename):
      self._refined_filename = refined_filename
      return

    def get_refined_filename(self):
      return self._refined_filename

    def get_refined_experiments_filename(self):
      return self._refined_experiments_filename

    def set_scan_varying(self, scan_varying):
      self._scan_varying = scan_varying

    def get_scan_varying(self):
      return self._scan_varying

    def set_use_all_reflections(self, use_all_reflections):
      self._use_all_reflections = use_all_reflections

    def get_use_all_reflections(self):
      return self._use_all_reflections

    def set_fix_detector(self, fix):
      self._fix_detector = fix

    def set_fix_beam(self, fix):
      self._fix_beam = fix

    def set_reflections_per_degree(self, reflections_per_degree):
      self._reflections_per_degree = int(reflections_per_degree)

    def set_interval_width_degrees(self, interval_width_degrees):
      self._interval_width_degrees = interval_width_degrees

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.refine')

      self.clear_command_line()
      self.add_command_line(self._experiments_filename)
      self.add_command_line(self._indexed_filename)
      self.add_command_line('scan_varying=%s' % self._scan_varying)
      self.add_command_line('use_all_reflections=%s' % \
                            self._use_all_reflections)
      self.add_command_line('close_to_spindle_cutoff=0.05')

      self._refined_experiments_filename = os.path.join(
        self.get_working_directory(),
        '%s_refined_experiments.json' % self.get_xpid())
      self.add_command_line(
        'output.experiments=%s' % self._refined_experiments_filename)
      self.add_command_line('output.reflections=%s' % self._refined_filename)

      if self._reflections_per_degree is not None:
        self.add_command_line(
          'reflections_per_degree=%i' %self._reflections_per_degree)
      if self._interval_width_degrees is not None:
        self.add_command_line(
          'interval_width_degrees=%i' %self._interval_width_degrees)
      if self._fix_detector:
        self.add_command_line('detector.fix=all')
      if self._fix_beam:
        self.add_command_line('beam.fix=all')
      if self._phil_file is not None:
        self.add_command_line('%s' %self._phil_file)

      self.start()
      self.close_wait()
      self.check_for_errors()
      return

  return RefineWrapper()
