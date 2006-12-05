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

def Scaler():
    '''Create a Scaler implementation.'''

    return CCP4Scaler()

