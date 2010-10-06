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
    x_to_d = - px * ox, - py * oy, distance

    return ra, beam, x_to_d, (px, py), distance, (nx, ny)

def XDS2CBF(xparm_file):
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

    ra, beam, x_to_d, pixel, distance, nxny = parse_xparm(xparm_file)

    # make them vectors

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
    z = beam - (beam.dot(ra) * ra)
    z = z / math.sqrt(z.dot())
    y = z.cross(x)

    # now lets figure the rotations we want to rotate x to _x, etc.

    _x = matrix.col([1, 0, 0])
    _y = matrix.col([0, 1, 0])
    _z = matrix.col([0, 0, 1])

    # ok then - #1 rotate about x ^ (1, 0, 0) - if they are not identical

    if _x.dot(x):
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

    # so that would be the distance between the sample and the
    # detector plane in the direction of the direct beam. 

    n = _m * matrix.col([0, 0, 1])
    n = n / math.sqrt(n.dot())
    D = _m * x_to_d
    d = n.dot(D)

    # calculate beam unit vector in cbf coordinate frame
    b = _m * beam
    b = b / math.sqrt(b.dot())

    # this will be the exact position where the beam strikes the
    # detector face - in the CBF coordinate frame
    B = b * (d / (b.dot(n)))

    # print '%10.4f %10.4f %10.4f' % B.elems

    # which I now need to convert to coordinates on the detector face!

    o = B - D

    # which is what w.r.t. the transformed x, y axes? - easy we know this
    # transformation - it's the inverse rotation!

    _o = _m.inverse() * o

    print 'Beam centre on the detector'
    print '%10.4f %10.4f %10.4f' % _o.elems

    # check the result is in the detector plane
    assert(math.fabs(_o.elems[2]) < 1.0e-7)

    # right that's enough for today - though would be nice to plot the
    # refined beam coordinates. OK that would be these then...

    # print _o.elems[0] / pixel[0], _o.elems[1] / pixel[1]

    _X = _m * _x
    _Y = _m * _y

    print 'Detector axes'
    print '%10.4f %10.4f %10.4f' % _X.elems
    print '%10.4f %10.4f %10.4f' % _Y.elems


if __name__ == '__main__':
    XDS2CBF(sys.argv[1])
