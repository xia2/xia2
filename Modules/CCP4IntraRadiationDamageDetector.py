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

############## CALCULATIONS #################

def meansd(values):
    '''Compute the mean and standard deviation of a list of values.'''
    mean = sum(values) / len(values)
    sd = math.sqrt(sum([(v - mean) * (v - mean) for v in values])/len(values))
    return mean, sd

# FIXME these need to be tidied up to take a generalised
# list of values
        
def bin(values, width):
    '''Bin values in bins of given width, computing the error
    (standard deviation) in the bin on the Y values. This is
    messy...'''
    if len(values) % width:
        raise RuntimeError, 'num values not multiple of width (%d %d)' % \
              (len(values), width)

    result = []
    for j in range(len(values) / width):
        block = values[j * width:(j + 1) * width]
        result.append((meansd([b[0] for b in block])[0],
                       meansd([b[1] for b in block])))
            
    return result

def chisq(data, model):
    '''Compute a chi^2 value for data vs. model. Data should be
    a list of points with errors, model should be a list of
    values with no errors.'''

    result = sum([((data[j][1][0] - model[j]) / data[j][1][1] *
                   (data[j][1][0] - model[j]) / data[j][1][1])
                  for j in range(len(data))])

    return result

def fit(data):
    '''Return an ML linear fit to data. This will fit
    y = a + bx and return a, b. Input is a list of
    (x, (y, sy)) where sy is the error on the y value.'''

    # two interesting cases.... have to provide default
    # results from these

    if len(data) == 0:
        return 0.0, 0.0

    if len(data) == 1:
        return data[0][1][0], 0.0

    # the rest... these can give meaningful values
    # equations from P104 of
    # "Data reduction and error analysis in the physical sciences"
    # 0-07-911243-9.

    # fixme need to tidy this up to use cleaner sum calculations
    # than the full and painful below.
    
    delta = sum([1.0 / (d[1][1] * d[1][1]) for d in data]) * \
            sum([(d[0] * d[0]) / (d[1][1] * d[1][1]) for d in data]) - \
            (sum([d[0] / (d[1][1] * d[1][1]) for d in data]) *
             sum([d[0] / (d[1][1] * d[1][1]) for d in data]))
    a = sum([(d[0] * d[0]) / (d[1][1] * d[1][1]) for d in data]) * \
        sum([d[1][0] / (d[1][1] * d[1][1]) for d in data]) - \
        sum([d[0] / (d[1][1] * d[1][1]) for d in data]) * \
        sum([(d[0] * d[1][0]) / (d[1][1] * d[1][1]) for d in data])
    b = sum([1.0 / (d[1][1] * d[1][1]) for d in data]) * \
        sum([(d[0] * d[1][0]) / (d[1][1] * d[1][1]) for d in data]) - \
        (sum([d[0] / (d[1][1] * d[1][1]) for d in data]) * \
         sum([d[1][0] / (d[1][1] * d[1][1]) for d in data]))

    return a / delta, b / delta

def decide_rd_limit(data):
    '''Decide the radiation damage limit for a list of measurements
    as tuples (epoch, r, b).'''

    # convert to the form we want to deal with...
    updata = [(d[0], -1 * d[1] * d[2]) for d in data]

    binned = bin(updata, 10)

    bin_tops = []
    for j in range(len(data)):
        if (j + 1) % 10:
            bin_tops.append(data[j][0])
    
    for j in range(1, len(binned)):
        basis = binned[:j]
        _a, _b = fit(basis)
        model = [_a + _b * b[0] for b in basis]
        chi = chisq(basis, model) / j

        if chi > 2.0:
            return bin_tops[j]

    # by default use all data...
    return data[-1][0] + 1

def run():
    '''Call all of the above to perform a chi-squared analysis.
    Assumption is that the data change linearly, and that any
    non-linear behaviour is an indication of significant radiation
    damage.'''
    
    data = [map(float, line.split()) for line in open(
        'reordered.txt', 'r').readlines()]
    
    updata = [(d[0] - data[0][0], -1 * d[1] * d[2]) for d in data]
    
    binned = bin(updata, 10)
    
    for j in range(1, len(binned)):
        basis = binned[:j]
        _a, _b = fit(basis)
        model = [_a + _b * b[0] for b in basis]
        chi = chisq(basis, model) / j

        b = binned[j]
        
        print '%d %.1f %.4f %.4f %.4f' % (10 * j, b[0], b[1][0], b[1][1], chi)


##################### END OF CALCULATIONS ###################


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

        batch_to_epoch = { }

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

            
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            if input.has_key('image_to_epoch'):
                for j in range(start, end + 1):
                    batch_to_epoch[j] = input['image_to_epoch'][
                        j - input['batch_offset']]

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

        if batch_to_epoch:
            analysis_data = []
            analysis_dict = { }
            for b in batches:
                analysis_dict[batch_to_epoch[b]] = (rmerges[b], bfactors[b])
            epochs = analysis_dict.keys()
            epochs.sort()
            for e in epochs:
                analysis_data.append(
                    (e, analysis_dict[e][0], analysis_dict[e][1]))
            rd_epoch = decide_rd_limit(analysis_data)
            Chatter.write('Radiation damage found at epoch %f' % rd_epoch)
        else:
            for b in batches:
                Chatter.write('%d 0 %f %f' % \
                              (b, rmerges[b], bfactors[b]))




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
            1096205418: {'batch_offset': 200,
                         'batches': (201,
                                     290),
                         'dname': 'PEAK',
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
                                            3: 1096205436.0,
                                            4: 1096205444.0,
                                            5: 1096205452.0,
                                            6: 1096205461.0,
                                            7: 1096205469.0,
                                            8: 1096205477.0,
                                            9: 1096205485.0,
                                            10: 1096205493.0,
                                            11: 1096205501.0,
                                            12: 1096205509.0,
                                            13: 1096205518.0,
                                            14: 1096205526.0,
                                            15: 1096205534.0,
                                            16: 1096205542.0,
                                            17: 1096205550.0,
                                            18: 1096205558.0,
                                            19: 1096205567.0,
                                            20: 1096205574.0,
                                            21: 1096205583.0,
                                            22: 1096205591.0,
                                            23: 1096205599.0,
                                            24: 1096205607.0,
                                            25: 1096205615.0,
                                            26: 1096205624.0,
                                            27: 1096205632.0,
                                            28: 1096205639.0,
                                            29: 1096205648.0,
                                            30: 1096205656.0,
                                            31: 1096205664.0,
                                            32: 1096205672.0,
                                            33: 1096205681.0,
                                            34: 1096205689.0,
                                            35: 1096205697.0,
                                            36: 1096205706.0,
                                            37: 1096205714.0,
                                            38: 1096205722.0,
                                            39: 1096205730.0,
                                            40: 1096205738.0,
                                            41: 1096205746.0,
                                            42: 1096205755.0,
                                            43: 1096205763.0,
                                            44: 1096205771.0,
                                            45: 1096205779.0,
                                            46: 1096205787.0,
                                            47: 1096205796.0,
                                            48: 1096205804.0,
                                            49: 1096205812.0,
                                            50: 1096205820.0,
                                            51: 1096205828.0,
                                            52: 1096205836.0,
                                            53: 1096205844.0,
                                            54: 1096205853.0,
                                            55: 1096205861.0,
                                            56: 1096205869.0,
                                            57: 1096205877.0,
                                            58: 1096205885.0,
                                            59: 1096205894.0,
                                            60: 1096205902.0,
                                            61: 1096205910.0,
                                            62: 1096205919.0,
                                            63: 1096205927.0,
                                            64: 1096205935.0,
                                            65: 1096205944.0,
                                            66: 1096205952.0,
                                            67: 1096205960.0,
                                            68: 1096205968.0,
                                            69: 1096205976.0,
                                            70: 1096205985.0,
                                            71: 1096205993.0,
                                            72: 1096206001.0,
                                            73: 1096206009.0,
                                            74: 1096206018.0,
                                            75: 1096206026.0,
                                            76: 1096206034.0,
                                            77: 1096206043.0,
                                            78: 1096206051.0,
                                            79: 1096206059.0,
                                            80: 1096206067.0,
                                            81: 1096206075.0,
                                            82: 1096206084.0,
                                            83: 1096206092.0,
                                            84: 1096206100.0,
                                            85: 1096206107.0,
                                            86: 1096206116.0,
                                            87: 1096206124.0,
                                            88: 1096206132.0,
                                            89: 1096206140.0,
                                            90: 1096206149.0}},
            1096203695: {'batch_offset': 0,
                         'batches': (1,
                                     90),
                         'dname': 'INFL',
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
                                            3: 1096203713.0,
                                            4: 1096203721.0,
                                            5: 1096203729.0,
                                            6: 1096203737.0,
                                            7: 1096203746.0,
                                            8: 1096203754.0,
                                            9: 1096203761.0,
                                            10: 1096203770.0,
                                            11: 1096203778.0,
                                            12: 1096203786.0,
                                            13: 1096203794.0,
                                            14: 1096203803.0,
                                            15: 1096203811.0,
                                            16: 1096203819.0,
                                            17: 1096203827.0,
                                            18: 1096203835.0,
                                            19: 1096203843.0,
                                            20: 1096203851.0,
                                            21: 1096203859.0,
                                            22: 1096203868.0,
                                            23: 1096203876.0,
                                            24: 1096203884.0,
                                            25: 1096203893.0,
                                            26: 1096203901.0,
                                            27: 1096203909.0,
                                            28: 1096203917.0,
                                            29: 1096203925.0,
                                            30: 1096203933.0,
                                            31: 1096204190.0,
                                            32: 1096204199.0,
                                            33: 1096204207.0,
                                            34: 1096204215.0,
                                            35: 1096204223.0,
                                            36: 1096204231.0,
                                            37: 1096204239.0,
                                            38: 1096204248.0,
                                            39: 1096204256.0,
                                            40: 1096204265.0,
                                            41: 1096204273.0,
                                            42: 1096204281.0,
                                            43: 1096204289.0,
                                            44: 1096204297.0,
                                            45: 1096204306.0,
                                            46: 1096204314.0,
                                            47: 1096204322.0,
                                            48: 1096204330.0,
                                            49: 1096204338.0,
                                            50: 1096204347.0,
                                            51: 1096204355.0,
                                            52: 1096204363.0,
                                            53: 1096204371.0,
                                            54: 1096204379.0,
                                            55: 1096204387.0,
                                            56: 1096204396.0,
                                            57: 1096204404.0,
                                            58: 1096204412.0,
                                            59: 1096204420.0,
                                            60: 1096204429.0,
                                            61: 1096204685.0,
                                            62: 1096204694.0,
                                            63: 1096204702.0,
                                            64: 1096204710.0,
                                            65: 1096204718.0,
                                            66: 1096204727.0,
                                            67: 1096204735.0,
                                            68: 1096204743.0,
                                            69: 1096204751.0,
                                            70: 1096204759.0,
                                            71: 1096204767.0,
                                            72: 1096204776.0,
                                            73: 1096204784.0,
                                            74: 1096204792.0,
                                            75: 1096204800.0,
                                            76: 1096204808.0,
                                            77: 1096204816.0,
                                            78: 1096204825.0,
                                            79: 1096204833.0,
                                            80: 1096204841.0,
                                            81: 1096204849.0,
                                            82: 1096204857.0,
                                            83: 1096204866.0,
                                            84: 1096204874.0,
                                            85: 1096204882.0,
                                            86: 1096204890.0,
                                            87: 1096204898.0,
                                            88: 1096204906.0,
                                            89: 1096204914.0,
                                            90: 1096204923.0}},
            1096203943: {'batch_offset': 100,
                         'batches': (101,
                                     190),
                         'dname': 'LREM',
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
                                            3: 1096203959.0,
                                            4: 1096203968.0,
                                            5: 1096203976.0,
                                            6: 1096203984.0,
                                            7: 1096203992.0,
                                            8: 1096204000.0,
                                            9: 1096204008.0,
                                            10: 1096204017.0,
                                            11: 1096204024.0,
                                            12: 1096204033.0,
                                            13: 1096204041.0,
                                            14: 1096204049.0,
                                            15: 1096204057.0,
                                            16: 1096204066.0,
                                            17: 1096204074.0,
                                            18: 1096204082.0,
                                            19: 1096204091.0,
                                            20: 1096204099.0,
                                            21: 1096204107.0,
                                            22: 1096204115.0,
                                            23: 1096204123.0,
                                            24: 1096204132.0,
                                            25: 1096204140.0,
                                            26: 1096204147.0,
                                            27: 1096204156.0,
                                            28: 1096204164.0,
                                            29: 1096204172.0,
                                            30: 1096204181.0,
                                            31: 1096204438.0,
                                            32: 1096204447.0,
                                            33: 1096204455.0,
                                            34: 1096204463.0,
                                            35: 1096204471.0,
                                            36: 1096204479.0,
                                            37: 1096204488.0,
                                            38: 1096204496.0,
                                            39: 1096204504.0,
                                            40: 1096204512.0,
                                            41: 1096204520.0,
                                            42: 1096204528.0,
                                            43: 1096204536.0,
                                            44: 1096204544.0,
                                            45: 1096204553.0,
                                            46: 1096204561.0,
                                            47: 1096204569.0,
                                            48: 1096204578.0,
                                            49: 1096204586.0,
                                            50: 1096204594.0,
                                            51: 1096204602.0,
                                            52: 1096204610.0,
                                            53: 1096204619.0,
                                            54: 1096204627.0,
                                            55: 1096204635.0,
                                            56: 1096204643.0,
                                            57: 1096204651.0,
                                            58: 1096204660.0,
                                            59: 1096204668.0,
                                            60: 1096204676.0,
                                            61: 1096204932.0,
                                            62: 1096204941.0,
                                            63: 1096204949.0,
                                            64: 1096204957.0,
                                            65: 1096204965.0,
                                            66: 1096204974.0,
                                            67: 1096204982.0,
                                            68: 1096204990.0,
                                            69: 1096204998.0,
                                            70: 1096205006.0,
                                            71: 1096205014.0,
                                            72: 1096205023.0,
                                            73: 1096205031.0,
                                            74: 1096205039.0,
                                            75: 1096205047.0,
                                            76: 1096205056.0,
                                            77: 1096205064.0,
                                            78: 1096205072.0,
                                            79: 1096205080.0,
                                            80: 1096205089.0,
                                            81: 1096205097.0,
                                            82: 1096205105.0,
                                            83: 1096205113.0,
                                            84: 1096205121.0,
                                            85: 1096205129.0,
                                            86: 1096205137.0,
                                            87: 1096205146.0,
                                            88: 1096205154.0,
                                            89: 1096205162.0,
                                            90: 1096205170.0}}}        
        
        irdd = CCP4IntraRadiationDamageDetector()
        
        irdd.set_hklin(os.path.join(os.environ['X2TD_ROOT'],
                                    'Test', 'UnitTest', 'Modules',
                                    'InterRadiationDamage',
                                    'TS03_12287_sorted.mtz'))
        
        irdd.set_sweep_information(sweep_information_extra)
        
        irdd.analyse()

