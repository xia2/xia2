#!/usr/bin/env python
# Combat.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 5th June 2006
# 
# An example of an combat CCP4 program wrapper, which can be used as the 
# base for other wrappers.
# 
# Provides:
# 
# Nothing
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Combat(DriverType = None):
    '''A factory for CombatWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class CombatWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Combat, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('combat')

            self._pname = None
            self._xname = None
            self._dname = None

            return

        def set_project_information(self, pname, xname, dname):
            self._pname = pname
            self._xname = xname
            self._dname = dname
            return

        def run(self):
            '''Actually convert to MTZ.'''

            self.check_hklin()
            self.check_hklout()

            # inspect hklin to decide what format it is...

            format = None
            
            first_char = open(self.get_hklin(), 'r').read(1)
            if first_char == '!':
                # may be XDS
                first_line = open(self.get_hklin(), 'r').readline()
                if 'XDS_ASCII' in first_line:
                    format = 'XDSASCII'

            if not format:
                raise RuntimeError, 'unknown format input file %s' % \
                      self.get_hklin()

            self.start()
            self.input('input %s' % format)
            if format == 'XDSASCII':
                self.input('scale 0.02')
                
            if self._pname and self._xname and self._dname:
                self.input('pname %s' % self._pname)
                self.input('xname %s' % self._xname)
                self.input('dname %s' % self._dname)

            self.close_wait()

            # check the status

            return

    return CombatWrapper()

if __name__ == '__main__':
    # run a test
    c = Combat()

    c.set_hklin('XDS_ASCII.HKL')
    c.set_hklout('temp.mtz')
    c.run()

    
