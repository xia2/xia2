#!/usr/bin/env python
# Freerflag.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 5th June 2006
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

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'freerflag'))

            self._free_fraction = 0.05

            return

        def set_free_fraction(self, free_fraction):
            self._free_fraction = free_fraction
            return

        def add_free_flag(self):
            self.check_hklin()
            self.check_hklout()

            self.start()
            self.input('freerfrac %.3f' % self._free_fraction)
            self.close_wait()
            self.check_for_errors()
            self.check_ccp4_errors()

            return

        def complete_free_flag(self):
            self.check_hklin()
            self.check_hklout()

            self.start()
            self.input('freerfrac %.3f' % self._free_fraction)
            self.input('complete FREE=FreeR_flag')
            self.close_wait()
            self.check_for_errors()
            self.check_ccp4_errors()

            return

    return FreerflagWrapper()
