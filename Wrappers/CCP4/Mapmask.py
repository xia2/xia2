#!/usr/bin/env python
# Mapmask.py
#
#   Copyright (C) 2008 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 23rd December 2008
#
# A wrapper for the CCP4 program mapmask
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Mapmask(DriverType = None):
    '''Create a Mapmask instance based on the passed in Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class MapmaskWrapper(CCP4DriverInstance.__class__):
        '''A wrapper class for converting reflections to mtz.'''

        def __init__(self):
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'mapmask'))

            self._symmetry = None

            return

        def set_symmetry(self, symmetry):
            self._symetry = symmetry
            return

        def mask_asu(self):
            self.check_mapin()
            self.check_mapout()

            self.start()

            if self._symmetry:
                self.input('symmetry %s' % str(self._symmetry))

            self.input('xyzlim asu')

            self.close_wait()

            return self.get_ccp4_status()

        def mask_xyzin(self):
            self.check_mapin()
            self.check_xyzin()

            self.check_mapout()

            self.start()

            if self._symmetry:
                self.input('symmetry %s' % str(self._symmetry))

            self.input('xyzlim asu')

            self.close_wait()

            return self.get_ccp4_status()

    return MapmaskWrapper()

if __name__ == '__main__':

    mapmask = Mapmask()

    mapmask.set_mapin(sys.argv[1])
    mapmask.set_mapout(sys.argv[2])

    print mapmask.mask_asu()
