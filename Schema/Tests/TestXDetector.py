#!/usr/bin/env python
# TestXDetector.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Tests for the XDetector class.

import math
import os
import sys

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.XDetector import XDetector
from Schema.XDetector import XDetectorFactory

def TestXDetector():
    '''A test class for the XDetector class.'''

    d = XDetectorFactory.Simple(100.0, (45.0, 52.0), '+x', '-y',
                                (0.172, 0.172), (516, 590), 1024, [])

    print d

    t = XDetectorFactory.TwoTheta(60.0, (35.0, 34.0), '+x', '+y', '+x', 30,
                                  (0.07, 0.07), (1042, 1042), 1024, [])

    print t

    c = XDetectorFactory.imgCIF('phi_scan.cbf')

    print c

def WorkXDetector():

    for j in range(10000):
        c = XDetectorFactory.imgCIF('phi_scan.cbf')

if __name__ == '__main__':

    TestXDetector()

