# A module to get the "best" beam centre from a labelit run. This will be
# used from within xia2setup.py as a key part of configuring the .xinfo
# file.
#
# Note well that this will check the input beam centres from the header to
# see what they are before they start, and perhaps will set a sensible
# input default (e.g. the middle of the image) for the labelit run.

from __future__ import absolute_import, division, print_function

import os

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
        return None

    return beam_centre
