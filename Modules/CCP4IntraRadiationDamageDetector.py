#!/usr/bin/env python
# CCP4IntraRadiationDamageDetector.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 29th March 2007
# 
# A detector of radiation damage within a sweep, defined by the B factor
# and R merge values from Scala. Note well :
#
#  - if B factor < -10 is "damaged" [pre]
#  - if R merge > ??? is "damaged" [gw]
#
# Second of these is more interesting for MAD data...
#
# Input:
# 
# Dictionary of lists of B factor, R merge vs. batch. Will need to balance
# truncation of batches against completeness so perhaps this should be 
# allowed to perform the actual scaling? Probably a better idea. Do this
# prior to "full" scaling...
# 
# Link also to "inter" radiation damage detection.
#
# Output:
# 
# List of "allowed" batches to use for different wavelengths.
# 
# Notes:
# 
# This may also need to know about (in some detail) how the images were
# collected e.g. mapping of RUN.BATCH -> time so that proper advice 
# about what to eliminate can be provided (e.g. fed back to the integraters.)
# 
# Test data:
# 
# In $X2TD_ROOT/Test/UnitTest/Modules/IntraRadiationDamage (1VRM) and 
# also InterRadiationDamage (1VPJ) for the latter this should look at the
# R merge vs. batch for the INFL and LREM (interesting stuff happens at
# batch 60 in each case...)
#

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.Scala import Scala as _Scala

class CCP4IntraRadiationDamageDetector:
    '''A class to inspect data for radiation damage within sweeps.'''

    def __init__(self):
        # working directory stuff...

        self._working_directory = os.getcwd()

        
        
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    # factory methods

    def Scala(self):
        '''Create a Scala wrapper from _Scala - set the working directory
        and log file stuff as a part of this...'''
        scala = _Scala()
        scala.set_working_directory(self.get_working_directory())
        auto_logfiler(scala)
        return scala
    
