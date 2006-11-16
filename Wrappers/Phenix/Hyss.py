#!/usr/bin/env python
# Hyss.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
# 
# FIXME 16/NOV/06 this needs to express the interface for substructure
#                 determination.
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Driver.DriverFactory import DriverFactory

def Hyss(DriverType = None):
    '''Factory for Hyss wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class HyssWrapper(DriverInstance.__class__):
        '''A wrapper for the program phenix.hyss, for locating the heavy
        atom substructure from an anomalous data set.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)            
            self.set_executable('phenix.hyss')

            # from the interface I will need to be able to record
            # the input reflection file, the number of heavy atoms
            # to find, the form of the input reflection file if it
            # happens to be hklf3, the type of heavy atoms and the
            # spacegroup...


    return HyssWrapper()



