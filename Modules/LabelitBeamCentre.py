#!/usr/bin/env python
# LabelitBeamCentre.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A module to get the "best" beam centre from a labelit run. This will be
# used from within xia2setup.py as a key part of configuring the .xinfo
# file.
#
# Note well that this will check the input beam centres from the header to
# see what they are before they start, and perhaps will set a sensible
# input default (e.g. the middle of the image) for the labelit run.
#
#

import os
import sys
import exceptions
import time

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.Labelit.LabelitIndex import LabelitIndex

def compute_beam_centre(sweep, working_directory = os.getcwd()):
    '''Compute the beam centre for the input sweep, working in the provided
    directory, perhaps.'''

    beam = sweep.get_beam()

    # perhaps fiddle with the beam here, and hide the indexing output
    # that is a side-effect of this.

    try:
        ls = LabelitIndex(indxr_print = False)
        ls.setup_from_image(sweep.imagename(min(sweep.get_images())))
        beam = ls.get_indexer_beam()
    except exceptions.Exception, e:
        # do not have labelit installed?
        # need to check the exception
        return None

    return beam

if __name__ == '__main__':

    from Experts.FindImages import image2template_directory
    from Schema.Sweep import SweepFactory

    if len(sys.argv) < 2:
        image = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img')
    else:
        image = sys.argv[1]

    template, directory = image2template_directory(image)

    sl = SweepFactory(template, directory)

    for s in sl:

        print '%6.2f %6.2f' % compute_beam_centre(s)
