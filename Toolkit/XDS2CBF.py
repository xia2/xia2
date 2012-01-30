#!/usr/bin/env python
# XDS2CBF.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Code to read in a GXPARM file from XDS and write out the corresponding
# CBF reference frame all nicely refined.

from scitbx import matrix
import math
import sys
import os

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2_ROOT']) in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.XDS.XDS import xds_read_xparm

def parse_xparm(xparm_file):
    '''Read an xparm file, return the rotation axis and beam vector in the
    XDS coordinate frame. Also the vector in this same coordinate frame to
    the start of the first pixel on the detector.'''

    xdata = xds_read_xparm(xparm_file)

    ra = xdata['axis']
    beam = xdata['beam']
    distance = xdata['distance']
    px = xdata['px']
    py = xdata['py']
    ox = xdata['ox']
    oy = xdata['oy']
    nx = xdata['nx']
    ny = xdata['ny']
    x_to_d = - px * ox, - py * oy, - distance

    x = xdata['x']
    y = xdata['y']

    x_to_d = - matrix.col(x) * px * ox + \
             - matrix.col(y) * py * oy + \
             distance * matrix.col(x).cross(matrix.col(y))

    return ra, beam, x_to_d.elems, (px, py), distance, (nx, ny), x, y

def get_abc_from_xparm(xparm_file):

    xdata = xds_read_xparm(xparm_file)

    return xdata['a'], xdata['b'], xdata['c']

def XDS2CBF(xparm_file, integrate_hkl):
    '''Given an XDS XPARM file, return a matrix which will transform from
    XDS coordinates to CBF reference frame.'''

    # XDS coordinate frame: x = detector fast direction
    #                       y = detector slow direction
    #                       z = x ^ y is detector normal (n.b. TOWARDS
    #                                                     the source)
    # CBF coordinate frame: x = primary gonio axis
    #                       y = z ^ x
    #                       z = component of beam |'r to x
    #
    # well that's ok then...

    ra, beam, x_to_d, pixel, distance, nxny, dx, dy = parse_xparm(xparm_file)

    # make them vectors etc.

    ra = matrix.col(ra)
    beam = matrix.col(beam)
    x_to_d = matrix.col(x_to_d)
    nx, ny = nxny

    wavelength = 1.0 / math.sqrt(beam.dot())

    # then unit vectors
    ra = ra / math.sqrt(ra.dot())
    beam = beam / math.sqrt(beam.dot())

    # right now lets calculate a rotation which will overlap the two reference
    # frames.... first relabel so we know what we are trying to do

    x = ra
    z = -1 * (beam - (beam.dot(ra) * ra))
    z = z / math.sqrt(z.dot())
    y = z.cross(x)

    # now lets figure the rotations we want to rotate x to _x, etc.

    _x = matrix.col([1, 0, 0])
    _y = matrix.col([0, 1, 0])
    _z = matrix.col([0, 0, 1])

    # ok then - #1 rotate about x ^ (1, 0, 0) - if they are not identical

    if _x.angle(x):
        _ra_x = _x.cross(x)
        _a_x = _x.angle(x)
    else:
        _ra_x = _x
        _a_x = 0.0

    _m_x = _ra_x.axis_and_angle_as_r3_rotation_matrix(- _a_x)

    # then rotate z to _z by rotating about _x (which is now coincident
    # with x) N.B. z cannot be perpendicular to x

    _ra_z = _x
    _a_z = _z.angle(_m_x * z)

    _m_z = _ra_z.axis_and_angle_as_r3_rotation_matrix(- _a_z)

    # _m is matrix to rotate FROM xds coordinate frame TO cbf reference frame

    _m = _m_z * _m_x

    # verify that this is a rotation i.e. has determinant +1.

    assert(math.fabs(_m.determinant() - 1.0) < 1.0e-7)

    # and finally the new beam

    print 'New beam vector'

    print '%10.7f %10.7f %10.7f' % (_m * beam).elems

    print 'To detector origin i.e. start of the first pixel'

    print '%10.4f %10.4f %10.4f' % (_m * x_to_d).elems

    # now need to consider the position of the detector etc. to derive the
    # new direct beam centre...

    _X = _m * dx
    _Y = _m * dy
    _N = _X.cross(_Y)

    # so that would be the distance between the sample and the
    # detector plane in the direction of the direct beam.

    _beam = _m * beam

    # D vector to detector origin, B vector to intersection of beam with det

    D = _m * x_to_d
    d = _N.dot(D)

    print 'Distance is %f' % d

    B = _beam * (d / _beam.dot(_N))

    o = B - D

    beam_x = o.dot(_X)
    beam_y = o.dot(_Y)
    beam_n = o.dot(_N)

    print 'Beam centre on the detector'
    print '%10.4f %10.4f %10.4f' % (beam_x, beam_y, beam_n)

    # check the result is in the detector plane
    assert(math.fabs(beam_n) < 1.0e-7)

    print 'Detector axes'
    print '%10.4f %10.4f %10.4f' % _X.elems
    print '%10.4f %10.4f %10.4f' % _Y.elems

    a, b, c = get_abc_from_xparm(xparm_file)

    _a = _m * a
    _b = _m * b
    _c = _m * c

    UB = matrix.sqr(_a.elems + _b.elems + _c.elems).inverse()

    print 'UB matrix:'
    print '%10.7f %10.7f %10.7f' % UB.elems[0:3]
    print '%10.7f %10.7f %10.7f' % UB.elems[3:6]
    print '%10.7f %10.7f %10.7f' % UB.elems[6:9]

    start_angle = None
    angle_range = None
    start_frame = None

    S0 = (1 / wavelength) * _beam
    O = _m * x_to_d

    for record in open(integrate_hkl):
        if '!' in record[:1]:
            if '!STARTING_ANGLE' in record:
                start_angle = float(record.split()[-1])
            elif '!STARTING_FRAME' in record:
                start_frame = float(record.split()[-1])
            elif '!OSCILLATION_RANGE' in record:
                angle_range = float(record.split()[-1])
            continue

        hkl = tuple(map(int, record.split()[:3]))
        xyz = tuple(map(float, record.split()[5:8]))

        phi = (xyz[2] - start_frame) * angle_range + start_angle

        R = _x.axis_and_angle_as_r3_rotation_matrix(math.pi * phi / 180.0)

        q = R * UB * hkl

        p = S0 + q

        p_ = p * (1.0 / math.sqrt(p.dot()))
        P = p_ * (O.dot(_N) / (p_.dot(_N)))

        R = P - O

        i = R.dot(_X)
        j = R.dot(_Y)
        k = R.dot(_N)

        if hkl == (-17, -10, 9):

            print '%d %d %d %.3f %.3f %.3f %.3f %.3f %.3f' % \
                  (hkl[0], hkl[1], hkl[2], i, j, k,
                   xyz[0] * pixel[0], xyz[1] * pixel[1], phi)

if __name__ == '__main__':
    XDS2CBF(sys.argv[1], sys.argv[2])
