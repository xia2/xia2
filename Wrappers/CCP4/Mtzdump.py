#!/usr/bin/env python
# Mtzdump.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 5th June 2006
#
# A wrapper for the CCP4 program mtzdump, for displaying the header
# information from an MTZ file.
#
# Provides:
#
# The content of the MTZ file header, as a dictionary.
#

from __future__ import absolute_import, division, print_function

import sys

def Mtzdump(DriverType = None):
  '''A factory for MtzdumpWrapper classes.'''

  from xia2.Modules.Mtzdump import Mtzdump as _Mtzdump
  return _Mtzdump()

if __name__ == '__main__':
  m = Mtzdump()

  if len(sys.argv) > 1:
    m.set_hklin(sys.argv[1])
  else:
    raise RuntimeError('%s hklin.mtz' % sys.argv[0])

  m.dump()
  print(m.get_spacegroup())
