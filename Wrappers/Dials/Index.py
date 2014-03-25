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
      self._indexing_method = "fft3d"
      self._p1_cell = None
      self._indxr_input_cell = None
      self._indxr_input_lattice = None

      self._max_cell = 250
      self._phil_file = None

      return

    def set_sweep_filename(self, sweep_filename):
      if sweep_filename == 'datablock.json':
        raise RuntimeError, 'chosen sweep name will be overwritten'
      self._sweep_filename = sweep_filename
      return

    def set_spot_filename(self, spot_filename):
      self._spot_filename = spot_filename
      return

    def set_indexer_input_lattice(self, lattice):
      self._indxr_input_lattice = lattice
      return

    def set_indexer_user_input_lattice(self, user):
      self._indxr_user_input_lattice = user
      return

    def set_indexer_input_cell(self, cell):
      if not type(cell) == type(()):
        raise RuntimeError, 'cell must be a 6-tuple de floats'

      if len(cell) != 6:
        raise RuntimeError, 'cell must be a 6-tuple de floats'

      self._indxr_input_cell = tuple(map(float, cell))
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

    def set_indexing_method(self, method):
      self._indexing_method = method
      return

    def set_indexing_method(self):
      return self._indexing_method

    def get_sweep_filename(self):
      import os
      return os.path.join(self.get_working_directory(), 'datablock.json')

    def get_experiments_filename(self):
      import os
      return os.path.join(self.get_working_directory(), 'experiments.json')

    def get_indexed_filename(self):
      import os
      return os.path.join(self.get_working_directory(), 'indexed.pickle')

    def get_p1_cell(self):
      return self._p1_cell

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def run(self, method):
      from Handlers.Streams import Debug
      Debug.write('Running dials.index')

      self.clear_command_line()
      self.add_command_line(self._sweep_filename)
      self.add_command_line(self._spot_filename)
      self.add_command_line('method=%s' % method)
      self.add_command_line('max_cell=%d' % self._max_cell)
      if self._indxr_input_lattice is not None:
        from Experts.SymmetryExpert import lattice_to_spacegroup_number
        self._symm = lattice_to_spacegroup_number(
            self._indxr_input_lattice)
        self.add_command_line('space_group=%s' % self._symm)
      if self._indxr_input_cell is not None:
        self.add_command_line(
          'unit_cell="%s,%s,%s,%s,%s,%s"' %self._indxr_input_cell)
      if self._maximum_spot_error:
        self.add_command_line('maximum_spot_error=%.f' %
                              self._maximum_spot_error)
      if self._detector_fix:
        self.add_command_line('detector.fix=%s' % self._detector_fix)
      if self._beam_fix:
        self.add_command_line('beam.fix=%s' % self._beam_fix)
      if self._phil_file is not None:
        self.add_command_line("%s" %self._phil_file)

      self.start()
      self.close_wait()
      self.check_for_errors()

      for record in self.get_all_output():
        if 'Unit cell:' in record:
          self._p1_cell = map(float, record.replace('(', '').replace(
            ')', '').replace(',', '').split()[-6:])

      return

  return IndexWrapper()

if __name__ == '__main__':
  import sys

  image_file = sys.argv[1]
  scan_ranges = [(int(token.split(',')[0]), int(token.split(',')[1]))
                 for token in sys.argv[2:]]

  from Wrappers.Dials.Import import Import
  from Wrappers.Dials.Spotfinder import Spotfinder
  from Wrappers.Dials.ExportXDS import ExportXDS
  from Wrappers.Dials.RefineBravaisSettings import RefineBravaisSettings

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

  rbs = RefineBravaisSettings()
  rbs.set_crystal_filename(indexer.get_crystal_filename())
  rbs.set_sweep_filename(indexer.get_sweep_filename())
  rbs.set_indexed_filename(indexer.get_indexed_filename())
  rbs.run()

  print 1/0

  exporter = ExportXDS()
  exporter.set_crystal_filename(indexer.get_crystal_filename())
  exporter.set_sweep_filename(indexer.get_sweep_filename())
  exporter.run()
