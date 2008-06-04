#!/usr/bin/env python
# Resolution.py
# 
#   Copyright (C) 2008 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th June, 2008
# 
# A module which, given an unmerged reflection file, will read through and
# calculate the distribution of I/sigma from unmerged reflections as a 
# function of resolution, along with quartiles (25%, 75%) which may help
# to make decisions when the data are anisotropic.
#

import sys
import os
import math

def compute_resolution(distance, offset, wavelength):
    '''Compute the resolution (d spacing) for the provided sample to
    detector distance, offset on the detector and wavelength. This assumes
    that the detector is orthogonal to the direct beam.'''

    theta = 0.5 * math.atan(offset / distance)
    dspacing = 0.5 * wavelength / math.sin(theta)

    return dspacing

def read_xds_ascii(xds_ascii_file, pixel_mm, distance, wavelength, beam_mm):
    '''Read the records in an XDS_ASCII.HKL reflection file and
    output a list of i, sigma, resolution for external processing.'''

    beam_x = beam_mm[1] / pixel_mm[0]
    beam_y = beam_mm[0] / pixel_mm[1]

    result = []

    for record in open(xds_ascii_file, 'r').readlines():
        if '!' in record:
            continue

        lst = record.split()

        i = float(lst[3])
        sigma = float(lst[4])
        x = pixel_mm[1] * (float(lst[5]) - beam_x)
        y = pixel_mm[0] * (float(lst[6]) - beam_y)

        offset = math.sqrt(x * x + y * y)

        resolution = compute_resolution(distance, offset, wavelength)

        result.append((i, sigma, resolution))

    return result

if __name__ == '__main__':

    xds_ascii = os.path.join(os.environ['X2TD_ROOT'],
                             'Test', 'UnitTest', 'Modules',
                             'Resolution', 'XDS_ASCII.HKL')

    xds_beam_pixel = 1158.7, 1157.6
    xds_beam = 94.46, 94.54
    xds_distance = 156.88
    xds_wavelength = 0.9790
    xds_pixel = 0.0816, 0.0816

    refl = read_xds_ascii(xds_ascii, xds_pixel, xds_distance,
                          xds_wavelength, xds_beam)
    
    for r in refl:
        print '%.2f %.2f' % (r[2], r[0] / r[1])
    
