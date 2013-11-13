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

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Schema.Interfaces.FrameProcessor import FrameProcessor

class Platform(FrameProcessor):
  def __init__(self, image):
    FrameProcessor.__init__(self, image)

  def findspots(self, images):
    from Wrappers.Dials.DialsSpotfinder import DialsSpotfinder
    fs = DialsSpotfinder()
    return fs(self, images)

def tst_findspots(image):
  p = Platform(image)
  return p.findspots(p.get_matching_images()[:1])

def tst_all():
  import sys
  tst_findspots(sys.argv[1])
  print 'OK'

if __name__ == '__main__':
  tst_all()
