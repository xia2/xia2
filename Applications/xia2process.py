#!/usr/bin/env python
# xia2process.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th August 2006
# 
# A small program for integration with Labelit & Mosflm - this will perform
# a reasonably thorough integration of the data with the intention of 
# growing into a full data reduction application.
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
from Wrappers.CCP4.Mosflm import Mosflm

def xia2process():
    '''Do it!'''

    m = Mosflm()

    # check to see if a beam has been specified

    beam = CommandLine.getBeam()

    if beam[0] * beam[1] > 0.0:
        m.setBeam(beam)

    # this will result in a run of printheader

    m.setup_from_image(CommandLine.getImage())

    if CommandLine.getLattice():
        m.set_indexer_input_lattice(CommandLine.getLattice())

    phi_width = m.getHeader_item('phi_width')
    images = m.getMatching_images()

    # FIXME this should be done automatically through the
    # indexer interface... now done!

    # m.add_indexer_image_wedge(images[0])
    # if int(90 / phi_width) in images:
    # m.add_indexer_image_wedge(int(90/ phi_width))
    # else:
    # m.add_indexer_image_wedge(images[-1])

    # create a new mosflm here just to show that you can

    n = Mosflm()
    n.setup_from_image(CommandLine.getImage())
    n.integrate_set_indexer(m)

    # check for resolution limit
    if CommandLine.getResolution_limit() > 0.0:
        n.integrate_set_high_resolution(CommandLine.getResolution_limit())

    hklout = n.integrate()

    # print out a little information about the lattice

    print 'Refined beam is: %6.2f %6.2f' % m.get_indexer_beam()
    print 'Distance:        %6.2f' % m.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % m.get_indexer_cell()
    print 'Lattice: %s' % m.get_indexer_lattice()
    print 'Mosaic: %6.2f' % m.get_indexer_mosaic()
    print 'Hklout: %s' % hklout

if __name__ == '__main__':
    xia2process()

            
            
