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
from Handlers.Streams import Chatter
from lib.Guff import auto_logfiler, transpose_loggraph

class CCP4IntraRadiationDamageDetector:
    '''A class to inspect data for radiation damage within sweeps.'''

    def __init__(self):
        # working directory stuff...

        self._working_directory = os.getcwd()

        self._hklin = None

        self._sweep_information = { }

    def set_hklin(self, hklin):
        self._hklin = hklin
        return

    def get_hklin(self):
        return self._hklin

    def check_hklin(self):
        if not self._hklin:
            raise RuntimeError, 'hklin not defined'
        return
        
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def set_sweep_information(self, sweep_information):
        self._sweep_information = sweep_information
        return

    # factory methods

    def Scala(self):
        '''Create a Scala wrapper from _Scala - set the working directory
        and log file stuff as a part of this...'''
        scala = _Scala()
        scala.set_working_directory(self.get_working_directory())
        auto_logfiler(scala)
        return scala

    def analyse(self):

        self.check_hklin()

        sc = self.Scala()

        sc.set_hklin(self._hklin)

        # this information will need to come from somewhere..

        epochs = self._sweep_information.keys()
        epochs.sort()

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   'xia2_rd_analyse.mtz'))

        # fixme need to check if anomalous
        
        sc.set_anomalous()
        sc.set_tails()

        # check for errors like data not sorted etc.
        
        sc.scale()

        loggraph = sc.parse_ccp4_loggraph()

        bfactor_info = { }

        for key in loggraph.keys():

            damaged = False
            damage_batch = 0
            
            if 'Scales v rotation range' in key:
                dataset = key.split(',')[-1].strip()
                bfactor_info[dataset] = transpose_loggraph(
                    loggraph[key])

                for j in range(len(bfactor_info[dataset]['1_N'])):
                    batch = int(bfactor_info[dataset]['4_Batch'][j])
                    bfactor = float(bfactor_info[dataset]['5_Bfactor'][j])

                    if bfactor < -10.0:
                        damaged = True
                        damage_batch = batch
                        break

                if damaged:
                    Chatter.write(
                        '%s appears to be radiation damaged (batch %d)' % \
                        (dataset, damage_batch))
                else:
                    Chatter.write(
                        '%s appears to be ok' % dataset)


if __name__ == '__main__':

    # example 1 - 1VRM - last set is radiation damaged
    # see this by the high rmerge vs. batch and also
    # large bfactors...

    irdd = CCP4IntraRadiationDamageDetector()

    irdd.set_hklin(os.path.join(os.environ['X2TD_ROOT'],
                                'Test', 'UnitTest', 'Modules',
                                'IntraRadiationDamage',
                                'TS00_13185_sorted.mtz'))

    sweep_information = {1: {'batches': (1, 360),
                             'dname': 'INFL',
                             'hklin': 'C:\\Ccp4Temp\\friday\\13185\\scale\\TS00_13185_INFL_0.mtz',
                             'pname': 'TS00',
                             'xname': '13185'},
                         2: {'batches': (1001, 1360),
                             'dname': 'LREM',
                             'hklin': 'C:\\Ccp4Temp\\friday\\13185\\scale\\TS00_13185_LREM_1.mtz',
                             'pname': 'TS00',
                             'xname': '13185'},
                         3: {'batches': (2001, 2400),
                             'dname': 'PEAK',
                             'hklin': 'C:\\Ccp4Temp\\friday\\13185\\scale\\TS00_13185_PEAK_2.mtz',
                             'pname': 'TS00',
                             'xname': '13185'}}
    
    irdd.set_sweep_information(sweep_information)

    irdd.analyse()

    
