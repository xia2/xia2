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
import math
from scitbx import matrix

from XSweep2 import XSweep2
from XDetectorHelpersTypes import XDetectorHelpersTypes

def xds_detector_name(xia2_name):
    '''Translate from a xia2 name from the detector library to an XDS detector
    name.'''

    if 'pilatus' in xia2_name:
        return 'PILATUS'
    if 'rayonix' in xia2_name:
        return 'CCDCHESS'
    if 'adsc' in xia2_name:
        return 'ADSC'
    if 'saturn' in xia2_name:
        return 'SATURN'

    raise RuntimeError, 'detector %s unknown' % xia2_name

class XSweep2XDS:
    '''A class to export contents of an XSweep2 as XDS.INP.'''

    def __init__(self, xsweep2_instance):
        self._xsweep = xsweep2_instance

        return

    def XDS(self):

        sensor = self._xsweep.get_xdetector().get_sensor()
        fast, slow = map(int, self._xsweep.get_xdetector().get_image_size())
        f, s = self._xsweep.get_xdetector().get_pixel_size()
        df = int(1000 * f)
        ds = int(1000 * s)

        # FIXME probably need to rotate by pi about the X axis

        R = matrix.col((1.0, 0.0, 0.0)).axis_and_angle_as_r3_rotation_matrix(
            180.0, deg = True)

        detector = xds_detector_name(
            XDetectorHelpersTypes.get(sensor, fast, slow, df, ds))
        trusted = self._xsweep.get_xdetector().get_trusted_range()

        print 'DETECTOR=%s MINIMUM_VALID_PIXEL_VALUE=%d OVERLOAD=%d' % \
              (detector, trusted[0] + 1, trusted[1])

        print 'DIRECTION_OF_DETECTOR_X-AXIS= %.3f %.3f %.3f' % \
              (R * self._xsweep.get_xdetector().get_fast_c()).elems

        print 'DIRECTION_OF_DETECTOR_Y-AXIS= %.3f %.3f %.3f' % \
              (R * self._xsweep.get_xdetector().get_slow_c()).elems

        print 'NX=%d NY=%d QX=%.4f QY=%.4f' % (fast, slow, f, s)

        F = R * self._xsweep.get_xdetector().get_fast_c()
        S = R * self._xsweep.get_xdetector().get_slow_c()
        N = F.cross(S)

        origin = R * self._xsweep.get_xdetector().get_origin_c()
        beam = R * self._xsweep.get_xbeam().get_direction_c() / \
               math.sqrt(self._xsweep.get_xbeam().get_direction_c().dot())
        centre = -(origin - origin.dot(N) * N)
        x = centre.dot(F)
        y = centre.dot(S)

        print 'DETECTOR_DISTANCE= %.3f' % origin.dot(N)
        print 'ORGX= %.1f ORGY= %.1f' % (x / f, y / s)
        print 'ROTATION_AXIS= %.3f %.3f %.3f' % \
              self._xsweep.get_xgoniometer().get_axis()
        print 'STARTING_ANGLE= %.3f' % \
              self._xsweep.get_xscan().get_oscillation()[0]
        print 'OSCILLATION_RANGE= %.3f' % \
              self._xsweep.get_xscan().get_oscillation()[1]
        print 'X-RAY_WAVELENGTH= %.5f' % \
              self._xsweep.get_xbeam().get_wavelength()
        print 'INCIDENT_BEAM_DIRECTION= %.3f %.3f %.3f' % \
              (- beam).elems
        print 'FRACTION_OF_POLARIZATION= %.3f' % \
              self._xsweep.get_xbeam().get_polarization_fraction()
        print 'POLARIZATION_PLANE_NORMAL= %.3f %.3f %.3f' % \
              self._xsweep.get_xbeam().get_polarization_plane()
        print 'NAME_TEMPLATE_OF_DATA_FRAMES= %s' % os.path.join(
            self._xsweep.get_xscan().get_directory(),             
            self._xsweep.get_xscan().get_template().replace('#', '?'))
        print 'TRUSTED_REGION= 0.0 1.41'
        for f0, f1, s0, s1 in self._xsweep.get_xdetector().get_mask():
            print 'UNTRUSTED_RECTANGLE= %d %d %d %d' % \
                  (f0 - 1, f1 + 1, s0 - 1, s1 + 1)

        start_end = self._xsweep.get_xscan().get_image_range()

        if start_end[0] == 0:
            start_end = (1, start_end[1])

        print 'DATA_RANGE= %d %d' % start_end
        print 'JOB=XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT'
        
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
        

        
    
