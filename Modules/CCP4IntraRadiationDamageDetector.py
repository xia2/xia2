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
# Second of these is more interesting for MAD data... however both provide 
# interesting information. The current implementation therefore looks
# at the product of these as a function of exposure epoch, and looks for 
# the point at which the behaviour becomes significantly non-linear.
# 
# The definition of "significantly non linear" is a little complex, and
# goes a little like this:
#
# q = R * B * -1
#
# b, db = mean_sd(bin(q)) - sd gives spread in values, minimum 0.05
#
# for i in b:
#   fit (ML) straight line to b(i)
#   compute chi_sq for this straight line - if "reduced chi_sq" > 2
#     then the straight line is not a good model - ergo bin(i) is damaged.
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
# List of "allowed" batches to use for different wavelengths. This should
# in fact return a dictionary of data sets for uses in different contexts,
# for example "all data", "best data", "refinement data".
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
from Handlers.Files import FileHandler

from lib.bits import auto_logfiler, transpose_loggraph
from lib.MathLib import linear_fit_ml

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

    # do not really want to warn about this...
    if len(values) % width and False:
        raise RuntimeError, 'num values not multiple of width (%d %d)' % \
              (len(values), width)

    result = []
    for j in range(len(values) / width):
        block = values[j * width:(j + 1) * width]
        mean, sd = meansd([b[1] for b in block])
        if sd < 0.05:
            sd = 0.05
        result.append((meansd([b[0] for b in block])[0],
                       (mean, sd)))
        
    return result

def chisq(data, model):
    '''Compute a chi^2 value for data vs. model. Data should be
    a list of points with errors, model should be a list of
    values with no errors.'''

    result = sum([((data[j][1][0] - model[j]) / data[j][1][1] *
                   (data[j][1][0] - model[j]) / data[j][1][1])
                  for j in range(len(data))])

    return result


# FIXME clean up the input to this to be there lists or arrays -
# x, y, sigy values. This will make it much clearer what is going
# on. Also call it ml_linear_fit and move it to a stats library
# of come kind...

def fit(data):
    '''Call linear_fit_ml to do this.'''

    X = [d[0] for d in data]
    Y = [d[1][0] for d in data]
    S = [d[1][1] for d in data]

    return linear_fit_ml(X, Y, S)

def _fit(data):
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

    # the following quantities are used in reality:
    # sum_inv_sig_sq, sum_x_sq_over_sig_sq, sum_x_over_sig_sq,
    # sum_y_over_sig_sq, sum_xy_over_sig_sq
    
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
        FileHandler.record_temporary_file(sc.get_hklout())

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
            rd_epoch = self.decide_rd_limit(analysis_data)
            Chatter.write('Radiation damage found at epoch %f' % rd_epoch)

            rd_log = open(os.path.join(self.get_working_directory(),
                                       'rd_info.log'), 'w')
                                       

            for b in batches:
                if batch_to_epoch[b] < rd_epoch:
                    rd_log.write('I %d %d %f %f\n' % \
                                 (b, batch_to_epoch[b],
                                  rmerges[b], bfactors[b]))
                else:
                    rd_log.write('X %d %d %f %f\n' % \
                                 (b, batch_to_epoch[b],
                                  rmerges[b], bfactors[b]))

            rd_log.close()

        else:
            # FIXME need to handle this some how...
            
            pass

        
    def decide_rd_limit(self, data):
        '''Decide the radiation damage limit for a list of measurements
        as tuples (epoch, r, b).'''
        
        start_t = data[0][0]
        
        # convert to the form we want to deal with...
        updata = [(d[0] - start_t, -1 * d[1] * d[2]) for d in data]
        
        binned = bin(updata, 10)

        for b in binned:
            # have a minimum "error" of 0.1 A^2 Rmerges .
            if b[1][1] < 0.1 and False:
                # can't do this is a list!
                b[1][1] = 0.1
        
        epoch = -1

        chi_log = open(os.path.join(self.get_working_directory(),
                                    'rd_chi.log'), 'w')
                                    
        for j in range(1, len(binned)):
            basis = binned[:j]
            _a, _b = fit(basis)
            model = [_a + _b * b[0] for b in basis]
            chi = chisq(basis, model) / j
            
            b = binned[j]
            chi_log.write('%f %f %f %f\n' %
                          (b[0], b[1][0], b[1][1], chi))

            if chi > 2.0 and epoch == -1:
                epoch = data[10 * j][0]

        chi_log.close()
        # by default use all data...

        if epoch == -1:
            epoch = data[-1][0] + 1
            
        return epoch


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

        sweep_information_extra = eval(open(
            os.path.join(os.environ['X2TD_ROOT'],
                         'Test', 'UnitTest', 'Modules',
                         'InterRadiationDamage',
                         'TS03_12287_sweep_info.txt'), 'r').read())
        
        irdd = CCP4IntraRadiationDamageDetector()
        
        irdd.set_hklin(os.path.join(os.environ['X2TD_ROOT'],
                                    'Test', 'UnitTest', 'Modules',
                                    'InterRadiationDamage',
                                    'TS03_12287_sorted.mtz'))
        
        irdd.set_sweep_information(sweep_information_extra)
        
        irdd.analyse()

