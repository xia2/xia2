#!/usr/bin/env python
# Spotfinder.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Find spots for autoindexing using the DIALS code; this will probably be
# renamed to Spotfinder at some point.

from __future__ import division

from __init__ import _setup_xia2_environ
_setup_xia2_environ()

from Handlers.Flags import Flags

def Spotfinder(DriverType = None):
  '''A factory for SpotfinderWrapper classes.'''

  from Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class SpotfinderWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.find_spots')

      self._sweep_filename = None
      self._spot_filename = 'strong.pickle'
      self._scan_ranges = []
      self._nspots = 0
      self._phil_file = None

      return

    def set_sweep_filename(self, sweep_filename):
      self._sweep_filename = sweep_filename
      return

    def set_spot_filename(self, spot_filename):
      self._spot_filename = spot_filename
      return

    def get_spot_filename(self):
      return self._spot_filename

    def set_scan_ranges(self, scan_ranges):
      self._scan_ranges = scan_ranges
      return

    def add_scan_range(self, scan_range):
      self._scan_ranges.append(scan_range)
      return

    def get_nspots(self):
      return self._nspots

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def run(self):
      from Handlers.Streams import Debug
      Debug.write('Running dials.find_spots')

      self.clear_command_line()
      self.add_command_line(self._sweep_filename)
      self.add_command_line('-o')
      self.add_command_line(self._spot_filename)
      nproc = Flags.get_parallel()
      self.add_command_line('--nproc=%i' % nproc)
      for scan_range in self._scan_ranges:
        self.add_command_line('scan_range=%d,%d' % scan_range)
      if self._phil_file is not None:
        self.add_command_line("%s" %self._phil_file)
      self.start()
      self.close_wait()
      self.check_for_errors()

      for record in self.get_all_output():
        if record.startswith('Saved') and 'reflections to' in record:
          self._nspots = int(record.split()[1])

      return

  return SpotfinderWrapper()

if __name__ == '__main__':
  import sys

  image_file = sys.argv[1]
  scan_ranges = [(int(token.split(',')[0]), int(token.split(',')[1]))
                 for token in sys.argv[2:]]

  from Wrappers.Dials.Import import Import

  importer = Import()
  importer.setup_from_image(image_file)
  importer.run()

  spotfinder = Spotfinder()
  spotfinder.set_sweep_filename(importer.get_sweep_filename())
  spotfinder.set_scan_ranges(scan_ranges)
  spotfinder.run()

  print spotfinder.get_nspots()
