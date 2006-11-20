#!/usr/bin/env python
# Freerflag.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 5th June 2006
# 
# An example of an freerflag CCP4 program wrapper, which can be used as the 
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

def Freerflag(DriverType = None):
    '''A factory for FreerflagWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class FreerflagWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Freerflag, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('freerflag')

        def add_free_flag(self):
            self.check_hklin()
            self.check_hklout()

            self.start()
            self.close_wait()
            self.check_for_errors()
            self.check_ccp4_errors()
            
            return
        
    return FreerflagWrapper()

