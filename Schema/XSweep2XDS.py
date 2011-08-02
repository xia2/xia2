#!/usr/bin/env python
# XSweep2XDS.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# Subclass to print out XSweep2 instance as XDS.

import os
import sys

from XSweep2 import XSweep2

class XSweep2XDS:
    '''A class to export contents of an XSweep2 as XDS.INP.'''

    def __init__(self, xsweep2_instance):
        self._xsweep = xsweep2_instance

        return

    def XDS(self):

        print self._xsweep.get_xscan().get_format()

        print self._xsweep.get_xdetector()

if __name__ == '__main__':

    # run some tests

    from XSweep2 import XSweep2Factory

    class XProject:
        def __init__(self):
            pass
        def get_name(self):
            return 'fakeproject'

    class XCrystal:
        def __init__(self):
            pass
        def get_name(self):
            return 'fakecrystal'
        def get_anomalous(self):
            return False
        def get_project(self):
            return XProject()
        def get_lattice(self):
            return None

    class XWavelength:
        def __init__(self):
            pass
        def get_name(self):
            return 'fakewavelength'
        def get_wavelength(self):
            return math.pi / 4
        
    xs = XSweep2Factory.FromImages(
        'noddy', XWavelength(), sys.argv[1:])

    xsx = XSweep2XDS(xs)

    xsx.XDS()
        

        
    
