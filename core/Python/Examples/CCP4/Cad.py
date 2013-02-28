#!/usr/bin/env python
# Cad.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 31st May 2006
# 
# A wrapper for the CCP4 program cad
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Cad(DriverType = None):
    '''Create a Cad instance based on the passed in Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class CadWrapper(CCP4DriverInstance.__class__):
        '''A wrapper class for rewriting mtz files.'''

        def __init__(self):
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable('cad')

        def cad(self):
            self.check_hklin()
            self.check_hklout()

            # this has to be passed in on a HKLIN1 token
            hklin = self.get_hklin()
            self.set_hklin(None)

            self.add_command_line('hklin1')
            self.add_command_line(hklin)

            self.set_task('Rewriting reflections %s => %s' % 
                      `   (os.path.split(hklin)[-1],
                       `   os.path.split(self.getHklout())[-1]))

            self.start()

            self.input('labin file 1 E1=FP E2=FOM E3=PHIB E4=SIGFP')
            self.input('labout E1=FP E4=SIGFP E3=PHIB E2=FOM')

            self.close_wait()

            # CAD eof looks like "Normal Termination of CAD" - Bummer!
            
            return self.get_ccp4_status().replace(' of CAD', '')

    return CadWrapper()

if __name__ == '__main__':

    c = Cad()

    c.set_hklin('temp.mtz')
    c.set_hklout('temp2.mtz')

    status = c.cad()

    print status
