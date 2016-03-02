#!/usr/bin/env python
# Platform.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Test platform for new Mosflm wrapper implementations.

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

  def header(self, images):
    from Wrappers.Mosflm.Header import Header
    h = Header()
    return h(self, images)

  def findspots(self, images):
    from Wrappers.Mosflm.Findspots import Findspots
    fs = Findspots()
    return fs(self, images)

  def autoindex(self, images = None):
    from Wrappers.Mosflm.Autoindex import Autoindex
    ai = Autoindex()
    return ai(self, images)

  def findspots_autoindex(self, images = None):
    from Wrappers.Mosflm.Findspots import Findspots
    from Wrappers.Mosflm.Autoindex import Autoindex

    ai = Autoindex()

    if images is None:
      images = ai.select_images(self)

    fs = Findspots()
    ai.set_spot_file(fs(self, images))
    return ai(self, images)

  def findspots_autoindex_randomize(self, images = None):
    from Wrappers.Mosflm.Findspots import Findspots
    from Wrappers.Mosflm.Autoindex import Autoindex
    from Wrappers.Mosflm.Exceptions import AutoindexError

    ai = Autoindex()

    if images is None:
      images = ai.select_images(self)

    fs = Findspots()
    spot_file = fs(self, images)
    from PlatformHelpers import randomize_spots
    spot_file = randomize_spots(spot_file)
    ai.set_spot_file(spot_file)
    try:
      solutions = ai(self, images)
    except AutoindexError, e:
      return

    raise RuntimeError, 'should not get here'

def tst_autoindex(image):
  p = Platform(image)
  return p.autoindex(p.get_matching_images()[:1])

def tst_findspots(image):
  p = Platform(image)
  return p.findspots(p.get_matching_images()[:1])

def tst_findspots_autoindex(image):
  p = Platform(image)
  return p.findspots_autoindex(p.get_matching_images()[:1])

def tst_findspots_autoindex_randomize(image):
  p = Platform(image)
  return p.findspots_autoindex_randomize(p.get_matching_images()[:1])

def tst_findspots_autoindex_select(image):
  p = Platform(image)
  return p.findspots_autoindex()

def tst_header(image):
  p = Platform(image)
  return p.header(p.get_matching_images())

def tst_all():
  import sys
  tst_header(sys.argv[1])
  tst_findspots(sys.argv[1])
  tst_autoindex(sys.argv[1])
  tst_findspots_autoindex(sys.argv[1])
  tst_findspots_autoindex_select(sys.argv[1])
  tst_findspots_autoindex_randomize(sys.argv[1])
  print 'OK'

if __name__ == '__main__':
  tst_all()
