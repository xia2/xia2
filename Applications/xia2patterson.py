#!/usr/bin/env python
# xia2patterson
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.

import sys
import os

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Experts.PattersonExpert import anomalous_patterson_jiffy

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise RuntimeError, '%s hklin [symmetry]' % sys.argv[0]

    hklin = sys.argv[1]
    if len(sys.argv) > 2:
        symmetry = sys.argv[2]
    else:
        symmetry = None

    if len(sys.argv) > 4:
        dmin, dmax = tuple(map(float, sys.argv[3:5]))
    else:
        dmin = None
        dmax = None

    peaks = anomalous_patterson_jiffy(hklin, symmetry,
                                      dmin = dmin, dmax = dmax)

    for p in peaks:
        print '%6.2f %6.2f %6.2f %6.2f' % p
    

