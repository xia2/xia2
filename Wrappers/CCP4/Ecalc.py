#!/usr/bin/env python
# Ecalc.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 20th June 2007
#

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Ecalc(DriverType = None):
    '''A factory for EcalcWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class EcalcWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Ecalc, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'ecalc'))

            self._labin_f = 'F'
            self._labin_sigf = 'SIGF'

            return

        def set_labin(self, labin_f, labin_sigf):
            self._labin_f = labin_f
            self._labin_sigf = labin_sigf
            return

        def ecalc(self):

            self.check_hklin()
            self.check_hklout()

            self.start()

            self.input('labin FP=%s SIGFP=%s' % (self._labin_f,
                                                 self._labin_sigf))

            self.close_wait()

            # should check for errors etc here

            return


    return EcalcWrapper()
