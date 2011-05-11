#!/usr/bin/env python
# ScalerFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 21/SEP/06 TEST RUN
# 
# Note that this is not production code... so fix it to be such!

import os
import sys
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

# scaler implementations

from CCP4Scaler import CCP4Scaler
from CCP4ScalerR import CCP4ScalerR
from CCP4ScalerRefactor import CCP4ScalerRefactor
from XDSScaler import XDSScaler
from XDSScalerR import XDSScalerR

# selection stuff

from Handlers.PipelineSelection import get_preferences, add_preference

# other odds and ends

from Exceptions.NotAvailableError import NotAvailableError
from Handlers.Streams import Debug

def Scaler():
    '''Create a Scaler implementation.'''

    # FIXED 08/JAN/07 this needs to be able to work out what the integraters
    # were before it can decide what the most appropriate scaler is...
    # this is now stored in a glbal preferences system.

    scaler = None
    preselection = get_preferences().get('scaler')

    if not scaler and \
       (not preselection or preselection == 'ccp4r'):
        try:
            scaler = CCP4ScalerR()
            Debug.write('Using CCP4R Scaler')
        except NotAvailableError, e:
            if preselection == 'ccp4r':
                raise RuntimeError, 'preselected scaler ccp4r not available'
            pass

    if not scaler and \
       (not preselection or preselection == 'ccp4'):
        try:
            scaler = CCP4Scaler()
            Debug.write('Using CCP4 Scaler')
        except NotAvailableError, e:
            if preselection == 'ccp4':
                raise RuntimeError, 'preselected scaler ccp4 not available'
            pass

    if not scaler and \
       (not preselection or preselection == 'ccp4refactor'):
        try:
            scaler = CCP4ScalerRefactor()
            Debug.write('Using CCP4 - refactor - Scaler')
        except NotAvailableError, e:
            if preselection == 'ccp4refactor':
                raise RuntimeError, \
                      'preselected scaler ccp4refactor not available'
            pass

    if not scaler and \
       (not preselection or preselection == 'xdsr'):
        try:
            scaler = XDSScalerR()
            Debug.write('Using XDSR Scaler')
        except NotAvailableError, e:
            if preselection == 'xdsr':
                raise RuntimeError, 'preselected scaler xdsr not available'
        pass

    if not scaler and \
       (not preselection or preselection == 'xds'):
        try:
            scaler = XDSScaler()
            Debug.write('Using XDS Scaler')
        except NotAvailableError, e:
            if preselection == 'xds':
                raise RuntimeError, 'preselected scaler xds not available'
        pass

    return scaler

