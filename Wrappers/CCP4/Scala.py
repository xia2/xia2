#!/usr/bin/env python
# Scala.py
# Maintained by G.Winter
# 5th June 2006
# 
# A wrapper for the CCP4 program Scala, for scaling & merging reflections.
# 
# Provides:
# 
# Scaling of reflection data from Mosflm and other programs.
# Merging of unmerged reflection data.
# Characterisazion of data from scaling statistics.
# 
# Versions:
# 
# Since this will be a complex interface, the first stage is to satisfy the
# most simple scaling requirements, which is to say taking exactly one
# dataset from Mosflm via Sortmtz and scaling this. This will produce
# the appropriate statistics. This corresponds to Simple 1 in the use case
# documentation.
# 
# 
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Scala(DriverType = None):
    '''A factory for ScalaWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class ScalaWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Scala, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.setExecutable('scala')

            # input and output files
            self._scalepack = None

            # scaling parameters
            self._resolution = None

            # scale model
            self._scales_file = None
            self._onlymerge = False

            self._bfactor = False
            self._anomalous = False
            self._tails = False
            self._mode = 'rotation'
            self._spacing = 5
            self._secondary = 6
            self._cycles = 20

            # less common parameters - see scala manual page:
            # (C line 1800)
            #
            # "Some alternatives
            #  >> Recommended usual case
            #  scales rotation spacing 5 secondary 6 bfactor off tails
            #
            #  >> If you have radiation damage, you need a Bfactor,
            #  >>  but a Bfactor at coarser intervals is more stable
            #  scales  rotation spacing 5 secondary 6  tails \
            #     bfactor on brotation spacing 20
            #  tie bfactor 0.5 - restraining the Bfactor also helps"

            self._brotation_spacing = 20
            self._bfactor_tie = 0.5
            
            # standard error parameters - now a dictionary to handle
            # multiple runs
            self._sd_parameters = { } 
            self._project_crystal_dataset = { }
            self._runs = []

    return ScalaWrapper()
