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
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from XScaleHelpers import generate_resolution_shells_str

from Handlers.Flags import Flags

def XScale(DriverType = None):

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

            # overall information
            self._resolution_shells = ''
            self._cell = None
            self._spacegroup_number = None

            # input reflections information - including grouping information
            # in the same way as the .xinfo files - through the wavelength
            # names, which will be used for the output files.
            self._input_reflection_files = []
            self._input_reflection_wavelength_names = []
            self._input_resolution_ranges = []

            # these are generated at the run time
            self._transposed_input = { }
            self._transposed_input_keys = []

            # decisions about the scaling
            self._crystal = None
            self._zero_dose = False
            self._anomalous = True
            self._merge = False

            return

        def add_reflection_file(self, reflections, wavelength, resolution):
            self._input_reflection_files.append(reflections)
            self._input_reflection_wavelength_names.append(wavelength)
            self._input_resolution_ranges.append(resolution)
            return

        def set_crystal(self, crystal):
            self._crystal = crystal
            return

        def set_zero_dose(self, zero_dose = True):
            self._zero_dose = zero_dose
            return

        def set_anomalous(self, anomalous = True):
            self._anomalous = anomalous
            return

        def _transform_input_files(self):
            '''Transform the input files to an order we can manage.'''

            for j in range(len(self._input_reflection_file)):
                hkl = self._input_reflection_files[j]
                wave = self._input_reflection_wavelength_names[j]
                resol = self._input_resolution_ranges[j]

                if not self._tranposed_input.has_key(wave):
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

        def _generate_resolution_shells(self):
            if len(self._input_resolution_ranges) == 0:
                raise RuntimeError, 'cannot generate resolution ranges'

            dmin = 100.0
            dmax = 0.0

            for r in self._input_resolution_ranges:
                if max(r) > dmax:
                    dmax = max(r)

                if min(r) < dmin:
                    dmin = min(r)

            self._resolution_shells = generate_resolution_shells_str(
                dmax, dmin)

            return

        def _write_xscale_inp(self):
            '''Write xscale.inp.'''

            self._generate_resolution_shells()
            self._transform_input_files()

            xscale_inp = open(os.path.join(self.get_working_directory(),
                                           'XSCALE.INP'), 'r')

            # header information

            xscale_inp.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % \
                             self._parallel)
            xscale_inp.write('RESOLUTION_SHELLS=%s\n' % \
                             self._resolution_shells)
            xscale_inp.write('SPACE_GROUP_NUMBER=%d\n' % \
                             self._spacegroup_number)
            xscale_inp.write('UNIT_CELL_CONSTANTS=')
            xscale_inp.write('%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f\n' % \
                             self._cell)

            # now information about the wavelengths
            for wave in self._transposed_input_keys:
                if self._anomalous:
                    xscale_inp.write(
                        'OUTPUT_FILE=%s.hkl FRIEDEL\'S_LAW=FALSE\n' % wave)
                else:
                    xscale_inp.write(
                        'OUTPUT_FILE=%s.hkl FRIEDEL\'S_LAW=TRUE\n' % wave)
                    
                for j in range(len(self._transposed_input[wave]['hkl'])):
                    
                    # FIXME input file length limited to 50 characters
                    # so will probably need to copy, softlink or use
                    # the relative path. Most likely it will be the
                    # softlink, as this is likely to cause the least
                    # grief, though will involve generating "unique" names.
                    # FIXME this is UNIX specific! But the so is XDS.

                    if os.name == 'nt':
                        raise RuntimeError, \
                              'using softlinks: will fail on windows'

                    new_file = '%s%d.HKL' % (wave, j + 1)
                    os.symlink(self._transposed_input[wave]['hkl'],
                               os.path.join(self.get_working_directory(),
                                            new_file))

                    xscale_inp.write(
                        'INPUT_FILE=%s XDS_ASCII %.2f %.2f\n' % \
                        (new_file,
                         self._transposed_input[wave]['resol'][0],
                         self._transposed_input[wave]['resol'][1]))

                if self._crystal and self._zero_dose:
                    xscale_inp.write('CRYSTAL_NAME=%s\n' % self._crystal)

            xscale_inp.close()
            return

        def run(self):
            '''Actually run XSCALE.'''
                
            self._write_xscale_inp()
            self.start()
            self.close_wait()

            # now look at XSCALE.LP

            return

    return XScaleWrapper()
