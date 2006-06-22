#!/usr/bin/env python
# xia2scan.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 9th June 2006
# 
# A small program to summarise the diffraction strength from a list of
# diffraction images. This will use labelit for both indexing and 
# distling.
# 
# Requires:
# 
# The correct beam centre.
# 
# 

import sys
import os

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Handlers.CommandLine import CommandLine
from Schema.Sweep import SweepFactory

# program wrappers we will use
from Wrappers.Labelit.LabelitScreen import LabelitScreen
from Wrappers.Labelit.LabelitStats_distl import LabelitStats_distl

def xia2scan():
    '''Do the scan.'''

    template, directory = CommandLine.getTemplate(), \
                          CommandLine.getDirectory()

    if not template or not directory:
        raise RuntimeError, 'no image information supplied'

    # if this isnot set, then we will presume that it is correct
    # in the image headers
    
    beam = CommandLine.getBeam()

    sweeps = SweepFactory(template, directory, beam)

    summary_info = { }

    for s in sweeps:

        # if > 1 image then these are probably stills... but we don't care
        # about that!

        for i in s.getImages():
            sys.stdout.write('.')
            sys.stdout.flush()

            beam = s.getBeam()

            ls = LabelitScreen()
            ls.addImage(s.imagename(i))
            ls.setBeam(beam[0], beam[1])
            ls.setRefine_beam(False)
            ls.index()

            solution = ls.getSolutions()[1]
            # P1 cell is always solution #1
            lsd = LabelitStats_distl()
            lsd.stats_distl()
            stats = lsd.getStatistics(s.imagename(i))
            summary_info[i] = { }
            summary_info[i]['volume'] = solution['volume']
            summary_info[i]['mosaic'] = solution['mosaic']
            summary_info[i]['spots_good'] = stats['spots_good']
            summary_info[i]['spots_total'] = stats['spots_total']
            summary_info[i]['resol_one'] = stats['resol_one']
            summary_info[i]['resol_two'] = stats['resol_two']

    sys.stdout.write('\n')

    images = summary_info.keys()
    images.sort()
    for i in images:
        print '%3d %6d %6d %6.2f %6.2f %6.2f %9d' % \
              (i, summary_info[i]['spots_total'],
               summary_info[i]['spots_good'],
               summary_info[i]['resol_one'],
               summary_info[i]['resol_two'],
               summary_info[i]['mosaic'],
               summary_info[i]['volume'])

if __name__ == '__main__':
    xia2scan()

    
