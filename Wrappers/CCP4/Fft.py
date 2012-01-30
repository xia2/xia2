#!/usr/bin/env python
# Fft.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 31st May 2006
#
# A wrapper for the CCP4 program fft
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Fft(DriverType = None):
    '''Create a Fft instance based on the passed in Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class FftWrapper(CCP4DriverInstance.__class__):
        '''A wrapper class for converting reflections to mtz.'''

        def __init__(self):
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'fft'))

            self._symmetry = None
            self._dmin = 0.0
            self._dmax = 0.0
            self._exclude_term = 0.0
            self._dname = None

        def set_symmetry(self, symmetry):
            if type(symmetry) == type('str'):
                self._symmetry = symmetry.replace(' ', '')
            else:
                self._symmetry = str(symmetry)

            return

        def set_resolution_range(self, dmin, dmax):
            self._dmin = dmin
            self._dmax = dmax
            return

        def set_exclude_term(self, exclude_term):
            self._exclude_term = exclude_term
            return

        def set_dataset(self, dname):
            self._dname = dname
            return

        def patterson(self):
            self.check_hklin()
            self.check_mapout()

            self.start()

            self.input('patterson')

            if self._symmetry:
                self.input('fftspacegroup %s' % str(self._symmetry))

            if self._dmin != 0.0 and self._dmax != 0.0:
                self.input('resolution %.2f %.2f' % (self._dmin, self._dmax))

            if self._exclude_term > 0.0:
                self.input('exclude term %.2f' % self._exclude_term)

            if self._dname:
                self.input('labin F1=DANO_%s SIG1=SIGDANO_%s' % \
                           (self._dname, self._dname))
            else:
                self.input('labin F1=DANO SIG1=SIGDANO')

            self.input('grid sample 3')

            self.close_wait()

            return self.get_ccp4_status()

    return FftWrapper()

if __name__ == '__main__':

    fft = Fft()

    fft.set_hklin(sys.argv[1])
    fft.set_mapout(sys.argv[2])
    fft.set_dataset(sys.argv[3])
    fft.set_resolution_range(40, 1.8)
    fft.set_exclude_term(900.0)

    print fft.patterson()
