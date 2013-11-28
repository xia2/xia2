#!/usr/bin/env python
# Say.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Say stuff, if on OS X

from __future__ import division

def Say(what):
  import os
  if os.name != 'posix':
    return
  say = os.path.join('/', 'usr', 'bin', 'say')
  if not os.path.exists(say):
    return
  os.system('%s %s' % (say, what))
  return            

if __name__ == '__main__':
  Say('Hello world')
