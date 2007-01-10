#!/usr/bin/env python
# DRStrategyExpert.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 10th January 2007
# 
# An expert system to propose a strategy for data reduction, based on
# the existing computational environment and some characteristics of the
# data set.
#
# Those characteristics are:
#
# ismosaic
#
# and the computational environment is:
#
# is the software available
#

import os
import sys

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverHelper import executable_exists

# write in strategy dictionary here

strategy_dict = {
    'default':{
    'score':1,
    'pipeline':{
    'indexer':'labelit', 'integrater':'xds', 'scaler':'xds-hybrid'}
    'depends-on':['labelit.screen', 'xds', 'xscale', 'scala', 'combat',
                  'pointless-1.1.0.4']},
    'default':{
    'score':2,
    'pipeline':{
    'indexer':'labelit', 'integrater':'mosflm', 'scaler':'mosflm'}
    'depends-on':['labelit.screen', 'mosflm', 'scala', 'reindex',
                  'pointless-1.1.0.4']},
    'mosaic':{
    'score':1,
    'pipeline':{
    'indexer':'labelit', 'integrater':'xds', 'scaler':'xds-hybrid'}
    'depends-on':['labelit.screen', 'xds', 'xscale', 'scala', 'combat',
                  'pointless-1.1.0.4']},
    'mosaic':{
    'score':2,
    'pipeline':{
    'indexer':'xds', 'integrater':'xds', 'scaler':'xds'}
    'depends-on':['xds', 'xscale']}
    }
