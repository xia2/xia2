#!/usr/bin/env python
# xia2process.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.


#
# 16th August 2006
# 
# A small program for integration with Labelit & Mosflm - this will perform
# a reasonably thorough integration of the data with the intention of 
# growing into a full data reduction application.
# 
# 04/SEP/06 FIXME this should go to the factories to get the implementations,
#           not code in static implementations.
# 04/SEP/06 FIXME need to start passing information into the output streams,
#           too...

import sys
import os

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.CommandLine import CommandLine
from Schema.Sweep import SweepFactory

# program wrappers we will use
from Wrappers.CCP4.Mosflm import Mosflm

# want to move over more like this...
from Modules.IndexerFactory import Indexer
from Modules.IntegraterFactory import Integrater

from Handlers.Streams import Chatter

def xia2process():
    '''Do it!'''

    # m = Mosflm()

    i = Indexer()

    # check to see if a beam has been specified

    beam = CommandLine.get_beam()

    if beam[0] * beam[1] > 0.0:
        i.set_beam(beam)

    # check that an image has been specified

    if CommandLine.get_image() is None:
        raise RuntimeError, 'must specify an image via -image'

    # this will result in a run of printheader

    i.setup_from_image(CommandLine.get_image())

    if CommandLine.get_lattice():
        i.set_indexer_input_lattice(CommandLine.get_lattice())

    # phi_width = m.getHeader_item('phi_width')
    # images = m.getMatching_images()

    # FIXME this should be done automatically through the
    # indexer interface... now done!

    # m.add_indexer_image_wedge(images[0])
    # if int(90 / phi_width) in images:
    # m.add_indexer_image_wedge(int(90/ phi_width))
    # else:
    # m.add_indexer_image_wedge(images[-1])

    # create a new mosflm here just to show that you can
    # FIXME this should really work as
    # 
    # n = Integrater(i)
    # 
    # which will delegate it to an IntegraterFactory, and through
    # to an appropriate constructor.
    # FIXME 2 - the setup_from_image should be inherited through
    # passing in an Indexer implementation.

    # n = Mosflm()
    # n.setup_from_image(CommandLine.getImage())
    # n.set_integrater_indexer(i)

    Chatter.write('Refined beam is: %6.2f %6.2f' % i.get_indexer_beam())
    Chatter.write('Distance:        %6.2f' % i.get_indexer_distance())
    Chatter.write('Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                  i.get_indexer_cell())
    Chatter.write('Lattice: %s' % i.get_indexer_lattice())
    Chatter.write('Mosaic: %6.2f' % i.get_indexer_mosaic())
    Chatter.write('Index resolution estimate: %5.2f' % \
                  i.get_indexer_resolution())

    n = Integrater()
    n.setup_from_image(CommandLine.get_image())
    n.set_integrater_indexer(i)

    # check for resolution limit
    if CommandLine.get_resolution_limit() > 0.0:
        n.set_integrater_high_resolution(CommandLine.get_resolution_limit())

    hklout = n.get_integrater_reflections()

    # print out a little information about the lattice

    Chatter.write('After processing...')

    Chatter.write('Refined beam is: %6.2f %6.2f' % i.get_indexer_beam())
    Chatter.write('Distance:        %6.2f' % i.get_indexer_distance())
    Chatter.write('Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' %
                   i.get_indexer_cell())
    Chatter.write('Lattice: %s' % i.get_indexer_lattice())
    Chatter.write('Mosaic: %6.2f' % i.get_indexer_mosaic())
    Chatter.write('Hklout: %s' % hklout)

if __name__ == '__main__':
    xia2process()

            
            
