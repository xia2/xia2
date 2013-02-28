#!/usr/bin/env python
# Freerflag.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 31st May 2006
# 
# A wrapper for the CCP4 program freerflag
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Freerflag(DriverType = None):
    '''Create a Freerflag instance based on the passed in Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class FreerflagWrapper(CCP4DriverInstance.__class__):
        '''A wrapper class for adding freer flags to mtz files.'''

        def __init__(self):
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable('freerflag')

        def freerflag(self):
            self.check_hklin()
            self.check_hklout()

            self.set_task('Adding freer flag column to %s => %s' % \
                          (os.path.split(self.getHklin())[-1],
                           os.path.split(self.getHklout())[-1]))

            self.start()
            self.close_wait()

            return self.get_ccp4_status()


    return FreerflagWrapper()

if __name__ == '__main__':

    f = Freerflag()

    f.set_hklin('temp2.mtz')
    f.set_hklout('1vpj-phased.mtz')

    status = f.freerflag()

    print status
