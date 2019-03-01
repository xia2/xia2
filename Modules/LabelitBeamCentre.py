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

from __future__ import absolute_import, division, print_function

import os
import sys

from xia2.Modules.Indexer.LabelitIndexer import LabelitIndexer


def compute_beam_centre(sweep, working_directory=None):
    """Compute the beam centre for the input sweep, working in the provided
    directory, perhaps."""

    if working_directory is None:
        working_directory = os.getcwd()

    beam_centre = sweep.get_beam_centre()

    # perhaps fiddle with the beam_centre here, and hide the indexing output
    # that is a side-effect of this.

    try:
        ls = LabelitIndexer(indxr_print=False)
        ls.set_working_directory(working_directory)
        ls.setup_from_imageset(sweep.get_imageset())
        beam_centre = ls.get_indexer_beam_centre()
    except Exception:
        # do not have labelit installed?
        # need to check the exception
        # import sys
        # import traceback
        # traceback.print_exc(sys.stderr)

        return None

    return beam_centre


if __name__ == "__main__":

    from xia2.Experts.FindImages import image2template_directory
    from xia2.Schema.Sweep import SweepFactory

    if len(sys.argv) < 2:
        image = os.path.join(
            os.environ["XIA2_ROOT"], "Data", "Test", "Images", "12287_1_E1_001.img"
        )
    else:
        image = sys.argv[1]

    template, directory = image2template_directory(image)

    sl = SweepFactory(template, directory)

    for s in sl:

        print("%6.2f %6.2f" % compute_beam_centre(s))
