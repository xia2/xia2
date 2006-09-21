#!/usr/bin/env python
# ScalerFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# 21/SEP/06 TEST RUN
# 
# Note that this is not production code...

from CCP4ScalerImplementation import CCP4Scaler

def Scaler():
    '''Create a Scaler implementation.'''

    return CCP4Scaler()

