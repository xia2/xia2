#!/usr/bin/env python
# XScaleHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Helpers for the wrapper for XSCALE, the XDS Scaling program.
#

import math

def _generate_resolution_shells(low, high):
    '''Generate 9 evenly spaced in reciprocal space resolution
    shells from low to high resolution, e.g. in 1/d^2.'''
    
    dmin = (1.0 / high) * (1.0 / high)
    dmax = (1.0 / low) * (1.0 / low)
    diff = (dmin -  dmax) / 8.0
    
    shells = [1.0 / math.sqrt(dmax)]
    
    for j in range(8):
        shells.append(1.0 / math.sqrt(dmax + diff * (j + 1)))
        
    return shells

def generate_resolution_shells_str(low, high):
    '''Generate a string of 8 evenly spaced in reciprocal space resolution
    shells from low to high resolution, e.g. in 1/d^2.'''

    result = ''
    shells = _generate_resolution_shells(low, high)

    for s in shells:
        result += ' %.2f' % s

    return result

if __name__ == '__main__':
    print generate_resolution_shells_str(40, 1.8)
