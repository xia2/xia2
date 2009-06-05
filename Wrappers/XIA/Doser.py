#!/usr/bin/env python
# Doser.py
#   Copyright (C) 2009 STFC / Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A program wrapper for "doser" - a jiffy program to add DOSE and TIME
# information to unmerged MTZ files.
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Doser(DriverType = None):
    '''A factory for DoserWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class DoserWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Doser, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things - provides hklin, hklout
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('doser')
            self._doses = { }
            self._times = { }

        def set_doses(self, doses):
            self._doses = doses
            return

        def set_times(self, times):
            self._times = times
            return

        def run(self):
            self.check_hklin()
            self.check_hklout()

            if not self._times and not self._doses:
                raise RuntimeError, 'provide either dose or time'

            batches = None

            if self._doses:
                batches = sorted(self._doses.keys())

            if self._times and not batches:
                batches = sorted(self._times.keys())

            self.start()

            for b in batches:
                d = self._doses.get(b, -1)
                t = self._times.get(b, -1)
            
                self.input('batch %d dose %f time %f' % (b, d, t))

            self.close_wait()

            return
                
    return DoserWrapper()

if __name__ == '__main__':
    # add a test
    pass
