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
      self.set_executable('dials.export_mtz')

      self._experiments_filename = None
      self._reflections_filename = None
      self._mtz_filename = "hklout.mtz"
      self._integration_algorithm = "fitrs"

      return

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
      Debug.write('Running dials.export_mtz')

      self.clear_command_line()
      self.add_command_line(self._experiments_filename)
      self.add_command_line(self._reflections_filename)
      self.add_command_line(self._mtz_filename)
      self.start()
      self.close_wait()
      self.check_for_errors()

      return

  return ExportMtzWrapper()

if __name__ == '__main__':
  import sys

  image_file = sys.argv[1]
  scan_ranges = [(int(token.split(',')[0]), int(token.split(',')[1]))
                 for token in sys.argv[2:]]

  from Wrappers.Dials.Import import Import
  from Wrappers.Dials.Spotfinder import Spotfinder
  from Wrappers.Dials.Index import Index
  from Wrappers.Dials.Integrate import Integrate
  from Wrappers.Dials.RefineBravaisSettings import RefineBravaisSettings

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
  rbs = RefineBravaisSettings()
  rbs.set_experiments_filename(indexer.get_experiments_filename())
  rbs.set_indexed_filename(indexer.get_indexed_filename())
  rbs.run()
  print ''.join(rbs.get_all_output())
  print "Done refining"

  print "Begin integrating"
  integrater = Integrate()
  integrater.set_experiments_filename(indexer.get_experiments_filename())
  integrater.set_reflections_filename(indexer.get_indexed_filename())
  integrater.run()
  print ''.join(integrater.get_all_output())
  print "Done integrating"

  print "Begin exporting"
  exporter = ExportMtz()
  exporter.set_experiments_filename(integrater.get_experiments_filename())
  exporter.set_reflections_filename(integrater.get_integrated_filename())
  exporter.run()
  print ''.join(exporter.get_all_output())
  print "Done exporting"
