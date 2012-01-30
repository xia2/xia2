#!/usr/bin/env python
# xia2pointgroup.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.


#
# 10th August 2006
#
# A small program to integrate in P1 a wedge of images and display
# the output of pointless run on these images.
#
# FIXME this is probably not using the proper interfaces...
#

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
from Wrappers.Labelit.LabelitIndex import LabelitIndex
from Wrappers.CCP4.Mosflm import Mosflm
from Wrappers.CCP4.Pointless import Pointless

def xia2pointgroup():
    '''Do it!'''

    l = LabelitIndex()

    l.setup_from_image(CommandLine.get_image())

    phi_width = l.get_header_item('phi_width')
    images = l.get_matching_images()

    # shouldn't need this any more
    l.add_indexer_image_wedge(images[0])
    if int(90 / phi_width) in images:
        l.add_indexer_image_wedge(int(90.0 / phi_width))
    else:
        l.add_indexer_image_wedge(images[-1])

    # integrate in P1
    l.set_indexer_input_lattice('aP')

    for width in [5.0, 10.0, 15.0, 30.0]:
        if len(images) * phi_width >= width:
            m = Mosflm()
            m.setup_from_image(CommandLine.get_image())
            m.set_integrater_indexer(l)
            m.set_integrater_wedge(images[0],
                                   images[0] + int(width / phi_width))

            p = Pointless()
            hklout = m.integrate()
            p.set_hklin(hklout)
            p.decide_pointgroup()

            print '%f %s %f' % (width, p.get_pointgroup(), p.get_confidence())

if __name__ == '__main__':
    xia2pointgroup()
