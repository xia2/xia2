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

# the class that we are extending

from XDSIndexer import XDSIndexer

# odds and sods that are needed

from xia2.Handlers.Streams import Debug
from xia2.Handlers.Phil import PhilIndex

# FIXME need to put in access here to Phil parameters to know how wide to make
# the summed images

from xia2.Wrappers.XDS.Merge2cbf import Merge2cbf

class XDSIndexerSum(XDSIndexer):
  '''An extension of XDSIndexer using all available images.'''

  def __init__(self):
    super(XDSIndexerSum, self).__init__()

    # XDSIndexer.__init__ modfies this!
    self._index_select_images = _index_select_images

    return

  # helper functions

  def _index_select_images(self):
    '''Select correct images based on image headers.'''

    # FIXME in here (i) sum the images defined from the existing class
    # contents then (ii) change the template stored, the directory and
    # the header contents to correspond to those new images. Finally make
    # a note of these changes so we can correct XPARM file at the end.

    assert(min(self.get_matching_images()) == 1)

    # make a note so we can fix the XPARM.XDS file at the end
    self._true_phi_width = self.get_header_item('phi_width')

    params = PhilIndex.params.xds.merge2cbf
    if params.data_range is None:
      params.data_range = 1, len(self.get_matching_images())
    m2c = Merge2cbf(params=params)
    m2c.setup_from_image(self.get_image_name(1))
    m2c.set_working_directory(os.path.join(
        self.get_working_directory(), 'summed_images'))
    os.mkdir(m2c.get_working_directory())
    m2c.run()

    # Is this safe to do?
    self._setup_from_image(
        os.path.join(m2c.get_working_directory(),
                     'merge2cbf_averaged_0001.cbf'))

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

    min_images = params.xia2.settings.input.min_images

    if len(images) < 3 and len(images) < min_images:
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

  def _index_finish(self):
    self._modify_xparm_xds()
    XDSIndexer._index_finish(self)

  def _modify_xparm_xds(self):
    import fileinput
    xparm_filename = os.path.join(
        self.get_working_directory(), 'XPARM.XDS')
    assert os.path.isfile(xparm_filename)
    f = fileinput.input(xparm_filename, mode='rb', inplace=1)
    updated_oscillation_range = False
    for line in f:
      if not updated_oscillation_range:
        # Starting image number (STARTING_FRAME=),
        # spindle angle at start (STARTING_ANGLE=),
        # oscillation range,
        # and laboratory coordinates of the rotation axis.
        tokens = line.split()
        if len(tokens) == 6:
          summed_oscillation_range = float(tokens[2])
          # sanity check - is this actually necessary?
          assert (summed_oscillation_range
                  - self.get_header_item('phi_width')) < 1e-6
          tokens[2] = '%.4f' %self._true_phi_width
          print " ".join(tokens)
          continue
      print line,
    f.close()

    # copy across file contents internally
    self._data_files['XPARM.XDS'] = open(xparm_filename, mode='rb').read()
