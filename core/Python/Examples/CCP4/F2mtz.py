#!/usr/bin/env python
# F2mtz.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 31st May 2006
# 
# A wrapper for the CCP4 program f2mtz
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def F2mtz(DriverType = None):
    '''Create a F2mtz instance based on the passed in Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class F2mtzWrapper(CCP4DriverInstance.__class__):
        '''A wrapper class for converting reflections to mtz.'''

        def __init__(self):
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable('f2mtz')

            self._cell = None
            self._symmetry = None

        def set_cell(self, cell):
            self._cell = cell

        def set_symmetry(self, symmetry):
            self._symmetry = symmetry

        def f2mtz(self):
            self.check_hklin()
            self.check_hklout()

            if self._symmetry is None:
                raise RuntimeError, 'symmetry not set'

            if self._cell is None:
                raise RuntimeError, 'cell not set'

            self.set_task('Converting reflections to mtz %s => %s' % \
                          (os.path.split(self.getHklin())[-1],
                           os.path.split(self.getHklout())[-1]))

            self.start()

            self.input('cell %f %f %f %f %f %f' % \
                       tuple(map(float, self._cell)))
            self.input('symmetry %s' % self._symmetry)
            self.input('labout H K L FP FOM PHIB SIGFP')
            self.input('CTYPOUT H H H F W P Q')
            
            self.close_wait()

            return self.get_ccp4_status()


    return F2mtzWrapper()

if __name__ == '__main__':

    f = F2mtz()

    f.set_hklin('1vpj.phs')
    f.set_hklout('temp.mtz')
    f.set_cell([51.690000, 51.680000, 157.800000,
                90.000000, 90.000000, 90.000000])
    f.set_symmetry('P43212')

    status = f.f2mtz()

    print status

    
