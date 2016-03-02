#!/usr/bin/env python
# pydiffdump.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Use the registry / new image header reading code to read images and print
# out what is going on...
#
# 03/MAR/16
# To resolve the naming conflict between this file and the entire xia2 module
# any xia2.* imports in this directory must instead be imported as ..*

import os
import sys
import time

from dxtbx.format.Registry import Registry

def pydiffdump(files):
  '''Print the class which claims to work with each file.'''

  s = time.time()

  for f in files:

    print f

    format = Registry.find(f)

    print format.__name__

    if format.understand(f):
      i = format(f)

      print 'Beam:'
      print i.get_beam()
      print 'Goniometer:'
      print i.get_goniometer()
      print 'Detector:'
      print i.get_detector()
      print 'Scan:'
      print i.get_scan()

  return time.time() - s

def pydiffdump_fast(files):
  '''First find the class, then read every frame with it.'''

  s = time.time()

  format = Registry.find(files[0])

  scan = None

  for f in files:

    i = format(f)
    print 'Beam:'
    print i.get_xbeam()
    print 'Goniometer:'
    print i.get_xgoniometer()
    print 'Detector:'
    print i.get_xdetector()
    print 'Scan:'
    print i.get_xscan()

    if scan is None:
      scan = i.get_xscan()
    else:
      scan += i.get_xscan()

  print scan

  return time.time() - s

if __name__ == '__main__':

  t = pydiffdump(sys.argv[1:])

  print 'Reading %d headers took %.1fs' % (len(sys.argv[1:]), t)
