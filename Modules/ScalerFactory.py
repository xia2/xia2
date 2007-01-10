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


from CCP4ScalerImplementation import CCP4Scaler
# from XDSScaler import XDSScaler
from Handlers.PipelineSelection import get_preferences, add_preference

def Scaler():
    '''Create a Scaler implementation.'''

    # FIXED 08/JAN/07 this needs to be able to work out what the integraters
    # were before it can decide what the most appropriate scaler is...
    # this is now stored in a glbal preferences system.

    return CCP4Scaler()

