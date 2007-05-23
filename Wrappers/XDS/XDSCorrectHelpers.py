#!/usr/bin/env python
# XDSCorrectHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 18th October 2006
# 
# Helpers for XDS when running the correct step - this will - 
# 
#  - check that all input files are present and correct
#  - run xds to do integration, with help from the input parameters
#    and a generic xds writer
#  - parse the output from CORRECT.LP

import os
import sys
import copy

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

# helper methods/functions - these can be used externally for the purposes
# of testing...

def _resolution_estimate(ordered_pair_list, cutoff):
    '''Come up with a linearly interpolated estimate of resolution at
    cutoff cutoff from input data [(resolution, i_sigma)].'''

    x = []
    y = []

    for o in ordered_pair_list:
        x.append(o[0])
        y.append(o[1])

    if max(y) < cutoff:
        # there is no point where this exceeds the resolution
        # cutoff
        return -1.0

    # this means that there is a place where the resolution cutof
    # can be reached - get there by working backwards

    x.reverse()
    y.reverse()

    if y[0] >= cutoff:
        # this exceeds the resolution limit requested
        return x[0]

    j = 0
    while y[j] < cutoff:
        j += 1

    resolution = x[j] + (cutoff - y[j]) * (x[j - 1] - x[j]) / \
                 (y[j - 1] - y[j])

    return resolution

def _parse_correct_lp(filename):
    '''Parse the contents of the CORRECT.LP file pointed to by filename.'''

    if not os.path.split(filename)[-1] == 'CORRECT.LP':
        raise RuntimeError, 'input filename not CORRECT.LP'

    file_contents = open(filename, 'r').readlines()

    postrefinement_stats = { }

    for i in range(len(file_contents)):
        if 'OF SPOT    POSITION (PIXELS)' in file_contents[i]:
            rmsd_pixel = float(file_contents[i].split()[-1])
            postrefinement_stats['rmsd_pixel'] = rmsd_pixel

        if 'OF SPINDLE POSITION (DEGREES)' in file_contents[i]:
            rmsd_phi = float(file_contents[i].split()[-1])
            postrefinement_stats['rmsd_phi'] = rmsd_phi        

        # want to convert this to mm in some standard setting!
        if 'DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM' in file_contents[i]:
            beam = map(float, file_contents[i].split()[-2:])
            postrefinement_stats['beam'] = beam        
            
        if 'CRYSTAL TO DETECTOR DISTANCE (mm)' in file_contents[i]:
            distance = float(file_contents[i].split()[-1])
            postrefinement_stats['distance'] = distance
        
        if 'UNIT CELL PARAMETERS' in file_contents[i]:
            cell = map(float, file_contents[i].split()[-6:])
            postrefinement_stats['cell'] = cell

        if 'E.D.D. OF CELL PARAMETERS' in file_contents[i]:
            cell_esd = map(float, file_contents[i].split()[-6:])
            postrefinement_stats['cell_esd'] = cell_esd

        if 'REFLECTIONS ACCEPTED' in file_contents[i]:
            postrefinement_stats['n_ref'] = int(file_contents[i].split()[0])

        # look for I/sigma (resolution) information...
        if 'RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR  R-FACTOR' in \
           file_contents[i]:
            resolution_info = []
            j = i + 3
            while not '-----' in file_contents[j]:
                l = file_contents[j].split()
                resolution_info.append((float(l[1]),float(l[2])))
                j += 1

            resolution = _resolution_estimate(resolution_info, 1.0)
            postrefinement_stats['resolution_estimate'] = resolution

    return postrefinement_stats

if __name__ == '__main__':
    correct_lp = os.path.join(os.environ['XIA2_ROOT'], 'Wrappers', 'XDS',
                              'Doc', 'CORRECT.LP')
    print _parse_correct_lp(correct_lp)

