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
        rmerge_info = { }

        bfactors = { }
        rmerges = { } 

        for key in loggraph.keys():

            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                rmerge_info[dataset] = transpose_loggraph(
                    loggraph[key])

                for j in range(len(rmerge_info[dataset]['1_N_batch'])):
                    batch = int(rmerge_info[dataset]['2_Batch_number'][j])
                    rmerge = float(rmerge_info[dataset]['9_Rmerge'][j])

                    rmerges[batch] = rmerge

            damaged = False
            damage_batch = 0
            
            if 'Scales v rotation range' in key:
                dataset = key.split(',')[-1].strip()
                bfactor_info[dataset] = transpose_loggraph(
                    loggraph[key])

                for j in range(len(bfactor_info[dataset]['1_N'])):
                    batch = int(bfactor_info[dataset]['4_Batch'][j])
                    bfactor = float(bfactor_info[dataset]['5_Bfactor'][j])

                    bfactors[batch] = bfactor

        batches = rmerges.keys()
        batches.sort()

        for b in batches:

            Chatter.write('%d %f %f' % (b, rmerges[b], bfactors[b]))





if __name__ == '__main__':

    # example 1 - 1VRM - last set is radiation damaged
    # see this by the high rmerge vs. batch and also
    # large bfactors...

    use_TS00 = False
    use_TS03 = True
    

    if use_TS00:
        
        irdd = CCP4IntraRadiationDamageDetector()
        
        irdd.set_hklin(os.path.join(os.environ['X2TD_ROOT'],
                                    'Test', 'UnitTest', 'Modules',
                                    'IntraRadiationDamage',
                                    'TS00_13185_sorted.mtz'))
        
        sweep_information = {
            1: {'batches': (1, 360),
                'dname': 'INFL',
                'pname': 'TS00',
                'xname': '13185'},
            2: {'batches': (1001, 1360),
                'dname': 'LREM',
                'pname': 'TS00',
                'xname': '13185'},
            3: {'batches': (2001, 2400),
                'dname': 'PEAK',
                'pname': 'TS00',
                'xname': '13185'}}
        
        irdd.set_sweep_information(sweep_information)
        
        irdd.analyse()

    if use_TS03:

        sweep_information = {
            1: {'batches': (1, 90),
                'dname': 'INFL',
                'pname': 'TS03',
                'xname': '12287'},
            2: {'batches': (101, 190),
                'dname': 'LREM',
                'pname': 'TS03',
                'xname': '12287'},
            3: {'batches': (201, 290),
                'dname': 'PEAK',
                'pname': 'TS03',
                'xname': '12287'}}

        sweep_information_extra = {
            1096205418: {'batches': (201, 290),
                         'dname': 'PEAK',
                         'hklin': '/Users/graeme/TEST/epoch/12287/scale/TS03_12287_PEAK_2.mtz',
                         'integrater': <Wrappers.CCP4.Mosflm.MosflmWrapper instance at 0x2282878>,
                         'header': {'exposure_time': 5.0,
                                    'distance': 170.0,
                                    'phi_start': 290.0,
                                    'phi_width': 1.0,
                                    'beam': [105.099998,
                                             101.050003],
                                    'epoch': 1096205418.0,
                                    'phi_end': 291.0,
                                    'detector_class': 'adsc q210 2x2 binned',
                                    'date': 'Sun Sep 26 14:30:18 2004',
                                    'wavelength': 0.97950000000000004,
                                    'detector': 'adsc',
                                    'pixel': (0.1024,
                                              0.1024),
                                    'size': [2048.0,
                                             2048.0]},
                         'pname': 'TS03',
                         'xname': '12287',
                         'image_to_epoch': {1: 1096205418.0,
                                            2: 1096205428.0,
                                            3: 1096205428.0,
                                            4: 1096205428.0,
                                            5: 1096205428.0,
                                            6: 1096205428.0,
                                            7: 1096205428.0,
                                            8: 1096205428.0,
                                            9: 1096205428.0,
                                            10: 1096205428.0,
                                            11: 1096205428.0,
                                            12: 1096205428.0,
                                            13: 1096205428.0,
                                            14: 1096205428.0,
                                            15: 1096205428.0,
                                            16: 1096205428.0,
                                            17: 1096205428.0,
                                            18: 1096205428.0,
                                            19: 1096205428.0,
                                            20: 1096205428.0,
                                            21: 1096205428.0,
                                            22: 1096205428.0,
                                            23: 1096205428.0,
                                            24: 1096205428.0,
                                            25: 1096205428.0,
                                            26: 1096205428.0,
                                            27: 1096205428.0,
                                            28: 1096205428.0,
                                            29: 1096205428.0,
                                            30: 1096205428.0,
                                            31: 1096205428.0,
                                            32: 1096205428.0,
                                            33: 1096205428.0,
                                            34: 1096205428.0,
                                            35: 1096205428.0,
                                            36: 1096205428.0,
                                            37: 1096205428.0,
                                            38: 1096205428.0,
                                            39: 1096205428.0,
                                            40: 1096205428.0,
                                            41: 1096205428.0,
                                            42: 1096205428.0,
                                            43: 1096205428.0,
                                            44: 1096205428.0,
                                            45: 1096205428.0,
                                            46: 1096205428.0,
                                            47: 1096205428.0,
                                            48: 1096205428.0,
                                            49: 1096205428.0,
                                            50: 1096205428.0,
                                            51: 1096205428.0,
                                            52: 1096205428.0,
                                            53: 1096205428.0,
                                            54: 1096205428.0,
                                            55: 1096205428.0,
                                            56: 1096205428.0,
                                            57: 1096205428.0,
                                            58: 1096205428.0,
                                            59: 1096205428.0,
                                            60: 1096205428.0,
                                            61: 1096205428.0,
                                            62: 1096205428.0,
                                            63: 1096205428.0,
                                            64: 1096205428.0,
                                            65: 1096205428.0,
                                            66: 1096205428.0,
                                            67: 1096205428.0,
                                            68: 1096205428.0,
                                            69: 1096205428.0,
                                            70: 1096205428.0,
                                            71: 1096205428.0,
                                            72: 1096205428.0,
                                            73: 1096205428.0,
                                            74: 1096205428.0,
                                            75: 1096205428.0,
                                            76: 1096205428.0,
                                            77: 1096205428.0,
                                            78: 1096205428.0,
                                            79: 1096205428.0,
                                            80: 1096205428.0,
                                            81: 1096205428.0,
                                            82: 1096205428.0,
                                            83: 1096205428.0,
                                            84: 1096205428.0,
                                            85: 1096205428.0,
                                            86: 1096205428.0,
                                            87: 1096205428.0,
                                            88: 1096205428.0,
                                            89: 1096205428.0,
                                            90: 1096205428.0}},
            1096203695: {'batches': (1, 90),
                         'dname': 'INFL',
                         'hklin': '/Users/graeme/TEST/epoch/12287/scale/TS03_12287_INFL_0.mtz',
                         'integrater': <Wrappers.CCP4.Mosflm.MosflmWrapper instance at 0x7945a8>,
                         'header': {'exposure_time': 5.0,
                                    'distance': 170.0,
                                    'phi_start': 290.0,
                                    'phi_width': 1.0,
                                    'beam': [105.099998,
                                             101.050003],
                                    'epoch': 1096203695.0,
                                    'phi_end': 291.0,
                                    'detector_class': 'adsc q210 2x2 binned',
                                    'date': 'Sun Sep 26 14:01:35 2004',
                                    'wavelength': 0.97965999999999998,
                                    'detector': 'adsc',
                                    'pixel': (0.1024,
                                              0.1024),
                                    'size': [2048.0,
                                             2048.0]},
                         'pname': 'TS03',
                         'xname': '12287',
                         'image_to_epoch': {1: 1096203695.0,
                                            2: 1096203704.0,
                                            3: 1096203704.0,
                                            4: 1096203704.0,
                                            5: 1096203704.0,
                                            6: 1096203704.0,
                                            7: 1096203704.0,
                                            8: 1096203704.0,
                                            9: 1096203704.0,
                                            10: 1096203704.0,
                                            11: 1096203704.0,
                                            12: 1096203704.0,
                                            13: 1096203704.0,
                                            14: 1096203704.0,
                                            15: 1096203704.0,
                                            16: 1096203704.0,
                                            17: 1096203704.0,
                                            18: 1096203704.0,
                                            19: 1096203704.0,
                                            20: 1096203704.0,
                                            21: 1096203704.0,
                                            22: 1096203704.0,
                                            23: 1096203704.0,
                                            24: 1096203704.0,
                                            25: 1096203704.0,
                                            26: 1096203704.0,
                                            27: 1096203704.0,
                                            28: 1096203704.0,
                                            29: 1096203704.0,
                                            30: 1096203704.0,
                                            31: 1096203704.0,
                                            32: 1096203704.0,
                                            33: 1096203704.0,
                                            34: 1096203704.0,
                                            35: 1096203704.0,
                                            36: 1096203704.0,
                                            37: 1096203704.0,
                                            38: 1096203704.0,
                                            39: 1096203704.0,
                                            40: 1096203704.0,
                                            41: 1096203704.0,
                                            42: 1096203704.0,
                                            43: 1096203704.0,
                                            44: 1096203704.0,
                                            45: 1096203704.0,
                                            46: 1096203704.0,
                                            47: 1096203704.0,
                                            48: 1096203704.0,
 49: 1096203704.0,
 50: 1096203704.0,
 51: 1096203704.0,
 52: 1096203704.0,
 53: 1096203704.0,
 54: 1096203704.0,
 55: 1096203704.0,
 56: 1096203704.0,
 57: 1096203704.0,
 58: 1096203704.0,
 59: 1096203704.0,
 60: 1096203704.0,
 61: 1096203704.0,
 62: 1096203704.0,
 63: 1096203704.0,
 64: 1096203704.0,
 65: 1096203704.0,
 66: 1096203704.0,
 67: 1096203704.0,
 68: 1096203704.0,
 69: 1096203704.0,
 70: 1096203704.0,
 71: 1096203704.0,
 72: 1096203704.0,
 73: 1096203704.0,
 74: 1096203704.0,
 75: 1096203704.0,
 76: 1096203704.0,
 77: 1096203704.0,
 78: 1096203704.0,
 79: 1096203704.0,
 80: 1096203704.0,
 81: 1096203704.0,
 82: 1096203704.0,
 83: 1096203704.0,
 84: 1096203704.0,
 85: 1096203704.0,
 86: 1096203704.0,
 87: 1096203704.0,
 88: 1096203704.0,
 89: 1096203704.0,
 90: 1096203704.0}},
 1096203943: {'batches': (101,
 190),
 'dname': 'LREM',
 'hklin': '/Users/graeme/TEST/epoch/12287/scale/TS03_12287_LREM_1.mtz',
 'integrater': <Wrappers.CCP4.Mosflm.MosflmWrapper instance at 0x1747800>,
 'header': {'exposure_time': 5.0,
 'distance': 170.0,
 'phi_start': 290.0,
 'phi_width': 1.0,
 'beam': [105.099998,
 101.050003],
 'epoch': 1096203943.0,
 'phi_end': 291.0,
 'detector_class': 'adsc q210 2x2 binned',
 'date': 'Sun Sep 26 14:05:43 2004',
 'wavelength': 1.0,
 'detector': 'adsc',
 'pixel': (0.1024,
 0.1024),
 'size': [2048.0,
 2048.0]},
 'pname': 'TS03',
 'xname': '12287',
 'image_to_epoch': {1: 1096203943.0,
 2: 1096203951.0,
 3: 1096203951.0,
 4: 1096203951.0,
 5: 1096203951.0,
 6: 1096203951.0,
 7: 1096203951.0,
 8: 1096203951.0,
 9: 1096203951.0,
 10: 1096203951.0,
 11: 1096203951.0,
 12: 1096203951.0,
 13: 1096203951.0,
 14: 1096203951.0,
 15: 1096203951.0,
 16: 1096203951.0,
 17: 1096203951.0,
 18: 1096203951.0,
 19: 1096203951.0,
 20: 1096203951.0,
 21: 1096203951.0,
 22: 1096203951.0,
 23: 1096203951.0,
 24: 1096203951.0,
 25: 1096203951.0,
 26: 1096203951.0,
 27: 1096203951.0,
 28: 1096203951.0,
 29: 1096203951.0,
 30: 1096203951.0,
 31: 1096203951.0,
 32: 1096203951.0,
 33: 1096203951.0,
 34: 1096203951.0,
 35: 1096203951.0,
 36: 1096203951.0,
 37: 1096203951.0,
 38: 1096203951.0,
 39: 1096203951.0,
 40: 1096203951.0,
 41: 1096203951.0,
 42: 1096203951.0,
 43: 1096203951.0,
 44: 1096203951.0,
 45: 1096203951.0,
 46: 1096203951.0,
 47: 1096203951.0,
 48: 1096203951.0,
 49: 1096203951.0,
 50: 1096203951.0,
 51: 1096203951.0,
 52: 1096203951.0,
 53: 1096203951.0,
 54: 1096203951.0,
 55: 1096203951.0,
 56: 1096203951.0,
 57: 1096203951.0,
 58: 1096203951.0,
 59: 1096203951.0,
 60: 1096203951.0,
 61: 1096203951.0,
 62: 1096203951.0,
 63: 1096203951.0,
 64: 1096203951.0,
 65: 1096203951.0,
 66: 1096203951.0,
 67: 1096203951.0,
 68: 1096203951.0,
 69: 1096203951.0,
 70: 1096203951.0,
 71: 1096203951.0,
 72: 1096203951.0,
 73: 1096203951.0,
 74: 1096203951.0,
 75: 1096203951.0,
 76: 1096203951.0,
 77: 1096203951.0,
 78: 1096203951.0,
 79: 1096203951.0,
 80: 1096203951.0,
 81: 1096203951.0,
 82: 1096203951.0,
 83: 1096203951.0,
 84: 1096203951.0,
 85: 1096203951.0,
 86: 1096203951.0,
 87: 1096203951.0,
 88: 1096203951.0,
 89: 1096203951.0,
 90: 1096203951.0}}}
        
        irdd = CCP4IntraRadiationDamageDetector()
        
        irdd.set_hklin(os.path.join(os.environ['X2TD_ROOT'],
                                    'Test', 'UnitTest', 'Modules',
                                    'InterRadiationDamage',
                                    'TS03_12287_sorted.mtz'))
        
        irdd.set_sweep_information(sweep_information)
        
        irdd.analyse()

