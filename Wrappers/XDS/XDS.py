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
# and should support all image types defined in the Diffdump dictionary.
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
import math
from scitbx import matrix

class XDSException(exceptions.Exception):
    def __init__(self, value):
        self.value = value
        return
    def __str__(self):
        return str(self.value)

class XDSIndexException(XDSException):
    def __init__(self, value):
        XDSException.__init__(self, value)
        return

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2_ROOT']) in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Handlers.Streams import Debug
from Handlers.Flags import Flags

from dxtbx.format.FormatPilatusHelpers import pilatus_6M_mask, \
     pilatus_2M_mask, pilatus_300K_mask

_running_xds_version_stamp = None

def _running_xds_version():
    global _running_xds_version_stamp
    if _running_xds_version_stamp is None:
        import subprocess
        xds_version_str = subprocess.check_output('xds')
        assert('VERSION' in xds_version_str)
        first_line = xds_version_str.split('\n')[1].strip()
        if not 'BUILT=' in xds_version_str:
            import datetime
            format_str = '***** XDS *****  (VERSION  %B %d, %Y)'
            date = datetime.datetime.strptime(first_line, format_str)
            
            _running_xds_version_stamp = (date.year * 10000 + date.month * 100 + 
                                          date.day)
        else:
            first_line = xds_version_str.split('\n')[1].strip()
            s = first_line.index('BUILT=') + 6
            _running_xds_version_stamp = int(first_line[s:s+8])

    return _running_xds_version_stamp
            
def _xds_version(xds_output_list):
    '''Return the version of XDS which has been run.'''

    for line in xds_output_list:
        if 'XDS VERSION' in line:
            return line.split('XDS VERSION')[1].split(')')[0].strip()
        if 'XDS' in line and 'VERSION' in line:
            return line.split('(VERSION')[1].split(')')[0].strip()

    raise RuntimeError, 'XDS version not found'

def xds_check_version_supported(xds_output_list):
    '''No longer check that the XDS version is supported.'''

    for record in xds_output_list:
        if 'Sorry, license expired' in record:
            raise RuntimeError, 'installed XDS expired on %s' % \
                  record.split()[-1]

    return

def xds_check_error(xds_output_list):
    '''Check for errors in XDS output and raise an exception if one is
    found.'''

    for line in xds_output_list:
        if '!!!' in line and 'ERROR' in line:
            error = '[XDS] %s' % line.split('!!!')[2].strip().lower()
            raise XDSException, error

    return

def rotate_cbf_to_xds_convention(fast, slow, axis = (1, 0, 0)):
    '''Rotate fast and slow directions about rotation axis to give XDS 
    conventional directions for fast and slow. This should be a rotation
    of 180 degrees about principle axis, defined to be 1,0,0.'''

    from scitbx import matrix

    R = matrix.col(axis).axis_and_angle_as_r3_rotation_matrix(180.0, deg = True)

    return (R * fast).elems, (R * slow).elems

def detector_axis_apply_two_theta_rotation(axis_string, header):
    '''Apply a rotation in degrees to this detector axis given as a string
    containing a list of three floating point values. Return as same.
    Header given as this definition may depend on the detector / instrument
    type.'''

    # is theta the wrong sign, as I record from diffdump? I think so.

    two_theta = -1 * header['two_theta'] * math.pi / 180.

    axis = map(float, axis_string.split())

    assert(len(axis) == 3)

    # assertion - this is a rotation about X (first coordinate) ergo will not
    # change this. Nope. Looks like it is a rotation about Y. Which makes
    # sense for a laboratory source...

    ct = math.cos(two_theta)
    st = math.sin(two_theta)

    new_axis = (axis[0] * ct + axis[2] * st,
                axis[1],
                - axis[0] * st + axis[2] * ct)

    return '%.3f %.3f %.3f' % new_axis

def header_to_xds(header, synchrotron = None, reversephi = False,
                  refined_beam_vector = None, refined_rotation_axis = None,
                  refined_distance = None):
    '''A function to take an input header dictionary from Diffdump
    and generate a list of records to start XDS - see Doc/INP.txt.'''

    # decide if we are at a synchrotron if we don't know already...
    # that is, the wavelength is around either the Copper or Chromium
    # K-alpha edge and this is an image plate.

    if synchrotron == None:

        if header['detector'] == 'marccd':
            synchrotron = True
        elif header['detector'] == 'adsc':
            synchrotron = True
        elif math.fabs(header['wavelength'] - 1.5418) < 0.01:
            Debug.write('Wavelength looks like Cu Ka -> lab source')
            synchrotron = False
        elif math.fabs(header['wavelength'] - 2.29) < 0.01:
            Debug.write('Wavelength looks like Cu Ka -> lab source')
            synchrotron = False
        else:
            synchrotron = True

    # --------- mapping tables -------------

    detector_to_detector = {
        'mar':'MAR345',
        'marccd':'CCDCHESS',
        'dectris':'PILATUS',
        'pilatus':'PILATUS',
        'raxis':'RAXIS',
        'saturn':'SATURN',
        'adsc':'ADSC'}

    detector_to_minimum_trusted = {
        'mar':1,
        'marccd':1,
        'dectris':0,
        'pilatus':0,
        'raxis':1,
        'saturn':1,
        'adsc':1}

    detector_to_overload = {
        'mar':130000,
        'marccd':65000,
        'dectris':1048500,
        'pilatus':1048500,
        'raxis':1000000,
        'saturn':1000000,
        'adsc':65000}

    detector_to_x_axis = {
        'mar':'1.0 0.0 0.0',
        'marccd':'1.0 0.0 0.0',
        'dectris':'1.0 0.0 0.0',
        'pilatus':'1.0 0.0 0.0',
        'raxis':'1.0 0.0 0.0',
        'saturn':'-1.0 0.0 0.0',
        'adsc':'1.0 0.0 0.0'}

    detector_to_y_axis = {
        'mar':'0.0 1.0 0.0',
        'marccd':'0.0 1.0 0.0',
        'dectris':'0.0 1.0 0.0',
        'pilatus':'0.0 1.0 0.0',
        'raxis':'0.0 -1.0 0.0',
        'saturn':'0.0 1.0 0.0',
        'adsc':'0.0 1.0 0.0'}

    detector_class_is_square = {
        'adsc q4':True,
        'adsc q4 2x2 binned':True,
        'adsc q210':True,
        'adsc q210 2x2 binned':True,
        'adsc q270':True,
        'adsc q270 2x2 binned':True,
        'adsc q315':True,
        'adsc q315 2x2 binned':True,
        'mar 345':False,
        'mar 180':False,
        'mar 240':False,
        'mar 300 ccd':True,
        'mar 325 ccd':True,
        'mar 225 ccd':True,
        'mar 165 ccd':False,
        'mar 135 ccd':False,
        'pilatus 6M':True,
        'pilatus 2M':True,
        'pilatus 300K':True,
        'rigaku saturn 92 2x2 binned':True,
        'rigaku saturn 944 2x2 binned':True,
        'rigaku saturn 724 2x2 binned':True,
        'rigaku saturn 92':True,
        'rigaku saturn 944':True,
        'rigaku saturn 724':True,
        'rigaku saturn a200':True,
        'raxis IV':True,
        'NOIR1':True}

    # FIXME not sure if this is correct...

    if reversephi:

        detector_to_rotation_axis = {
            'mar':'-1.0 0.0 0.0',
            'marccd':'-1.0 0.0 0.0',
            'dectris':'-1.0 0.0 0.0',
            'pilatus':'-1.0 0.0 0.0',
            'raxis':'0.0 -1.0 0.0',
            'saturn':'0.0 -1.0 0.0',
            'adsc':'-1.0 0.0 0.0'}

    else:

        detector_to_rotation_axis = {
            'mar':'1.0 0.0 0.0',
            'marccd':'1.0 0.0 0.0',
            'dectris':'1.0 0.0 0.0',
            'pilatus':'1.0 0.0 0.0',
            'raxis':'0.0 1.0 0.0',
            'saturn':'0.0 1.0 0.0',
            'adsc':'1.0 0.0 0.0'}

    detector_to_polarization_plane_normal = {
        'mar':'0.0 1.0 0.0',
        'marccd':'0.0 1.0 0.0',
        'dectris':'0.0 1.0 0.0',
        'pilatus':'0.0 1.0 0.0',
        'raxis':'1.0 0.0 0.0',
        'saturn':'0.0 1.0 0.0',
        'adsc':'0.0 1.0 0.0'}

    # --------- end mapping tables ---------

    width, height = tuple(map(int, header['size']))
    qx, qy = tuple(header['pixel'])
    detector = header['detector']

    if detector == 'rigaku':
        if 'raxis' in header['detector_class']:
            detector = 'raxis'
        else:
            detector = 'saturn'

    detector_class = header['detector_class']

    result = []

    # FIXME what follows below should perhaps be 0 for the really weak
    # pilatus data sets?

    result.append('DETECTOR=%s MINIMUM_VALID_PIXEL_VALUE=%d OVERLOAD=%d' % \
                  (detector_to_detector[detector],
                   detector_to_minimum_trusted[detector],
                   detector_to_overload[detector]))

    if not detector in ['raxis', 'saturn', 'dectris', 'pilatus', 'adsc'] and \
           math.fabs(header['two_theta']) > 1.0:
        raise RuntimeError, 'two theta offset not supported for %s' % detector

    if 'fast_direction' in header and 'slow_direction' in header:
        fast_direction, slow_direction = rotate_cbf_to_xds_convention(
            header['fast_direction'], header['slow_direction'])
        
        result.append('DIRECTION_OF_DETECTOR_X-AXIS=%f %f %f' % \
                      fast_direction)

        result.append('DIRECTION_OF_DETECTOR_Y-AXIS=%f %f %f' % \
                      slow_direction)

    elif detector in ['raxis', 'saturn']:

        result.append(
            'DIRECTION_OF_DETECTOR_X-AXIS=%s' % \
            detector_axis_apply_two_theta_rotation(
            detector_to_x_axis[detector], header))

        result.append(
            'DIRECTION_OF_DETECTOR_Y-AXIS=%s' % \
            detector_axis_apply_two_theta_rotation(
            detector_to_y_axis[detector], header))

    elif detector in ['dectris']:

        # a warning to the reader - the following code has been tested
        # only with full CBF Pilatus 300K images from Diamond Beamline I19.

        if math.fabs(header['two_theta']) > 1.0:
            assert('fast_direction' in header)
            assert('slow_direction' in header)

            fast_direction = tuple([-1 * d for d in header['fast_direction']])
            slow_direction = tuple([d for d in header['slow_direction']])

            result.append('DIRECTION_OF_DETECTOR_X-AXIS=%f %f %f' % \
                          fast_direction)

            result.append('DIRECTION_OF_DETECTOR_Y-AXIS=%f %f %f' % \
                          slow_direction)

        else:
            result.append('DIRECTION_OF_DETECTOR_X-AXIS=%s' % \
                          detector_to_x_axis[detector])

            result.append('DIRECTION_OF_DETECTOR_Y-AXIS=%s' % \
                          detector_to_y_axis[detector])

    else:

        result.append('DIRECTION_OF_DETECTOR_X-AXIS=%s' % \
                      detector_to_x_axis[detector])

        result.append('DIRECTION_OF_DETECTOR_Y-AXIS=%s' % \
                      detector_to_y_axis[detector])

    from Handlers.Phil import PhilIndex
    params = PhilIndex.get_python_object()
    if params.deprecated_xds.parameter.trusted_region:
        result.append('TRUSTED_REGION %.2f %.2f' % tuple(
            params.deprecated_xds.parameter.trusted_region))
    elif detector_class_is_square[detector_class]:
        result.append('TRUSTED_REGION=0.0 1.41')
    else:
        result.append('TRUSTED_REGION=0.0 0.99')

    if detector == 'dectris':
        # width, height need to be swapped...
        result.append('NX=%d NY=%d QX=%6.6f QY=%6.6f' % \
                      (height, width, qx, qy))
    else:
        result.append('NX=%d NY=%d QX=%6.6f QY=%6.6f' % \
                      (width, height, qx, qy))

    # RAXIS detectors have the distance written negative - why????
    # this is ONLY for XDS - SATURN are the same - probably left handed
    # goniometer rotation on rigaku X-ray sets.

    if refined_distance:
        result.append('DETECTOR_DISTANCE=%7.3f' % refined_distance)
    elif not detector in ['raxis', 'saturn']:
        result.append('DETECTOR_DISTANCE=%7.3f' % header['distance'])
    else:
        result.append('DETECTOR_DISTANCE=%7.3f' % (-1 * header['distance']))

    result.append('OSCILLATION_RANGE=%4.2f' % (header['phi_end'] -
                                               header['phi_start']))
    result.append('X-RAY_WAVELENGTH=%8.6f' % header['wavelength'])

    if refined_rotation_axis:
        result.append('ROTATION_AXIS= %f %f %f' % \
                      refined_rotation_axis)
    elif 'rotation_axis' in header:
        R = matrix.sqr((1, 0, 0, 0, -1, 0, 0, 0, -1))
        result.append('ROTATION_AXIS= %.3f %.3f %.3f' % \
                      (R * matrix.col(header['rotation_axis'])).elems)
    else:
        result.append('ROTATION_AXIS= %s' % \
                      detector_to_rotation_axis[detector])

    if refined_beam_vector:
        result.append('INCIDENT_BEAM_DIRECTION=%f %f %f' % \
                      refined_beam_vector)
    else:
        result.append('INCIDENT_BEAM_DIRECTION=0.0 0.0 1.0')

    if synchrotron:
        result.append('FRACTION_OF_POLARIZATION=0.99')
        result.append('POLARIZATION_PLANE_NORMAL=%s' % \
                      detector_to_polarization_plane_normal[detector])
    else:
        result.append('FRACTION_OF_POLARIZATION=0.5')
        result.append('POLARIZATION_PLANE_NORMAL=%s' % \
                      detector_to_polarization_plane_normal[detector])

    # FIXME 11/DEC/06 this should depend on the wavelength
    result.append('AIR=0.001')

    # dead regions of the detector for pilatus 6M, 2M, 300K etc.

    if 'pilatus' in header['detector_class']:
        result.append('SENSOR_THICKNESS=0.32')

    if header['detector_class'] == 'pilatus 6M':
        for limits in pilatus_6M_mask():
            result.append('UNTRUSTED_RECTANGLE= %d %d %d %d' % tuple(limits))

    elif header['detector_class'] == 'pilatus 2M':
        for limits in pilatus_2M_mask():
            result.append('UNTRUSTED_RECTANGLE= %d %d %d %d' % tuple(limits))

    elif header['detector_class'] == 'pilatus 300K':
        for limits in pilatus_300K_mask():
            result.append('UNTRUSTED_RECTANGLE= %d %d %d %d' % tuple(limits))

    if params.deprecated_xds.parameter.untrusted_ellipse:
        result.append('UNTRUSTED_ELLIPSE= %d %d %d %d' % tuple(
            params.deprecated_xds.parameter.untrusted_ellipse()))

    if params.deprecated_xds.parameter.untrusted_rectangle:
        result.append('UNTRUSTED_RECTANGLE= %d %d %d %d' % tuple(
            params.deprecated_xds.parameter.untrusted_rectangle()))

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

    # though if we have a two-theta offset we need to put the origin
    # in as where the detector normal meets the crystal.

    if 'detector_origin_mm' in header:
        return header['detector_origin_mm'][0] / qx, \
               header['detector_origin_mm'][1] / qy

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

def xds_read_xparm(xparm_file):
    '''Parse the new-style or old-style XPARM file.'''

    if 'XPARM' in open(xparm_file, 'r').readline():
        return xds_read_xparm_new_style(xparm_file)
    else:
        return xds_read_xparm_old_style(xparm_file)

def xds_read_xparm_old_style(xparm_file):
    '''Parse the XPARM file to a dictionary.'''

    data = map(float, open(xparm_file, 'r').read().split())

    assert(len(data) == 42)

    starting_frame = int(data[0])
    phi_start, phi_width = data[1:3]
    axis = data[3:6]

    wavelength = data[6]
    beam = data[7:10]

    nx, ny = map(int, data[10:12])
    px, py = data[12:14]

    distance = data[14]
    ox, oy = data[15:17]

    x, y = data[17:20], data[20:23]
    normal = data[23:26]

    spacegroup = int(data[26])
    cell = data[27:33]

    a, b, c = data[33:36], data[36:39], data[39:42]

    results = {
        'starting_frame':starting_frame,
        'phi_start':phi_start, 'phi_width':phi_width,
        'axis':axis, 'wavelength':wavelength, 'beam':beam,
        'nx':nx, 'ny':ny, 'px':px, 'py':py, 'distance':distance,
        'ox':ox, 'oy':oy, 'x':x, 'y':y, 'normal':normal,
        'spacegroup':spacegroup, 'cell':cell, 'a':a, 'b':b, 'c':c
        }

    return results

def xds_read_xparm_new_style(xparm_file):
    '''Parse the XPARM file to a dictionary.'''

    data = map(float, ' '.join(open(xparm_file, 'r').readlines()[1:]).split())

    starting_frame = int(data[0])
    phi_start, phi_width = data[1:3]
    axis = data[3:6]

    wavelength = data[6]
    beam = data[7:10]

    spacegroup = int(data[10])
    cell = data[11:17]
    a, b, c = data[17:20], data[20:23], data[23:26]
    assert(int(data[26]) == 1)
    nx, ny = map(int, data[27:29])
    px, py = data[29:31]
    ox, oy = data[31:33]
    distance = data[33]
    x, y = data[34:37], data[37:40]
    normal = data[40:43]

    results = {
        'starting_frame':starting_frame,
        'phi_start':phi_start, 'phi_width':phi_width,
        'axis':axis, 'wavelength':wavelength, 'beam':beam,
        'nx':nx, 'ny':ny, 'px':px, 'py':py, 'distance':distance,
        'ox':ox, 'oy':oy, 'x':x, 'y':y, 'normal':normal,
        'spacegroup':spacegroup, 'cell':cell, 'a':a, 'b':b, 'c':c
        }

    return results


if __name__ == '__main__':
    from Wrappers.XIA.Diffdump import Diffdump

    dd = Diffdump()

    if len(sys.argv) < 2:

        directory = os.path.join(os.environ['XIA2_ROOT'],
                                 'Data', 'Test', 'Images')

        dd.set_image(os.path.join(directory, '12287_1_E1_001.img'))

    else:
        dd.set_image(sys.argv[1])

    for record in header_to_xds(dd.readheader()):
        print record
