#!/usr/bin/env python
# Shelxc.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
#  
# A wrapper for SHELXC from the SHELX phasing package. SHELXC prepares 
# the data for substructure determination, and needs to know the "names"
# of the different data sets, e.g. PEAK INFL LREM HREM NATIVE.
# For this to work it is assumed that these will be the dataset (e.g.
# wavelength) names provided.
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Driver.DriverFactory import DriverFactory

def Shelxc(DriverType = None):
    '''Create a Shelxc instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShelxcWrapper(DriverInstance.__class__):
        '''A wrapper class for Shelxc.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('shelxc')

            # input files
            self._infl = None
            self._lrem = None
            self._peak = None
            self._hrem = None
            self._sad = None
            self._native = None

            # heavy atom information
            self._n_sites = 0

            # cell and symmetry
            self._cell = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            self._symmetry = None

            # naming information
            self._name = None

            # control information for shelxd (which will go in through the
            # .ins file)

            self._ntry = 20
            self._mind = 3.5

            # output information
            self._fa_hkl = None

            return

        def set_cell(self, cell):
            self._cell = cell
            return

        def set_symmetry(self, symmetry):
            self._symmetry = symmetry
            return

        def set_n_sites(self, n_sites):
            self._n_sites = n_sites
            return

        def set_peak(self, peak):
            self._peak = peak
            return

        def set_infl(self, infl):
            self._infl = infl
            return

        def set_lrem(self, lrem):
            self._lrem = lrem
            return

        def set_hrem(self, hrem):
            self._hrem = hrem
            return

        def set_native(self, native):
            self._native = native
            return

        def set_sad(self, sad):
            self._sad = sad
            return

        def set_name(self, name):
            self._name = name
            return

        def prepare(self):
            '''Prepare the experimental phasing data.'''

            self.add_command_line(self._name)

            self.start()

            if self._peak:
                self.input('PEAK %s\n' % self._peak)
            if self._infl:
                self.input('INFL %s\n' % self._infl)
            if self._hrem:
                self.input('HREM %s\n' % self._hrem)
            if self._lrem:
                self.input('LREM %s\n' % self._lrem)
            if self._sad:
                self.input('SAD %s\n' % self._sad)
            if self._native:
                self.input('NATIVE %s\n' % self._native)
            
            self.input('CELL %f %f %f %f %f %f' % tuple(self._cell))
            self.input('SPAG %s' % self._symmetry)
            self.input('FIND %d' % self._n_sites)
            self.input('NTRY %d' % self._ntry)
            self.input('MIND %f' % (-1.0 * self._mind))

            self.close_wait()

            # perform checks here for errors...

            self.check_for_errors()

            for line in self.get_all_output():
                if 'Reflections written' in line and 'SHELXD/E' in line:
                    self._fa_hkl = line.split()[5]

            return

        def get_fa_hkl(self):
            return self._fa_hkl

    return ShelxcWrapper()
