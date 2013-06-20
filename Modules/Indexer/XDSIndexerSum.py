#!/usr/bin/env python
# XDSIndexerSum.py
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter & Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 20th June 2013
#
# An reimplementation of the XDS indexer to work by first summing images before
# the spot finding for indexing. May or may not help...

import os
import sys
import math
import exceptions

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the class that we are extending

from XDSIndexer import XDSIndexer

# wrappers for programs that this needs

from Wrappers.XIA.Diffdump import Diffdump

# helper functions

from Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from Wrappers.XDS.XDS import beam_centre_xds_to_mosflm
from Wrappers.XDS.XDS import XDSException
from Modules.Indexer.XDSCheckIndexerSolution import xds_check_indexer_solution

# interfaces that this must implement to be an indexer - though these
# are inherited implicitly

# from Schema.Interfaces.Indexer import Indexer
# from Schema.Interfaces.FrameProcessor import FrameProcessor

# odds and sods that are needed

from lib.bits import auto_logfiler, nint
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Phil import Phil
from Handlers.Files import FileHandler

# FIXME need to put in access here to Phil parameters to know how wide to make
# the summed images

class XDSIndexerII(XDSIndexer):
    '''An extension of XDSIndexer using all available images.'''

    def __init__(self):

        # set up the inherited objects

        XDSIndexer.__init__(self)

        return

    # helper functions

    def _index_select_images(self):
        '''Select correct images based on image headers.'''

        # FIXME in here (i) sum the images defined from the existing class
        # contents then (ii) change the template stored, the directory and
        # the header contents to correspond to those new images. Finally make
        # a note of these changes so we can correct XPARM file at the end.
        
        assert(min(self.get_matching_images()) == 1)


        phi_width = self.get_header_item('phi_width')

        if phi_width == 0.0:
            raise RuntimeError, 'cannot use still images'
        
        # use five degrees for the background calculation

        five_deg = int(round(5.0 / phi_width)) - 1

        if five_deg < 5:
            five_deg = 5

        images = self.get_matching_images()

        # characterise the images - are there just two (e.g. dna-style
        # reference images) or is there a full block? if it is the
        # former then we have a problem, as we want *all* the images in the
        # sweep...

        wedges = []

        if len(images) < 3 and len(images) < Flags.get_min_images():
            raise RuntimeError, \
                  'This INDEXER cannot be used for only %d images' % \
                  len(images)

        Debug.write('Adding images for indexer: %d -> %d' % \
                    (min(images), max(images)))

        wedges.append((min(images), max(images)))

        # FIXME this should have a wrapper function!

        if min(images) + five_deg in images:
            self._background_images = (min(images), min(images) + five_deg)
        else:
            self._background_images = (min(images), max(images))

        return wedges

    # FIXME here override _index_finish by calling original _index_finish
    # then correcting the XPARM file as mentioned above.
