# ExampleProgramRaiseException.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 27/MAR/06
#
# An example program to test input, output, job control etc. in the new
# XIA. This one will raise an exception on startup (e.g. this must be
# handled equivalently to a load library missing).

from __future__ import absolute_import, division, print_function

__doc__ = '''A small program which will raise an exception on startup,
for testing of the XIA core.'''

def run():
  raise RuntimeError('program run')

if __name__ == '__main__':
  run()
