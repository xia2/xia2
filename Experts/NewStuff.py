#!/usr/bin/env python
# 
# Code to interpret XDS (G)XPARM file and produce the rotation axis and beam 
# vector in the imgCIF coordinate frame. From there, can transform to 
# Mosflm missetting angles.
# 

from scitbx import matrix
import math
import sys

def parse_xparm(xparm_file):
    '''Read an xparm file, return the rotation axis and beam vector in the
    XDS coordinate frame.'''

    values = map(float, open(xparm_file, 'r').read().split())

    return tuple(values[3:6]), tuple(values[7:10])

def xds_to_cbf(xparm_file):
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

    ra, beam = parse_xparm(xparm_file)

    # make them vectors

    ra = matrix.col(ra)
    beam = matrix.col(beam)

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

    _m = _m_z * _m_x

    # now rotate the original things thus, to ensure that they are behaving
    # themselves.

    print '%10.7f %10.7f %10.7f' % (_m * x).elems
    print '%10.7f %10.7f %10.7f' % (_m * y).elems
    print '%10.7f %10.7f %10.7f' % (_m * z).elems

    # then see how things behave when we look at the rest of the environment

    print 'new laboratory frame axes (detector axes)'

    print '%10.7f %10.7f %10.7f' % (_m * matrix.col([1, 0, 0])).elems
    print '%10.7f %10.7f %10.7f' % (_m * matrix.col([0, 1, 0])).elems
    print '%10.7f %10.7f %10.7f' % (_m * matrix.col([0, 0, 1])).elems

    # and finally the new beam

    print 'New beam vector'

    print '%10.7f %10.7f %10.7f' % (_m * beam).elems

    # now need to consider the position of the detector etc. to derive the
    # new direct beam centre...
    
    m = matrix.sqr([x[0], x[1], x[2],
                    y[0], y[1], y[2],
                    z[0], z[1], z[2]])

    _beam = m * beam
    _nbeam = m.inverse() * (0, 0, 1)
    _ra = m.inverse() * (1, 0, 0)

    det_x = m * matrix.col((1, 0, 0))
    det_y = m * matrix.col((0, 1, 0))
    det_z = m * matrix.col((0, 0, 1))
    det_n = det_x.cross(det_y)



if __name__ == '__main__':
    xds_to_cbf(sys.argv[1])
