#!/usr/bin/env python
# XDSIntegrate.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 17th October 2006
# 
# A wrapper for XDS when running the integrate step - this will - 
# 
#  - check that all input files are present and correct
#  - run xds to do integration, with help from the input parameters
#    and a generic xds writer
#  - parse the output from INTEGRATE.LP

import os
import sys
import copy

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Driver.DriverFactory import DriverFactory

# helper methods/functions - these can be used externally for the purposes
# of testing...

def _parse_integrate_lp(filename):
    '''Parse the contents of the INTEGRATE.LP file pointed to by filename.'''

    if not os.path.split(filename)[-1] == 'INTEGRATE.LP':
        raise RuntimeError, 'input filename not INTEGRATE.LP'

    file_contents = open(filename, 'r').readlines()

    per_image_stats = { }
    pro_block_stats = []

    for i in range(len(file_contents)):
        if 'IMAGE IER  SCALE' in file_contents[i]:
            j = i + 1
            while len(file_contents[j].strip()):
                list = file_contents[j].split()
                image = int(list[0])
                scale = float(list[2])
                overloads = int(list[4])
                strong = int(list[6])
                rejected = int(list[7])
                per_image_stats[image] = {'scale':scale,
                                          'overloads':overloads,
                                          'strong':strong,
                                          'rejected':rejected}

                j += 1

    return per_image_stats

def _print_integrate_lp(integrate_lp_stats):
    '''Print the contents of the integrate.lp dictionary.'''

    images = integrate_lp_stats.keys()
    images.sort()

    for i in images:
        data = integrate_lp_stats[i]
        print '%4d %5.3f %5d %5d %5d' % (i, data['scale'], data['strong'],
                                        data['overloads'], data['rejected'])

if __name__ == '__main__':
    integrate_lp = os.path.join(os.environ['DPA_ROOT'], 'Wrappers', 'XDS',
                                'Doc', 'INTEGRATE.LP')
    _print_integrate_lp(_parse_integrate_lp(integrate_lp))
