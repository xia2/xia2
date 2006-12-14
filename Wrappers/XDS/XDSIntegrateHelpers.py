#!/usr/bin/env python
# XDSIntegrateHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# Routines which help with working with XDS INTEGRATE - e.g. parsing the 
# output INTEGRATE.LP.
# 

import math
import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Admin, Science, Status, Chatter

def _parse_integrate_lp(filename):
    '''Parse the contents of the INTEGRATE.LP file pointed to by filename.'''

    if not os.path.split(filename)[-1] == 'INTEGRATE.LP':
        raise RuntimeError, 'input filename not INTEGRATE.LP'

    file_contents = open(filename, 'r').readlines()

    per_image_stats = { }

    block_start_finish = (0, 0)

    oscillation_range = 0.0

    for i in range(len(file_contents)):

        # check for the header contents - this is basically a duplicate
        # of the input data....

        if 'OSCILLATION_RANGE=' in file_contents[i]:
            oscillation_range = float(file_contents[i].split()[1])

        if 'PROCESSING OF IMAGES' in file_contents[i]:
            list = file_contents[i].split()
            block_start_finish = (int(list[3]), int(list[5]))

        # look for explicitly per-image information
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

        # then look for per-block information - this will be mapped onto
        # individual images using the block_start_finish information

        if 'CRYSTAL MOSAICITY (DEGREES)' in file_contents[i]:
            mosaic = float(file_contents[i].split()[3])
            for image in range(block_start_finish[0],
                               block_start_finish[1] + 1):
                per_image_stats[image]['mosaic'] = mosaic

        if 'OF SPOT    POSITION (PIXELS)' in file_contents[i]:
            rmsd_pixel = float(file_contents[i].split()[-1])
            for image in range(block_start_finish[0],
                               block_start_finish[1] + 1):
                per_image_stats[image]['rmsd_pixel'] = rmsd_pixel

        if 'OF SPINDLE POSITION (DEGREES)' in file_contents[i]:
            rmsd_phi = float(file_contents[i].split()[-1])
            for image in range(block_start_finish[0],
                               block_start_finish[1] + 1):
                per_image_stats[image]['rmsd_phi'] = \
                                                   rmsd_phi / oscillation_range

        # want to convert this to mm in some standard setting!
        if 'DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM' in file_contents[i]:
            beam = map(float, file_contents[i].split()[-2:])
            for image in range(block_start_finish[0],
                               block_start_finish[1] + 1):
                per_image_stats[image]['beam'] = beam
            
        if 'CRYSTAL TO DETECTOR DISTANCE (mm)' in file_contents[i]:
            distance = float(file_contents[i].split()[-1])
            for image in range(block_start_finish[0],
                               block_start_finish[1] + 1):
                per_image_stats[image]['distance'] = distance
            

    return per_image_stats

def _print_integrate_lp(integrate_lp_stats):
    '''Print the contents of the integrate.lp dictionary.'''

    images = integrate_lp_stats.keys()
    images.sort()

    for i in images:
        data = integrate_lp_stats[i]
        print '%4d %5.3f %5d %5d %5d %4.2f %6.2f' % \
              (i, data['scale'], data['strong'],
               data['overloads'], data['rejected'],
               data['mosaic'], data['distance'])

def _happy_integrate_lp(integrate_lp_stats):
    '''Return a string which explains how happy we are with the integration.'''

    images = integrate_lp_stats.keys()
    images.sort()

    results = ''

    Science.write('Report on images %d to %d' % (min(images), max(images)),
                  forward = False)

    for i in images:
        data = integrate_lp_stats[i]
    
        if data['rmsd_phi'] > 1.0 or data['rmsd_pixel'] > 1.0:
            status = '*'
            Science.write('Image %4d ... high rmsd (%f, %f)' % \
                          (i, data['rmsd_pixel'], data['rmsd_phi']),
                          forward = False)

        else:

            status = '.'
            Science.write('Image %4d ... ok' % i, forward = False)


        results += status

    return results


if __name__ == '__main__':
    integrate_lp = os.path.join(os.environ['XIA2_ROOT'], 'Wrappers', 'XDS',
                                'Doc', 'INTEGRATE.LP')
    stats = _parse_integrate_lp(integrate_lp)
    _print_integrate_lp(stats)
    print _happy_integrate_lp(stats)
