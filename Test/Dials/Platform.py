#!/usr/bin/env python
# Platform.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Test platform for new Dials wrapper implementations.

from __future__ import division
import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Schema.Interfaces.FrameProcessor import FrameProcessor

class Platform(FrameProcessor):
  def __init__(self, image):
    super(Platform, self).__init__()

  def findspots(self, images):
    from Wrappers.Dials.DialsSpotfinder import DialsSpotfinder
    fs = DialsSpotfinder()
    return fs(self, images)

def tst_findspots(image):
  p = Platform(image)
  return p.findspots(p.get_matching_images()[:10])

def tst_all():
  import sys
  tst_findspots(sys.argv[1])
  print 'OK'

if __name__ == '__main__':
  tst_all()
