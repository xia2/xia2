#!/usr/bin/env python
# Mtzutils.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.


#
# 8th November 2006
#
# A wrapper for the CCP4 program Mtzutils, specifically for trimming the
# resolution of an unmerged reflection file...
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Mtzutils(DriverType = None):
    '''A factory for MtzutilsWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class MtzutilsWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Mtzutils, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'mtzutils'))

            self._resolution_limit_high = 0.0
            self._resolution_limit_low = 100.0

            return

        def set_resolution(self, resolution):
            self._resolution_limit_high = resolution

            return

        def edit(self):
            '''Edit the input reflection file by removing the spare (over
            resolution) reflections.'''

            self.check_hklin()
            self.check_hklout()

            self.start()

            self.input('resolution %f %f' % \
                       (self._resolution_limit_high,
                        self._resolution_limit_low))

            self.close_wait()

            # check for generic errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError, e:
                # something went wrong; remove the output file
                try:
                    os.remove(self.get_hklout())
                except:
                    pass
                raise e

            return self.get_ccp4_status()

    return MtzutilsWrapper()
