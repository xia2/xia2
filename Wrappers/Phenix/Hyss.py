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

if not os.environ['SS_ROOT'] in sys.path:
    sys.path.append(os.environ['SS_ROOT'])

from Driver.DriverFactory import DriverFactory

from Schema.Interfaces.SubstructureFinder import SubstructureFinder

def Hyss(DriverType = None):
    '''Factory for Hyss wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class HyssWrapper(DriverInstance.__class__,
                      SubstructureFinder):
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

        def _substructure_find_prepare(self):
            '''Prepare data for hyss to work with.'''

            # get the data from the scaler

            # decide what to do with it based on the input format

            # perhaps run something (e.g. shelxc) to prepare the data

            # record the prepared reflection file

            # set the spacegroup if it is not already set

            return

        def _substructure_find(self):
            '''Actually run hyss to find the sites.'''

            # get the prepared reflection file

            # start hyss

            # check that hys has worked ok - if not either
            # (i) change something so it will work fine next time - or -
            # (ii) raise an exception so we get out of teh stuck loop

            # get the output heavy atom pdb file

            # transmogrify it into the standard format

            # return


    return HyssWrapper()



