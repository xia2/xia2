#!/usr/bin/env python
# Truncate.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 26th October 2006
# 
# A wrapper for the CCP4 program Truncate, which calculates F's from
# I's and gives a few useful statistics about the data set.
#
# FIXME 26/OCT/06 this needs to be able to take into account the solvent
#                 content of the crystal (at the moment it will be assumed
#                 to be 50%.)

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
            self.set_executable('truncate')

            return

        def truncate(self):
            '''Actually perform the truncation procedure.'''
            
            self.check_hklin()
            self.check_hklout()

            self.start()

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

            return

    return TruncateWrapper()
