#!/usr/bin/env python
# PattersonExpert.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# 24th July 2007
# 
# A small expert to handle patterson map calculations. This will factor in
# things like the symmetry of the crystal in the analysis.

import os
import sys
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.Fft import Fft
from Wrappers.CCP4.Mtzdump import Mtzdump
from Wrappers.CCP4.Peakmax import Peakmax
from Wrappers.CCP4.Mapmask import Mapmask
from Wrappers.CCP4.Scaleit import Scaleit

def anomalous_patterson_jiffy(hklin, symmetry, working_directory, scratch):
    '''Run a Patterson calculation: scaleit -> fft -> mapmask -> peakmax
    with the intention of getting a meaningful list of peaks out. Scratch
    is a temporary name for temporary map files etc.'''

    # get the resolution limits out etc.

    mtzdump = Mtzdump()
    mtzdump.set_hklin(hklin)
    mtzdump.dump()
    dmin, dmax = mtzdump.get_resolution_range()
    datasets = mtzdump.get_datasets()
    
    if len(datasets) > 1:
        raise RuntimeError, 'more than one dataset for anomalous Patterson'

    hklout = os.path.join(os.environ['CCP4_SCR'], '%s-scaleit.mtz' % scratch)

    # find the maximum aceptable difference

    scaleit = Scaleit()
    scaleit.set_working_directory(working_directory)
    scaleit.set_hklin(hklin)
    scaleit.set_hklout(hklout)
    scaleit.set_anomalous(True)
    scaleit.scaleit()
    max_diff = scaleit.get_statistics()['max_difference']

    mapout = os.path.join(os.environ['CCP4_SCR'], '%s-fft.map' % scratch)

    # calculate the full anomalous difference Patterson 

    fft = Fft()
    fft.set_working_directory(working_directory)
    fft.set_symmetry(symmetry)
    fft.set_hklin(hklin)
    fft.set_mapout(mapout)
    fft.set_resolution_range(dmin, dmax)
    fft.set_exclude_term(max_diff * max_diff)
    fft.set_dataset(datasets[0].split('/')[-1])
    fft.patterson()

    mapin = mapout
    mapout = os.path.join(os.environ['CCP4_SCR'], '%s-mapmask.map' % scratch)
    
    # cut the map down to the ASU

    mapmask = Mapmask()
    mapmask.set_working_directory(working_directory)
    mapmask.set_mapin(mapin)
    mapmask.set_mapout(mapout)
    mapmask.set_symmetry(symmetry)
    mapmask.mask_asu()

    mapin = mapout
    xyzout = os.path.join(os.environ['CCP4_SCR'], '%s-peakmax.pdb' % scratch)

    # now run a peak search

    peakmax = Peakmax()
    peakmax.set_working_directory(working_directory)
    peakmax.set_mapin(mapin)
    peakmax.set_xyzout(xyzout)
    peakmax.set_rms(5.0)
    peakmax.peaksearch()

    # now read the peak list

    peaks = []

    for record in open(xyzout, 'r').readlines():
        if 'ATOM' in record[:4]:
            x = float(record[30:38].strip())
            y = float(record[38:46].strip())
            z = float(record[46:54].strip())
            o = float(record[54:60].strip())

            peaks.append((x, y, z, o))

    return peaks

if __name__ == '__main__':

    scratch = 'test'
    working_directory = os.getcwd()
    symmetry = 'P212121'
    hklin = '/Users/graeme/Projects/Patterson/ppe/analyse/PPE_X150A_free.mtz'
    
    peaks = anomalous_patterson_jiffy(hklin, symmetry,
                                      working_directory, scratch)

    for p in peaks:
        print '%6.2f %6.2f %6.2f %6.2f' % p
