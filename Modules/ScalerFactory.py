#!/usr/bin/env python
# ScalerFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 21/SEP/06 TEST RUN
# 
# Note that this is not production code...

from CCP4ScalerImplementation import CCP4Scaler
# from XDSScaler import XDSScaler

def Scaler():
    '''Create a Scaler implementation.'''

    # FIXME 078/JAN/07 this needs to be able to work out what the integraters
    # were before it can decide what the most appropriate scaler is...

    return CCP4Scaler()

