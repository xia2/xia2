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
import os
import shutil

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

      self._experiment_filename = None
      self._indexed_filename = None

      self._nref = None
      self._rmsd_x = None
      self._rmsd_y = None
      self._rmsd_z = None

      self._max_cell = None
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
      return os.path.join(self.get_working_directory(), 'datablock.json')

    def get_experiments_filename(self):
      return self._experiment_filename

    def get_indexed_filename(self):
      return self._indexed_filename

    def get_p1_cell(self):
      return self._p1_cell

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def get_nref_rmsds(self):
      return self._nref, (self._rmsd_x, self._rmsd_y, self._rmsd_z)

    def set_max_cell(self, max_cell):
      self._max_cell = max_cell
      return

    def run(self, method):
      from Handlers.Streams import Debug
      Debug.write('Running dials.index')

      self.clear_command_line()
      self.add_command_line(self._sweep_filename)
      self.add_command_line(self._spot_filename)
      self.add_command_line('indexing.method=%s' % method)
      self.add_command_line('use_all_reflections=False')
      self.add_command_line('close_to_spindle_cutoff=0.02')
      if self._max_cell:
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

      self._experiment_filename = os.path.join(
        self.get_working_directory(), '%d_experiments.json' %self.get_xpid())
      shutil.copyfile(
        os.path.join(self.get_working_directory(), 'experiments.json'),
        self._experiment_filename)

      self._indexed_filename = os.path.join(
        self.get_working_directory(), '%d_indexed.pickle' %self.get_xpid())
      shutil.copyfile(
        os.path.join(self.get_working_directory(), 'indexed.pickle'),
        self._indexed_filename)

      records = self.get_all_output()

      for i, record in enumerate(records):
        if 'Unit cell:' in record:
          self._p1_cell = map(float, record.replace('(', '').replace(
            ')', '').replace(',', '').split()[-6:])

        if 'Final RMSDs by experiment' in record:
          values = records[i+6].strip().strip('|').split('|')
          if len(values):
            values = [float(v) for v in values]
            if values[0] == 0:
              self._nref = int(values[1])
              self._rmsd_x = values[2]
              self._rmsd_y = values[3]
              self._rmsd_z = values[4]

      return

  return IndexWrapper()

if __name__ == '__main__':
  import sys

  image_file = sys.argv[1]
  scan_ranges = [(int(token.split(',')[0]), int(token.split(',')[1]))
                 for token in sys.argv[2:]]

  from Wrappers.Dials.Import import Import
  from Wrappers.Dials.Spotfinder import Spotfinder
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

