#!/usr/bin/env python
# XDSIndexerInteractive.py
#   Copyright (C) 2013 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

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

# odds and sods that are needed

from lib.bits import auto_logfiler, nint
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

class XDSIndexerInteractive(XDSIndexer):
  '''An extension of XDSIndexer using all available images.'''

  def __init__(self):

    # set up the inherited objects

    XDSIndexer.__init__(self)
    self._index_select_images = 'interactive'

    return

  # helper functions

  def _index_select_images_interactive(self):

    phi_width = self.get_header_item('phi_width')

    # use five degrees for the background calculation

    five_deg = int(round(5.0 / phi_width)) - 1

    if five_deg < 5:
      five_deg = 5

    images = self.get_matching_images()

    from IndexerSelectImages import index_select_image_wedges_user
    
    wedges = index_select_image_wedges_user(
      self._fp_template, phi_width, images, Chatter)

    if min(images) + five_deg in images:
      self._background_images = (min(images), min(images) + five_deg)
    else:
      self._background_images = (min(images), max(images))

    return wedges

