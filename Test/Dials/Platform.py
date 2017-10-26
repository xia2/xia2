#!/usr/bin/env python
# Platform.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Test platform for new Dials wrapper implementations.

from __future__ import absolute_import, division

import sys

from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

class Platform(FrameProcessor):
  def __init__(self, image):
    super(Platform, self).__init__()

  def findspots(self, images):
    from xia2.Wrappers.Dials.DialsSpotfinder import DialsSpotfinder
    fs = DialsSpotfinder()
    return fs(self, images)

def tst_findspots(image):
  p = Platform(image)
  return p.findspots(p.get_matching_images()[:10])

def tst_all():
  tst_findspots(sys.argv[1])
  print 'OK'

if __name__ == '__main__':
  tst_all()
