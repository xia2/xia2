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
        print Registry.find(f).__name__

if __name__ == '__main__':
    
    TestRegistry(sys.argv[1:])

