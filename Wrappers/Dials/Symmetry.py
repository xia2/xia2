from __future__ import absolute_import, division, print_function

import json
import math
import os
import shutil
import sys

from cctbx import sgtbx, crystal
from cctbx.sgtbx import bravais_types

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug
from xia2.Handlers.Syminfo import Syminfo
# this was rather complicated - now simpler!
from xia2.lib.SymmetryLib import (clean_reindex_operator, lauegroup_to_lattice,
                                  spacegroup_name_xHM_to_old)
# XDS_ASCII meddling things
from xia2.Modules.XDS_ASCII import remove_misfits
from dxtbx.serialize import load

def DialsSymmetry(DriverType = None):
  '''A factory for DialsSymmetryWrapper classes.'''

  DriverInstance = DriverFactory.Driver(DriverType)

  class DialsSymmetryWrapper(DriverInstance.__class__):
    '''A wrapper for dials.symmetry'''

    def __init__(self):
      # generic things
      super(DialsSymmetryWrapper, self).__init__()

      self.set_executable('dials.symmetry')

      self._input_laue_group = None

      self._experiments_filenames = []
      self._reflections_filenames = []
      self._output_experiments_filename = None
      self._output_reflections_filename = None

      self._hklin = None
      self._hklout = None
      self._pointgroup = None
      self._spacegroup = None
      self._reindex_matrix = None
      self._reindex_operator = None
      self._spacegroup_reindex_matrix = None
      self._spacegroup_reindex_operator = None
      self._confidence = 0.0
      self._hklref = None
      self._xdsin = None
      self._probably_twinned = False
      self._allow_out_of_sequence_files = False

      self._relative_length_tolerance = 0.05
      self._absolute_angle_tolerance = 2

      # space to store all possible solutions, to allow discussion of
      # the correct lattice with the indexer... this should be a
      # list containing e.g. 'tP'
      self._possible_lattices = []

      self._lattice_to_laue = { }

      # all "likely" spacegroups...
      self._likely_spacegroups = []

      # and unit cell information
      self._cell_info = { }
      self._cell = None

      self._json = None

    #def set_hklref(self, hklref):
      #self._hklref = hklref

    def set_hklin(self, hklin):
      self._hklin = hklin

    def get_hklin(self):
      return self._hklin

    def add_experiments(self, experiments):
      self._experiments_filenames.append(experiments)

    def add_reflections(self, reflections):
      self._reflections_filenames.append(reflections)

    def set_experiments_filename(self, experiments_filename):
      self._experiments_filenames = [experiments_filename]

    def set_reflections_filename(self, reflections_filename):
      self._reflections_filenames = [reflections_filename]

    def set_output_experiments_filename(self, experiments_filename):
      self._output_experiments_filename = experiments_filename

    def set_output_reflections_filename(self, reflections_filename):
      self._output_reflections_filename = reflections_filename

    def get_output_reflections_filename(self):
      return self._output_reflections_filename

    def get_output_experiments_filename(self):
      return self._output_experiments_filename

    def set_json(self, json):
      self._json = json

    def set_allow_out_of_sequence_files(self, allow=True):
      self._allow_out_of_sequence_files = allow

    def set_tolerance(self, relative_length_tolerance=0.05, absolute_angle_tolerance=2):
      self._relative_length_tolerance=relative_length_tolerance
      self._absolute_angle_tolerance=absolute_angle_tolerance

    #def get_hklref(self):
      #return self._hklref

    #def check_hklref(self):
      #if self._hklref is None:
        #raise RuntimeError('hklref not defined')
      #if not os.path.exists(self._hklref):
        #raise RuntimeError('hklref %s does not exist' % self._hklref)

    def set_correct_lattice(self, lattice):
      '''In a rerunning situation, set the correct lattice, which will
      assert a correct lauegroup based on the previous run of the
      program...'''

      if self._lattice_to_laue == { }:
        raise RuntimeError('no lattice to lauegroup mapping')

      if lattice not in self._lattice_to_laue:
        raise RuntimeError('lattice %s not possible' % lattice)

      self._input_laue_group = self._lattice_to_laue[lattice]

    def decide_pointgroup(self, ignore_errors=False, batches=None):
      '''Decide on the correct pointgroup for hklin.'''

      self.clear_command_line()

      if self._hklref:
        self.add_command_line('hklref')
        self.add_command_line(self._hklref)

      if self._hklin is not None:
        assert os.path.isfile(self._hklin)
        self.add_command_line("'%s'" % self._hklin)
      else:
        assert self._experiments_filenames# is not None
        assert self._reflections_filenames# is not None
        for exp in self._experiments_filenames:
          self.add_command_line("'%s'" % exp)
        for refl in self._reflections_filenames:
          self.add_command_line("'%s'" % refl)

        if not self._output_experiments_filename:
          self._output_experiments_filename = os.path.join(
            self.get_working_directory(), '%d_reindexed_experiments.json' % self.get_xpid())
        if not self._output_reflections_filename:
          self._output_reflections_filename = os.path.join(
            self.get_working_directory(), '%d_reindexed_reflections.pickle' % self.get_xpid())

        self.add_command_line("output.experiments='%s'" % self._output_experiments_filename)
        self.add_command_line("output.reflections='%s'" % self._output_reflections_filename)

      self.add_command_line('relative_length_tolerance=%s' % self._relative_length_tolerance)
      self.add_command_line('absolute_angle_tolerance=%s' % self._absolute_angle_tolerance)
      if not self._json:
        self._json = os.path.join(self.get_working_directory(),
                                '%d_dials_symmetry.json' % self.get_xpid())

      self.add_command_line("output.json='%s'" % self._json)

      self.start()

      self.close_wait()

      # check for errors
      self.check_for_errors()

      output = self.get_all_output()

      assert os.path.exists(self._json)
      with open(self._json, 'rb') as f:
        d = json.load(f)

      best_solution = d['subgroup_scores'][0]
      patterson_group = sgtbx.space_group(
        str(best_solution['patterson_group']))
      if PhilIndex.params.xia2.settings.symmetry.chirality in (None, 'chiral'):
        patterson_group = patterson_group.build_derived_acentric_group()

      exp = load.experiment_list(
        self.get_output_experiments_filename(), check_format=0)[0]
      unit_cell = exp.crystal.get_unit_cell()
      cs = crystal.symmetry(unit_cell=unit_cell,
        space_group=patterson_group)
      cb_op_best_to_ref = cs.change_of_basis_op_to_reference_setting()
      cs_reference = cs.as_reference_setting()
      self._pointgroup = cs_reference.space_group().type().lookup_symbol()

      self._confidence = best_solution['confidence']
      self._totalprob = best_solution['likelihood']
      cb_op_inp_min = sgtbx.change_of_basis_op(str(d['cb_op_inp_min']))
      cb_op_min_best = sgtbx.change_of_basis_op(str(best_solution['cb_op']))
      cb_op_inp_best = cb_op_min_best * cb_op_inp_min * cb_op_best_to_ref
      self._reindex_operator = cb_op_inp_best.as_xyz()
      self._reindex_matrix = cb_op_inp_best.c().r().as_double()

      if not self._input_laue_group and not self._hklref:
        for score in d['subgroup_scores']:
          patterson_group = sgtbx.space_group(str(score['patterson_group']))
          if PhilIndex.params.xia2.settings.symmetry.chirality in (None, 'chiral'):
            patterson_group = patterson_group.build_derived_acentric_group()
          cs = crystal.symmetry(unit_cell=unit_cell,
            space_group=patterson_group)
          cs_reference = cs.as_reference_setting()
          patterson_group = cs_reference.space_group()

          netzc = score['z_cc_net']
          # record this as a possible lattice if its Z score is positive
          lattice = str(bravais_types.bravais_lattice(
            group=patterson_group))
          if not lattice in self._possible_lattices:
            if netzc > 0.0:
              self._possible_lattices.append(lattice)
            self._lattice_to_laue[lattice] = patterson_group.type().lookup_symbol()
          self._likely_spacegroups.append(patterson_group.type().lookup_symbol())
      return

    def get_reindex_matrix(self):
      return self._reindex_matrix

    def get_reindex_operator(self):
      return self._reindex_operator

    def get_pointgroup(self):
      return self._pointgroup

    def get_cell(self):
      return self._cell

    def get_probably_twinned(self):
      return self._probably_twinned

    #def get_spacegroup(self):
      #return self._spacegroup

    #def get_spacegroup_reindex_operator(self):
      #return self._spacegroup_reindex_operator

    #def get_spacegroup_reindex_matrix(self):
      #return self._spacegroup_reindex_matrix

    # FIXME spacegroup != pointgroup
    decide_spacegroup = decide_pointgroup
    get_spacegroup = get_pointgroup
    get_spacegroup_reindex_operator = get_reindex_operator
    get_spacegroup_reindex_matrix = get_reindex_matrix

    def get_likely_spacegroups(self):
      return self._likely_spacegroups

    def get_confidence(self):
      return self._confidence

    def get_possible_lattices(self):
      return self._possible_lattices

  return DialsSymmetryWrapper()

if __name__ == '__main__':
  p = DialsSymmetry()

  hklin = sys.argv[1]

  p.set_hklin(hklin)

  p.decide_pointgroup()

  pass
