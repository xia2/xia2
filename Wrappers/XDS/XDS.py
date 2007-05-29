#!/usr/bin/env python
# XDS.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# This module is a generic wrapper for the basic components needed to make
# XDS run, including writing the generic header information. This will 
# include the writing of the information from the image header, for instance,
# and should support all image types defined in the Printheader dictionary.
# That is:
# 
# detector_class = {('adsc', 2304, 81):'adsc q4',
#                   ('adsc', 1502, 163):'adsc q4 2x2 binned',
#                   ('adsc', 4096, 51):'adsc q210',
#                   ('adsc', 2048, 102):'adsc q210 2x2 binned',
#                   ('adsc', 6144, 51):'adsc q315',
#                   ('adsc', 3072, 102):'adsc q315 2x2 binned',
#                   ('marccd', 4096, 73):'mar 300',
#                   ('marccd', 3072, 73):'mar 225',
#                   ('marccd', 2048, 79):'mar 165',
#                   ('mar', 2300, 150):'mar 345'}
#
# as of starting this wrapper, 11th December 2006. These detector types
# will map onto standard input records, including the directions of the
# different axes (beam, detector x, detector y) trusted regions of the
# detector (e.g. does the picture go to the corners) and so on.

import os
import sys
import exceptions

class XDSException(exceptions.Exception):
    def __init__(self, value):
        self.value = value
        return
    def __str__(self):
        return str(self.value)

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2_ROOT']) in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

def _xds_version(xds_output_list):
    '''Return the version of XDS which has been run.'''

    for line in xds_output_list:
        if 'XDS VERSION' in line:
            return line.split('XDS VERSION')[1].split(')')[0].strip()
        if 'XDS' in line and 'VERSION' in line:
            return line.split('(VERSION')[1].split(')')[0].strip()

    raise RuntimeError, 'XDS version not found'

def xds_check_version_supported(xds_output_list):
    '''Check that the XDS version is supported.'''

    xds_version = _xds_version(xds_output_list)

    supported_versions = ['June 2006', 'August 18, 2006', 'May 8, 2007']

    if not xds_version in supported_versions:
        raise RuntimeError, 'XDS version "%s" not supported' % xds_version

    return

def xds_error(xds_output_list):
    '''Check for errors in XDS output and raise an exception if one is
    found.'''
    
    for line in xds_output_list:
        if '!!!' in line and 'ERROR' in line:
            error = line.split('!!!')[2].strip()
            raise XDSException, error

    return

def header_to_xds(header, synchrotron = True):
    '''A function to take an input header dictionary from Printheader
    and generate a list of records to start XDS - see Doc/INP.txt.'''

    # --------- mapping tables -------------

    detector_to_detector = {
        'mar':'MAR345',
        'marccd':'CCDCHESS',
        'raxis':'RAXIS',
        'adsc':'ADSC'}

    detector_to_overload = {
        'mar':130000,
        'marccd':65000,
        'raxis':1000000,
        'adsc':65000}

    detector_to_x_axis = {
        'mar':'1.0 0.0 0.0',
        'marccd':'1.0 0.0 0.0',        
        'raxis':'1.0 0.0 0.0',
        'adsc':'1.0 0.0 0.0'}

    detector_to_y_axis = {
        'mar':'0.0 1.0 0.0',
        'marccd':'0.0 1.0 0.0',        
        'raxis':'0.0 -1.0 0.0',
        'adsc':'0.0 1.0 0.0'}

    detector_class_is_square = {
        'adsc q4':True,
        'adsc q4 2x2 binned':True,
        'adsc q210':True,
        'adsc q210 2x2 binned':True,
        'adsc q315':True,
        'adsc q315 2x2 binned':True,
        'mar 345':False,
        'mar 300':True,
        'mar 225':True,
        'mar 165':False,
        'raxis IV':True}

    detector_to_rotation_axis = {
        'mar':'1.0 0.0 0.0',
        'marccd':'1.0 0.0 0.0',        
        'raxis':'0.0 1.0 0.0',
        'adsc':'1.0 0.0 0.0'}

    # --------- end mapping tables ---------

    width, height = tuple(map(int, header['size']))
    qx, qy = tuple(header['pixel'])

    detector = header['detector']
    detector_class = header['detector_class']

    result = []

    result.append('DETECTOR=%s MINIMUM_VALID_PIXEL_VALUE=%d OVERLOAD=%d' % \
                  (detector_to_detector[detector], 0,
                   detector_to_overload[detector]))

    result.append('DIRECTION_OF_DETECTOR_X-AXIS=%s' % \
                  detector_to_x_axis[detector])

    result.append('DIRECTION_OF_DETECTOR_Y-AXIS=%s' % \
                  detector_to_y_axis[detector])

    if detector_class_is_square[detector_class]:
        result.append('TRUSTED_REGION=0.0 1.41')
    else:
        result.append('TRUSTED_REGION=0.0 0.99')

    result.append('NX=%d NY=%d QX=%6.4f QY=%6.4f' % \
                  (width, height, qx, qy))

    result.append('DETECTOR_DISTANCE=%7.3f' % header['distance'])
    result.append('OSCILLATION_RANGE=%4.2f' % (header['phi_end'] -
                                               header['phi_start']))
    result.append('X-RAY_WAVELENGTH=%8.6f' % header['wavelength'])
    result.append('ROTATION_AXIS= %s' % \
                  detector_to_rotation_axis[detector])

    result.append('INCIDENT_BEAM_DIRECTION=0.0 0.0 1.0')

    if synchrotron:
        result.append('FRACTION_OF_POLARIZATION=0.95')
        result.append('POLARIZATION_PLANE_NORMAL= 0.0 1.0 0.0')
    else:
        result.append('FRACTION_OF_POLARIZATION=0.5')
        result.append('POLARIZATION_PLANE_NORMAL= 0.0 1.0 0.0')

    # FIXME 11/DEC/06 this should depend on the wavelength
    result.append('AIR=0.001')

    return result

def beam_centre_mosflm_to_xds(x, y, header):
    '''Convert a beam centre for image with header information in
    header from mm x, y in the Mosflm cordinate frame to pixels
    x, y in the XDS frame.'''

    # first gather up some useful information from the header

    width, height = tuple(map(int, header['size']))
    qx, qy = tuple(header['pixel'])
    detector = header['detector']

    # convert input to pixels

    px = x / qx
    py = y / qy

    # next ensure that the beam centre is on the detector

    if px < 0 or px > width:
        raise RuntimeError, 'beam x coordinate outside detector'

    if py < 0 or py > width:
        raise RuntimeError, 'beam y coordinate outside detector'

    # next perform some detector specific transformation to put
    # the centre in the right place... from looking at the papers
    # by Kabsch and Rossmann it turns out that the coordinate
    # frames are the same in the case where the experimental geometry
    # is the same... you just have to swap x & y. I have checked this
    # and it is correct - the Mosflm frame has the x, y axes mirrored to
    # the traditional Cartesian frame.

    return py, px

def beam_centre_xds_to_mosflm(px, py, header):
    '''Convert back...'''

    # first gather up some useful information from the header

    width, height = tuple(map(int, header['size']))
    qx, qy = tuple(header['pixel'])
    detector = header['detector']

    # convert input to pixels

    x = px * qx
    y = py * qy

    return y, x

if __name__ == '__main__':
    from Wrappers.XIA.Printheader import Printheader

    ph = Printheader()

    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    ph.set_image(os.path.join(directory, '12287_1_E1_001.img'))
    for record in header_to_xds(ph.readheader()):
        print record
