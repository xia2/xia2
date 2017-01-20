#!/usr/bin/env python
# DecoratorHelper.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 21st June 2006
#
# Helper functions for Decorator implementations.
#

from __future__ import absolute_import, division

def inherits_from(this_class,
                  base_class_name):
  '''Return True if base_class_name contributes to the this_class class.'''

  if this_class.__bases__:
    for b in this_class.__bases__:
      if inherits_from(b, base_class_name):
        return True

  if this_class.__name__ == base_class_name:
    return True

  return False

if __name__ == '__main__':
  # run a test

  class A(object):
    pass

  class B(A):
    pass

  class C(object):
    pass

  if inherits_from(B, 'A'):
    print 'ok'
  else:
    print 'failed'

  if not inherits_from(C, 'A'):
    print 'ok'
  else:
    print 'failed'
