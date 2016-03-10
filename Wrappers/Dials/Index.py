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

from xia2.Handlers.Flags import Flags

def Index(DriverType = None):
  '''A factory for IndexWrapper classes.'''

  from xia2.Driver.DriverFactory import DriverFactory
  DriverInstance = DriverFactory.Driver(DriverType)

  class IndexWrapper(DriverInstance.__class__):

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('dials.index')

      self._sweep_filenames = []
      self._spot_filenames = []
      self._unit_cell = None
      self._space_group = None
      self._maximum_spot_error = None
      self._detector_fix = None
      self._beam_fix = None
      self._indexing_method = "fft3d"
      self._p1_cell = None
      self._indxr_input_cell = None
      self._indxr_input_lattice = None
      self._reflections_per_degree = None
      self._fft3d_n_points = None

      self._experiment_filename = None
      self._indexed_filename = None

      self._nref = None
      self._rmsd_x = None
      self._rmsd_y = None
      self._rmsd_z = None

      self._max_cell = None
      self._min_cell = None

      self._d_min_start = None

      self._phil_file = None
      self._outlier_algorithm = None
      self._close_to_spindle_cutoff = None

      return

    def add_sweep_filename(self, sweep_filename):
      self._sweep_filenames.append(sweep_filename)
      return

    def add_spot_filename(self, spot_filename):
      self._spot_filenames.append(spot_filename)
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

    def set_reflections_per_degree(self, reflections_per_degree):
      self._reflections_per_degree = int(reflections_per_degree)

    def set_fft3d_n_points(self, n_points):
      self._fft3d_n_points = n_points
      return

    def get_sweep_filenames(self):
      return self._sweep_filenames

    def get_experiments_filename(self):
      return self._experiment_filename

    def get_indexed_filename(self):
      return self._indexed_filename

    def get_p1_cell(self):
      return self._p1_cell

    def set_phil_file(self, phil_file):
      self._phil_file = phil_file
      return

    def set_outlier_algorithm(self, outlier_algorithm):
      self._outlier_algorithm = outlier_algorithm
      return

    def get_nref_rmsds(self):
      return self._nref, (self._rmsd_x, self._rmsd_y, self._rmsd_z)

    def set_max_cell(self, max_cell):
      self._max_cell = max_cell
      return

    def set_min_cell(self, min_cell):
      self._min_cell = min_cell
      return

    def set_d_min_start(self, d_min_start):
      self._d_min_start = d_min_start
      return

    def set_close_to_spindle_cutoff(self, close_to_spindle_cutoff):
      self._close_to_spindle_cutoff = close_to_spindle_cutoff
      return

    def run(self, method):
      from xia2.Handlers.Streams import Debug
      Debug.write('Running dials.index')

      self.clear_command_line()
      for f in self._sweep_filenames:
        self.add_command_line(f)
      for f in self._spot_filenames:
        self.add_command_line(f)
      self.add_command_line('indexing.method=%s' % method)
      nproc = Flags.get_parallel()
      self.set_cpu_threads(nproc)
      self.add_command_line('indexing.nproc=%i' % nproc)
      if Flags.get_small_molecule():
        self.add_command_line('filter_ice=false')
      if self._reflections_per_degree is not None:
        self.add_command_line(
          'reflections_per_degree=%i' %self._reflections_per_degree)
      if self._fft3d_n_points is not None:
        self.add_command_line(
          'fft3d.reciprocal_space_grid.n_points=%i' %self._fft3d_n_points)
      if self._close_to_spindle_cutoff is not None:
        self.add_command_line(
          'close_to_spindle_cutoff=%f' %self._close_to_spindle_cutoff)
      if self._outlier_algorithm:
        self.add_command_line('outlier.algorithm=%s' % self._outlier_algorithm)
      if self._max_cell:
        self.add_command_line('max_cell=%d' % self._max_cell)
      if self._min_cell:
        self.add_command_line('min_cell=%d' % self._min_cell)
      if self._d_min_start:
        self.add_command_line('d_min_start=%f' % self._d_min_start)
      if self._indxr_input_lattice is not None:
        from xia2.Experts.SymmetryExpert import lattice_to_spacegroup_number
        self._symm = lattice_to_spacegroup_number(
            self._indxr_input_lattice)
        self.add_command_line('known_symmetry.space_group=%s' % self._symm)
      if self._indxr_input_cell is not None:
        self.add_command_line(
          'known_symmetry.unit_cell="%s,%s,%s,%s,%s,%s"' %self._indxr_input_cell)
      if self._maximum_spot_error:
        self.add_command_line('maximum_spot_error=%.f' %
                              self._maximum_spot_error)
      if self._detector_fix:
        self.add_command_line('detector.fix=%s' % self._detector_fix)
      if self._beam_fix:
        self.add_command_line('beam.fix=%s' % self._beam_fix)
      if self._phil_file is not None:
        self.add_command_line("%s" %self._phil_file)

      self._experiment_filename = os.path.join(
        self.get_working_directory(), '%d_experiments.json' %self.get_xpid())
      self._indexed_filename = os.path.join(
        self.get_working_directory(), '%d_indexed.pickle' %self.get_xpid())
      self.add_command_line("output.experiments=%s" %self._experiment_filename)
      self.add_command_line("output.reflections=%s" %self._indexed_filename)

      self.start()
      self.close_wait()
      self.check_for_errors()

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
