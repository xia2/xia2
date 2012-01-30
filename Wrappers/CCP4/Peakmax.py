#!/usr/bin/env python
# Peakmax.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 31st May 2006
#
# A wrapper for the CCP4 program peakmax
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Peakmax(DriverType = None):
    '''Create a Peakmax instance based on the passed in Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class PeakmaxWrapper(CCP4DriverInstance.__class__):
        '''A wrapper class for converting reflections to mtz.'''

        def __init__(self):
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'peakmax'))

            self._rms = 0.0

        def set_rms(self, rms):
            self._rms = rms
            return

        def peaksearch(self):
            self.check_mapin()
            self.check_xyzout()

            self.start()

            self.input('thresh rms %f' % self._rms)
            self.input('output brookhaven')
            self.close_wait()

            return self.get_ccp4_status()

    return PeakmaxWrapper()

if __name__ == '__main__':

    peakmax = Peakmax()

    peakmax.set_mapin(sys.argv[1])
    peakmax.set_xyzout(sys.argv[2])
    peakmax.set_rms(2.5)

    print peakmax.peaksearch()
