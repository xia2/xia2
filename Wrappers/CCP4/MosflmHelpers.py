#!/usr/bin/env python
# MosflmHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 23rd June 2006
# 
# Helper functions which will make working with Mosflm in detail a little
# easier... for instance parsing the rather extensive output file to 
# decide if the integration went well or no.
# 
# FIXME 19/OCT/06 need to be able to parse the integration log to be able to 
#                 decide if it went ok for all images.
# 
# FIXME 19/OCT/06 would also be useful to be able to get an estimate of
#                 the "useful" integration limit (e.g. where the individual
#                 reflections have an I/sigma ~ 1)

import os

def _parse_mosflm_integration_output(integration_output_list):
    '''Parse mosflm output from integration, passed in as a list of
    strings.'''

    length = len(integration_output_list)

    per_image_stats = {0:{}}

    current_image = 0

    pixel_size = 0.0

    for i in range(length):
        record = integration_output_list[i]


        if 'Pixel size of' in record:
            pixel_size = float(record.replace('mm', ' ').split()[3])
        
        if 'Processing Image' in record:
            current_image = int(record.split()[2])

            if not per_image_stats.has_key(current_image):
                per_image_stats[current_image] = {'scale':1.0}

        if 'Integrating Image' in record:
            current_image = int(record.split()[2])

        if 'XCEN    YCEN  XTOFRA   XTOFD' in record:
            data = map(float, integration_output_list[i + 1].split())
            beam = (data[0], data[1])
            distance = data[3]

            per_image_stats[current_image]['beam'] = beam
            per_image_stats[current_image]['distance'] = distance

        if 'Smoothed value for refined mosaic spread' in record:
            mosaic = float(record.split()[-1])
            per_image_stats[current_image]['mosaic'] = mosaic

        if 'Final rms residual:' in record:
            residual = float(record.replace('mm', ' ').split()[3])
            # FIXME to do this need to be able to compute the
            # residual in pixels...
            rmsd = residual / pixel_size
            per_image_stats[current_image]['rmsd_pixel'] = rmsd
            per_image_stats[current_image]['rmsd_phi'] = 0.0

        if 'Real cell parameters' in record:
            cell = map(float, integration_output_list[i + 1].split())
            per_image_stats[current_image]['cell'] = cell

        if 'Spots measured on this image' in record:
            spots = int(record.split()[0])
            # FIXME this is misnamed because it matches a name in the
            # XDS version of this parser.
            per_image_stats[current_image]['strong'] = spots

        if 'are OVERLOADS' in record:
            overloads = int(record.replace(',', ' ').split()[4])
            per_image_stats[current_image]['overloads'] = overloads
            
        if 'Number of bad spots' in record:
            bad = int(record.split()[-1])
            # FIXME also with the name...
            per_image_stats[current_image]['rejected'] = bad
            
    return per_image_stats

def _print_integrate_lp(integrate_lp_stats):
    '''Print the contents of the integrate.lp dictionary.'''

    images = integrate_lp_stats.keys()
    images.sort()

    if images[0] == 0:
        images = images[1:]

    for i in images:
        data = integrate_lp_stats[i]
        print '%4d %5.3f %5d %5d %5d %4.2f %6.2f' % \
              (i, data['scale'], data['strong'],
               data['overloads'], data['rejected'],
               data.get('mosaic', 0.0), data['distance'])

if __name__ == '__main__':
    integrate_lp = os.path.join(os.environ['DPA_ROOT'], 'Wrappers', 'CCP4',
                                'Doc', 'mosflm-reintegration.log')
    stats = _parse_mosflm_integration_output(
        open(integrate_lp, 'r').readlines())
    _print_integrate_lp(stats)
    
