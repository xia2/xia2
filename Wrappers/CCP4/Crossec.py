#!/usr/bin/env python
# Crossec.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 21st August 2007
#
# A wrapper for the CCP4 program crossec, which is used for guessing f', f''
# given an atom and wavelength. This is only useful away from the edge.
#

import os
import sys
import math
import string
import exceptions

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

# helper functions

def energy_to_wavelength(energy):
    h = 6.6260693e-34
    c = 2.9979246e8
    e = 1.6021765e-19

    return 1.0e10 * (h * c) / (e * energy)

def Crossec(DriverType = None):
    '''Factory for Crossec wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class CrossecWrapper(DriverInstance.__class__):
        def __init__(self):

            DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'crossec'))

            self._atom = None
            self._wavelength = None

            self._fp_fpp = ()

        def set_atom(self, atom):
            self._atom = atom

        def set_wavelength(self, wavelength):
            self._wavelength = wavelength

        def compute_fp_fpp(self, atom = None, wavelength = None):
            if atom:
                self._atom = atom
            if wavelength:
                self._wavelength = wavelength

            if not self._atom:
                raise RuntimeError, 'atom undefined'

            if not self._wavelength:
                raise RuntimeError, 'wavelength undefined'

            self.start()
            self.input('atom %s' % self._atom)
            self.input('nwav 1 %f' % self._wavelength)
            self.input('end')
            self.close_wait()

            output = self.get_all_output()

            for j in range(len(output)):
                line = output[j]

                if line.strip() == 'Lambda  F\'  F" $$':
                    self._fp_fpp = tuple(map(float, output[j + 2].split()[2:]))

            return self._fp_fpp

    return CrossecWrapper()

if __name__ == '__main__':

    crossec = Crossec()

    print '%.2f %.2f' % crossec.compute_fp_fpp('se', 0.9793)
