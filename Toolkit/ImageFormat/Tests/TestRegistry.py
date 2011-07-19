#!/usr/bin/env python
# Registry.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Code to give the registry a bit of a workout.

import os
import sys

assert('XIA2_ROOT' in os.environ)

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Toolkit.ImageFormat.Registry import Registry

def TestRegistry(files):
    '''Print the class which claims to work with each file.'''
    for f in files:
        format = Registry.find(f)

        print format.__name__

        if format.understand(f) >= 2:
            i = format(f)
            print i.get_xbeam()
            print i.get_xgoniometer()
            print i.get_xdetector()

if __name__ == '__main__':
    
    TestRegistry(sys.argv[1:])

