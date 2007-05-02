#!/usr/bin/env python
# Truncate.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 26th October 2006
# 
# A wrapper for the CCP4 program Truncate, which calculates F's from
# I's and gives a few useful statistics about the data set.
#
# FIXME 26/OCT/06 this needs to be able to take into account the solvent
#                 content of the crystal (at the moment it will be assumed
#                 to be 50%.)
# 
# FIXME 16/NOV/06 need to be able to get the estimates B factor from the
#                 Wilson plot and also second moment stuff, perhaps?

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Truncate(DriverType = None):
    '''A factory for TruncateWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class TruncateWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Truncate, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self._anomalous = False
            self._nres = 0

            self.set_executable('truncate')

            self._b_factor = 0.0

            return

        def set_anomalous(self, anomalous):
            self._anomalous = anomalous
            return

        def truncate(self):
            '''Actually perform the truncation procedure.'''
            
            self.check_hklin()
            self.check_hklout()

            self.start()

            # write the harvest files in the local directory, not
            # in $HARVESTHOME.
            self.input('usecwd')

            if self._anomalous:
                self.input('anomalous yes')
            else:
                self.input('anomalous no')

            if self._nres:
                self.input('nres %d' % self._nres)

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

            # FIXME need to parse the output for interesting things here!

            for line in self.get_all_output():
                if 'Least squares straight line gives' in line:
                    list = line.split()
                    self._b_factor = float(list[7])

            return

        def get_b_factor(self):
            return self._b_factor

    return TruncateWrapper()
