#!/usr/bin/env python
# TestXGoniometer.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Tests for the XGoniometer class.

import math
import os
import sys

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.XGoniometer import XGoniometer
from Schema.XGoniometer import XGoniometerFactory

def compare_tuples(a, b, tol = 1.0e-6):
    
    assert(len(a) == len(b))
    
    for j in range(len(a)):
        if math.fabs(b[j] - a[j]) > tol:
            return False

    return True

def TestXGoniometer():
    '''A test class for the XGoniometer class.'''

    axis = (1, 0, 0)
    fixed = (1, 0, 0, 0, 1, 0, 0, 0, 1)

    xg = XGoniometer(axis, fixed)

    assert(len(xg.get_axis()) == 3)
    assert(len(xg.get_fixed()) == 9)

    assert(compare_tuples(xg.get_axis(), axis))
    assert(compare_tuples(xg.get_fixed(), fixed))

    single = XGoniometerFactory.SingleAxis()

    assert(len(single.get_axis()) == 3)
    assert(len(single.get_fixed()) == 9)

    assert(compare_tuples(single.get_axis(), axis))
    assert(compare_tuples(single.get_fixed(), fixed))

    kappa = XGoniometerFactory.Kappa(50.0, 0.0, 0.0, 0.0, '-y', 'omega')

    assert(len(single.get_axis()) == 3)
    assert(len(single.get_fixed()) == 9)

    assert(compare_tuples(kappa.get_axis(), axis))
    assert(compare_tuples(kappa.get_fixed(), fixed))

    kappa = XGoniometerFactory.Kappa(50.0, 0.0, 0.0, 0.0, '-y', 'omega')

    assert(len(single.get_axis()) == 3)
    assert(len(single.get_fixed()) == 9)

    assert(compare_tuples(kappa.get_axis(), axis))
    assert(compare_tuples(kappa.get_fixed(), fixed))

    kappa = XGoniometerFactory.Kappa(50.0, 0.0, 0.0, 0.0, '-y', 'phi')

    assert(len(single.get_axis()) == 3)
    assert(len(single.get_fixed()) == 9)

    assert(compare_tuples(kappa.get_axis(), axis))
    assert(compare_tuples(kappa.get_fixed(), fixed))

    kappa = XGoniometerFactory.Kappa(50.0, 0.0, 30.0, 0.0, '-y', 'omega')

    assert(len(single.get_axis()) == 3)
    assert(len(single.get_fixed()) == 9)

    assert(compare_tuples(kappa.get_axis(), axis))
    assert(not compare_tuples(kappa.get_fixed(), fixed))

    cbf = XGoniometerFactory.imgCIF('phi_scan_001.cbf')

    print cbf

    kappa = XGoniometerFactory.Kappa(50.0, -10.0, 30.0, 0.0, '-y', 'phi')

    print kappa

    cbf = XGoniometerFactory.imgCIF('omega_scan.cbf')

    print cbf

    kappa = XGoniometerFactory.Kappa(50.0, -10.0, 30.0, 20.0, '-y', 'omega')

    print kappa


if __name__ == '__main__':

    TestXGoniometer()
