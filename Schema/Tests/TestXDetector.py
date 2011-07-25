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
from scitbx import matrix

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.XDetector import XDetector
from Schema.XDetector import XDetectorFactory
from Schema.XDetectorHelpers import read_xds_xparm
from Schema.XDetectorHelpers import compute_frame_rotation

def TestXDetector():
    '''A test class for the XDetector class.'''

    d = XDetectorFactory.Simple(100.0, (45.0, 52.0), '+x', '-y',
                                (0.172, 0.172), (516, 590), 1024, [])
    t = XDetectorFactory.TwoTheta(60.0, (35.0, 34.0), '+x', '+y', '+x', 30,
                                  (0.07, 0.07), (1042, 1042), 1024, [])
    c = XDetectorFactory.imgCIF('phi_scan.cbf')
    x = XDetectorFactory.XDS('example-xparm.xds')

    print t
    print x

def WorkXDetector():

    for j in range(10000):
        c = XDetectorFactory.imgCIF('phi_scan.cbf')

def WorkXDetectorHelpers():
    compute_frame_rotation((matrix.col((1, 0, 0)),
                            matrix.col((0, 1, 0)),
                            matrix.col((0, 0, 1))),
                           (matrix.col((1, 0, 0)),
                            matrix.col((0, 1, 0)),
                            matrix.col((0, 0, 1))))
    
    compute_frame_rotation((matrix.col((-1, 0, 0)),
                            matrix.col((0, 0, 1)),
                            matrix.col((0, 1, 0))),
                           (matrix.col((1, 0, 0)),
                            matrix.col((0, 1, 0)),
                            matrix.col((0, 0, 1))))

if __name__ == '__main__':

    # WorkXDetectorHelpers()
    TestXDetector()

