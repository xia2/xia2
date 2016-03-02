#!/usr/bin/env python
# XDSIndexerInteractive.py
#   Copyright (C) 2013 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Interactive indexing with XDS: at the moment this means just selecting which
# images you want to use for indexing though FIXME it should be possible to
# have the indexing fully interactive i.e. user can run index, select solution,
# change images to use etc. so it becomes fully interactive.

import os
import sys

# the class that we are extending

from XDSIndexer import XDSIndexer

# odds and sods that are needed

from xia2.Handlers.Streams import Chatter

class XDSIndexerInteractive(XDSIndexer):
  '''An extension of XDSIndexer using all available images.'''

  def __init__(self):
    super(XDSIndexerInteractive, self).__init__()
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
