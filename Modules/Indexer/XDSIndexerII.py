#!/usr/bin/env python
# XDSIndexerII.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th June 2008
# 
# An reimplementation of the XDS indexer to work for harder cases, for example
# cases where the whole sweep needs to be read into memory in IDXREF to get 
# a decent indexing solution (these do happen) and also cases where the 
# crystal is highly mosaic. Perhaps. This will now be directly inherited from
# the original XDSIndexer and only the necessary method overloaded (as I
# should have done this in the first place.)

import os
import sys
import math

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

from lib.Guff import auto_logfiler, nint
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags

class XDSIndexerII(XDSIndexer):
    '''An extension of XDSIndexer using all available images.'''

    def __init__(self):

        # set up the inherited objects
        
        XDSIndexer.__init__(self)

        return

    # helper functions

    def _index_select_images(self):
        '''Select correct images based on image headers.'''
        
        phi_width = self.get_header_item('phi_width')
        
        if phi_width == 0.0:
            Debug.write('Phi width 0.0? Assuming 1.0!')
            phi_width = 1.0

        # use five degrees for the background calculation

        five_deg = int(round(5.0 / phi_width)) - 1

        if five_deg < 5:
            five_deg = 5

        images = self.get_matching_images()

        # characterise the images - are there just two (e.g. dna-style
        # reference images) or is there a full block? if it is the
        # former then we have a problem, as we want *all* the images in the
        # sweep...

        if len(images) < 3:
            raise RuntimeError, \
                  'This INDEXER cannot be used for only 2 images'

        Debug.write('Adding images for indexer: %d -> %d' % \
                    (min(images), max(images)))
        
        self.add_indexer_image_wedge((min(images), max(images)))

        # FIXME this should have a wrapper function!

        if min(images) + five_deg in images:
            self._background_images = (min(images), min(images) + five_deg)
        else:
            self._background_images = (min(images), max(images))

        # FIXME this also needs to generate a list of images to use for
        # the background calculation as this is currently bodged a little
        # in the old implementation - look at init.set_background_range
        # in XDSIndexer...
        
        return


    
