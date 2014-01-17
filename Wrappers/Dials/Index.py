#!/usr/bin/env python
# Index.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Autoindex using the DIALS code: assumes spots found from same.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def Index(DriverType = None):
  '''A factory for IndexWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class IndexWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.index')

      self._sweep_filename = None
      self._spot_filename = None
      self._unit_cell = None
      self._space_group = None
      self._maximum_spot_error = 3.0
      self._detector_fix = None
      self._beam_fix = None
      
      return

    def set_sweep_filename(self, sweep_filename):
      if sweep_filename == 'sweep.json':
        raise RuntimeError, 'chosen sweep name will be overwritten'
      self._sweep_filename = sweep_filename
      return

    def set_spot_filename(self, spot_filename):
      self._spot_filename = spot_filename
      return

    def set_unit_cell(self, unit_cell):
      self._unit_cell = unit_cell
      return

    def set_space_group(self, space_group):
      self._space_group = space_group
      return

    def set_maximum_spot_error(self, maximum_spot_error):
      self._maximum_spot_error = maximum_spot_error
      return

    def set_detector_fix(self, detector_fix):
      self._detector_fix = detector_fix
      return

    def set_beam_fix(self, beam_fix):
      self._beam_fix = beam_fix
      return
    
    def run(self, method):
      from Handlers.Streams import Debug
      Debug.write('Running dials.index')

      self.clear_command_line()
      self.add_command_line(self._sweep_filename)
      self.add_command_line(self._spot_filename)
      self.add_command_line('method=%s' % method)
      if self._space_group:
        self.add_command_line('space_group=%s' % self._space_group)
      if self._unit_cell:
        self.add_command_line('unit_cell=%s' % self._unit_cell)
      if self._maximum_spot_error:
        self.add_command_line('maximum_spot_error=%.f' % 
                              self._maximum_spot_error)
      if self._detector_fix:
        self.add_command_line('detector.fix=%s' % self._detector_fix)
      if self._beam_fix:
        self.add_command_line('beam.fix=%s' % self._beam_fix)
                              
      self.start()
      self.close_wait()
      self.check_for_errors()

      for record in self.get_all_output():
        print record[:-1]

      return

  return IndexWrapper()

if __name__ == '__main__':
  import sys

  image_file = sys.argv[1]
  scan_ranges = [(int(token.split(',')[0]), int(token.split(',')[1]))
                 for token in sys.argv[2:]]

  from Wrappers.Dials.Import import Import
  from Wrappers.Dials.Spotfinder import Spotfinder

  importer = Import()
  importer.setup_from_image(image_file)
  importer.run()

  spotfinder = Spotfinder()
  spotfinder.set_sweep_filename(importer.get_sweep_filename())
  spotfinder.set_scan_ranges(scan_ranges)
  spotfinder.run()

  indexer = Index()
  indexer.set_spot_filename(spotfinder.get_spot_filename())
  indexer.set_sweep_filename(importer.get_sweep_filename())
  indexer.run('fft3d')
