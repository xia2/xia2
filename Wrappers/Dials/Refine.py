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

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor

def Refine(DriverType = None):
  '''A factory for RefineWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class RefineWrapper(DriverInstance.__class__,
                      FrameProcessor):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      FrameProcessor.__init__(self)

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
      self.add_command_line('scan_varying=%s' %self._scan_varying)
      self.add_command_line('use_all_reflections=%s' %self._use_all_reflections)

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
      self._refined_experiments_filename = os.path.join(
        self.get_working_directory(), 'refined_experiments.json')
      return

  return RefineWrapper()

if __name__ == '__main__':
  import sys

  image_file = sys.argv[1]
  scan_ranges = [(int(token.split(',')[0]), int(token.split(',')[1]))
                 for token in sys.argv[2:]]

  from Wrappers.Dials.Import import Import
  from Wrappers.Dials.Spotfinder import Spotfinder
  from Wrappers.Dials.Index import Index

  print "Begin importing"
  importer = Import()
  importer.setup_from_image(image_file)
  importer.set_image_range(scan_ranges[0])
  importer.run()
  print ''.join(importer.get_all_output())
  print "Done importing"

  print "Begin spotfinding"
  spotfinder = Spotfinder()
  spotfinder.set_sweep_filename(importer.get_sweep_filename())
  spotfinder.set_scan_ranges(scan_ranges)
  spotfinder.run()
  print ''.join(spotfinder.get_all_output())
  print "Done spotfinding"

  print "Begin indexing"
  indexer = Index()
  indexer.set_spot_filename(spotfinder.get_spot_filename())
  indexer.set_sweep_filename(importer.get_sweep_filename())
  indexer.run('fft3d')
  print ''.join(indexer.get_all_output())
  print "Done indexing"

  print "Begin refining"
  refiner = Refine()
  refiner.set_experiments_filename(indexer.get_experiments_filename())
  refiner.set_indexed_filename(indexer.get_indexed_filename())
  refiner.set_scan_varying(True)
  refiner.set_use_all_reflections(True)
  refiner.run()
  print ''.join(refiner.get_all_output())
  print "Done refining"
