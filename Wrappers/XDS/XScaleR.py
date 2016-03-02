#!/usr/bin/env python
# XScale.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper for XSCALE, the XDS Scaling program.
#

import os
import sys
import copy
import math
import time
import shutil

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from XDS import xds_check_error

from Handlers.Flags import Flags
from Handlers.Streams import Debug
from Handlers.Phil import PhilIndex
from XScaleHelpers import get_correlation_coefficients_and_group

def XScaleR(DriverType = None,
            correct_decay = True,
            correct_absorption = True,
            correct_modulation = True):

  DriverInstance = DriverFactory.Driver(DriverType)

  class XScaleWrapper(DriverInstance.__class__):
    '''A wrapper for wrapping XSCALE.'''

    def __init__(self):

      # set up the object ancestors...
      DriverInstance.__class__.__init__(self)

      # now set myself up...
      self._parallel = Flags.get_parallel()
      if self._parallel <= 1:
        self.set_executable('xscale')
      else:
        self.set_executable('xscale_par')

      self._version = 'new'

      # overall information
      self._resolution_shells = ''
      self._cell = None
      self._spacegroup_number = None
      self._reindex_matrix = None

      # corrections to apply - N.B. default values come from the
      # factory function default arguments...
      self._correct_decay = correct_decay
      self._correct_absorption = correct_absorption
      self._correct_modulation = correct_modulation

      # input reflections information - including grouping information
      # in the same way as the .xinfo files - through the wavelength
      # names, which will be used for the output files.
      self._input_reflection_files = []
      self._input_reflection_wavelength_names = []
      self._input_resolution_ranges = []

      # these are generated at the run time
      self._transposed_input = { }
      self._transposed_input_keys = []

      # output
      self._output_reflection_files = { }
      self._remove = []

      # decisions about the scaling
      self._crystal = None
      self._zero_dose = False
      self._anomalous = True
      self._merge = False

      # scale factor output
      self._scale_factor = 1.0

      # Rmerge values - for the scale model analysis - N.B. get
      # one for each data set, obviously...
      self._rmerges = { }


      return

    def add_reflection_file(self, reflections, wavelength, resolution):
      self._input_reflection_files.append(reflections)
      self._input_reflection_wavelength_names.append(wavelength)
      self._input_resolution_ranges.append(resolution)
      return

    def get_remove(self):
      return self._remove

    def set_crystal(self, crystal):
      self._crystal = crystal
      return

    def set_zero_dose(self, zero_dose = True):
      self._zero_dose = zero_dose
      return

    def set_anomalous(self, anomalous = True):
      self._anomalous = anomalous
      return

    def set_correct_decay(self, correct_decay):
      self._correct_decay = correct_decay
      return

    def set_correct_absorption(self, correct_absorption):
      self._correct_absorption = correct_absorption
      return

    def set_correct_modulation(self, correct_modulation):
      self._correct_modulation = correct_modulation
      return

    def get_output_reflection_files(self):
      '''Get a dictionary of output reflection files keyed by
      wavelength name.'''

      return copy.deepcopy(self._output_reflection_files)

    def _transform_input_files(self):
      '''Transform the input files to an order we can manage.'''

      for j in range(len(self._input_reflection_files)):
        hkl = self._input_reflection_files[j]
        wave = self._input_reflection_wavelength_names[j]
        resol = self._input_resolution_ranges[j]

        if not self._transposed_input.has_key(wave):
          self._transposed_input[wave] = {'hkl':[],
                                          'resol':[]}
          self._transposed_input_keys.append(wave)

        self._transposed_input[wave]['hkl'].append(hkl)
        self._transposed_input[wave]['resol'].append(resol)

      return

    def set_spacegroup_number(self, spacegroup_number):
      self._spacegroup_number = spacegroup_number
      return

    def set_cell(self, cell):
      self._cell = cell
      return

    def set_reindex_matrix(self, reindex_matrix):
      if not len(reindex_matrix) == 12:
        raise RuntimeError, 'reindex matrix must be 12 numbers'
      self._reindex_matrix = reindex_matrix
      return

    def _write_xscale_inp(self):
      '''Write xscale.inp.'''

      self._transform_input_files()

      xscale_inp = open(os.path.join(self.get_working_directory(),
                                     'XSCALE.INP'), 'w')

      # header information

      xscale_inp.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % \
                       self._parallel)
      xscale_inp.write('SPACE_GROUP_NUMBER=%d\n' % \
                       self._spacegroup_number)
      xscale_inp.write('UNIT_CELL_CONSTANTS=')
      xscale_inp.write('%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f\n' % \
                       tuple(self._cell))
      xscale_inp.write(
        'MINIMUM_I/SIGMA=%.1f\n' %PhilIndex.params.xds.xscale.min_isigma)

      if self._reindex_matrix:
        xscale_inp.write(
            'REIDX=%d %d %d %d %d %d %d %d %d %d %d %d\n' % \
            tuple(map(int, self._reindex_matrix)))

      # now information about the wavelengths
      for wave in self._transposed_input_keys:

        self._output_reflection_files[wave] = os.path.join(
            self.get_working_directory(), '%s.HKL' % wave)

        xscale_inp.write(
            'OUTPUT_FILE=%s.HKL ' % wave)
        if self._version == 'new':
          xscale_inp.write('\n')
        if self._anomalous:
          xscale_inp.write('FRIEDEL\'S_LAW=FALSE MERGE=FALSE\n')
          xscale_inp.write('STRICT_ABSORPTION_CORRECTION=TRUE\n')
        else:
          xscale_inp.write('FRIEDEL\'S_LAW=TRUE MERGE=FALSE\n')
        if self._version == 'new':
          xscale_inp.write('\n')

        for j in range(len(self._transposed_input[wave]['hkl'])):

          # FIXME note to self, this should now be a local
          # file which has been placed in here by XDSScaler -
          # should check that the files exists though...

          resolution = self._transposed_input[wave]['resol'][j]

          if resolution[0]:
            xscale_inp.write(
                'INPUT_FILE=%s XDS_ASCII\n' % \
                self._transposed_input[wave]['hkl'][j])
            xscale_inp.write(
                'INCLUDE_RESOLUTION_RANGE= %.2f %.2f\n' % \
                (resolution[1], resolution[0]))

          else:
            xscale_inp.write(
                'INPUT_FILE=%s XDS_ASCII\n' % \
                self._transposed_input[wave]['hkl'][j])

          # FIXME this needs to be removed before being used again
          # in anger!
          # xscale_inp.write('CORRECTIONS=DECAY ABSORPTION\n')

          corrections = 'CORRECTIONS='
          if self._correct_decay:
            corrections += ' DECAY'
          if self._correct_modulation:
            corrections += ' MODULATION'
          if self._correct_absorption:
            corrections += ' ABSORPTION'
          corrections += '\n'

          xscale_inp.write(corrections)

        if self._crystal and self._zero_dose:
          xscale_inp.write('CRYSTAL_NAME=%s\n' % self._crystal)

      xscale_inp.close()
      return

    def run(self):
      '''Actually run XSCALE.'''

      self._write_xscale_inp()

      # copy the input file...
      shutil.copyfile(os.path.join(self.get_working_directory(),
                                   'XSCALE.INP'),
                      os.path.join(self.get_working_directory(),
                                   '%d_XSCALE.INP' % self.get_xpid()))

      self.start()
      self.close_wait()

      # copy the LP file
      shutil.copyfile(os.path.join(self.get_working_directory(),
                                   'XSCALE.LP'),
                      os.path.join(self.get_working_directory(),
                                   '%d_XSCALE.LP' % self.get_xpid()))

      # now look at XSCALE.LP
      xds_check_error(self.get_all_output())

      dname = None

      # get the outlier reflections... and the overall scale factor
      for line in open(os.path.join(
          self.get_working_directory(),
          'XSCALE.LP'), 'r').readlines():
        if '"alien"' in line:
          h, k, l = tuple(map(int, line.split()[:3]))
          z = float(line.split()[4])
          if not (h, k, l, z) in self._remove:
            self._remove.append((h, k, l, z))

        if 'FACTOR TO PLACE ALL DATA SETS TO ' in line:
          self._scale_factor = float(line.split()[-1])

        if 'STATISTICS OF SCALED OUTPUT DATA SET' in line:
          dname = line.split()[-1].replace('.HKL', '')

        if 'total' in line and not dname in self._rmerges:
          if len(line.split()) > 5:
            self._rmerges[dname] = float(
                line.replace('%', '').split()[5])

        # trac #419 - if the data sets are not correctly indexed,
        # throw an exception. N.B. this will only work if the
        # data sets are moderately complete (i.e. there are more
        # than a handful of common reflections) - which may not be
        # the case in MULTICRYSTAL mode.

        if ' !!! WARNING !!! ' in line and \
               'CORRELATION FACTORS ARE DANGEROUSLY SMALL' in line:
          groups = get_correlation_coefficients_and_group(
              os.path.join(self.get_working_directory(),
                           'XSCALE.LP'))
          Debug.write('Low correlations - check data sets')
          for j, name in enumerate(groups):
            Debug.write('Group %d' % j)
            for file_name in groups[name]:
              Debug.write(file_name)

          if not Flags.get_microcrystal():
            raise RuntimeError, 'reindexing error: %s' % \
                  os.path.join(self.get_working_directory(),
                               'XSCALE.LP')

      return

    def get_scale_factor(self):
      return self._scale_factor

    def get_rmerges(self):
      return self._rmerges

  return XScaleWrapper()
