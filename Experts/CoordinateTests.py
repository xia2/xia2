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
    XDS coordinate frame. Also the vector in this same coordinate frame to
    the start of the first pixel on the detector.'''

    values = map(float, open(xparm_file, 'r').read().split())

    ra = tuple(values[3:6])
    beam = tuple(values[7:10])

    # calculation of the true detector origin
    nx, ny = int(values[10]), int(values[11])
    px, py = values[12], values[13]
    ox, oy = values[15], values[16]

    # question - what is the refined distance defined as *precisely* -
    # the distance from the crystal to the detector origin?! - if it's
    # mrad off, it will essentially make *no* difference
    
    x_to_d = - px * ox, - py * oy, values[14]

    return ra, beam, x_to_d, (px, py), values[14], (nx, ny)

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

    ra, beam, x_to_d, pixel, distance, nxny = parse_xparm(xparm_file)

    # make them vectors

    ra = matrix.col(ra)
    beam = matrix.col(beam)
    x_to_d = matrix.col(x_to_d)
    nx, ny = nxny

    if False:

        # try to reproduce the beam centre
        
        distance = x_to_d[2]
        nbeam = math.sqrt(beam.dot())
        
        bx_to_d = beam * distance / beam.elems[2]
        offset = bx_to_d - matrix.col(x_to_d)
        
        # ok this reproduces the correct beam centre - why can't I get this
        # below?!

        print 'Refined beam centre in pixels'
        print offset.elems[0] / pixel[0], offset.elems[1] / pixel[1]

    if False:

        # assert: distance is in direction of beam: convert to distance to
        # origin
        
        d1 = distance * beam / math.sqrt(beam.dot())
        d2 = d1.elems[2]
        
        x_to_d = x_to_d[0], x_to_d[1], d2

        print 'New distance: %.3f' % d2

    wavelength = 1.0 / math.sqrt(beam.dot())

    print 'Wavelength: %.5f' % wavelength

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

    # now rotate the original things thus, to ensure that they are behaving
    # themselves.

    print '%10.7f %10.7f %10.7f' % (_m * x).elems
    print '%10.7f %10.7f %10.7f' % (_m * y).elems
    print '%10.7f %10.7f %10.7f' % (_m * z).elems

    # then see how things behave when we look at the rest of the environment

    print 'Following is in CBF reference frame'
    print 'New laboratory frame axes (detector axes, then normal)'

    print '%10.7f %10.7f %10.7f' % (_m * matrix.col([1, 0, 0])).elems
    print '%10.7f %10.7f %10.7f' % (_m * matrix.col([0, 1, 0])).elems
    print '%10.7f %10.7f %10.7f' % (_m * matrix.col([0, 0, 1])).elems

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

    print '%10.4f %10.4f %10.4f' % B.elems

    # which I now need to convert to coordinates on the detector face!

    o = B - D

    # which is what w.r.t. the transformed x, y axes? - easy we know this
    # transformation - it's the inverse rotation!

    _o = _m.inverse() * o

    print '%10.4f %10.4f %10.4f' % _o.elems

    # check the result is in the detector plane
    assert(math.fabs(_o.elems[2]) < 1.0e-7)

    # right that's enough for today - though would be nice to plot the
    # refined beam coordinates. OK that would be these then...

    print _o.elems[0] / pixel[0], _o.elems[1] / pixel[1]

    # now to calculate e.g. Mosflm corrections - TILT, TWIST, CCOMEGA
    # which are in 1/100 degrees for the first two, degrees for the
    # third.

    # to do this though we need to make the reference frame beam centric -
    # that is, rotate to ensure that the direct beam is along a cartesian
    # axis.

    # TILT - rotation about HORIZONTAL
    # TWIST - rotation about VERTICAL
    # CCOMEGA - rotation of detector about BEAM

    # first rotate about vertical axis

    _b = b
    _bt = matrix.col([0.0, 0.0, 1.0])
    _r = matrix.col([1.0, 0.0, 0.0])

    _v = _b.cross(_r)
    _a = _b.angle(_bt)

    cbf_to_mos = _v.axis_and_angle_as_r3_rotation_matrix(- _a)

    print '%10.7f %10.7f %10.7f' % _v.elems
    print 'angle: %f degrees' % (_a * 180.0 / math.pi)

    print '%10.7f %10.7f %10.7f' % (cbf_to_mos * _b).elems
    print '%10.7f %10.7f %10.7f' % (cbf_to_mos * _r).elems

    # now rotate everything else - in particular the detector origin, the
    # axes and the position on the detector where the direct beam hits
    # (which I assume is done in terms of pixel coordinates, converted
    # to mm...)

    # first attempt to get an accurate detector origin in the new (mosflm)
    # reference frame

    __o = cbf_to_mos * D

    print '%10.4f %10.4f %10.4f' % __o.elems

    __b = cbf_to_mos * B

    print '%10.4f %10.4f %10.4f' % __b.elems

    # get the new detector axes

    __x = cbf_to_mos * _m * matrix.col([1.0, 0.0, 0.0])
    __y = cbf_to_mos * _m * matrix.col([0.0, 1.0, 0.0])

    # now want to get the displacement from where the beam strikes the
    # detector to the origin w.r.t. these detector axes

    print '%10.7f %10.7f %10.7f' % __x.elems
    print '%10.7f %10.7f %10.7f' % __y.elems

    print 'Beam centre offset'

    __beam = cbf_to_mos * (B - D)

    print '%10.7f %10.7f %10.7f' % __beam.elems    

    mos_to_det = (cbf_to_mos * _m * matrix.sqr([1.0, 0.0, 0.0,
                                                0.0, 1.0, 0.0,
                                                0.0, 0.0, 1.0])).inverse()

    print 'On detector coordinate frame'
    print '%10.7f %10.7f %10.7f' % (mos_to_det * __beam).elems

    x, y, z = (mos_to_det * __beam).elems

    print 'Mosflm beam centre, which is swapped around w.r.t. XDS'
    print '%10.4f %10.4f' % (y, x)

    # now to try to calculate the TILT and TWIST from these... best way would
    # be to rotate the detector axes to put the vertical in the right plane
    # etc - since ccomega will be soaked up elsewhere. then can just use
    # vector.angle. This should be simply a rotation about (0, 0, 1).

    cx = matrix.col([1.0, 0.0, 0.0])
    cy = matrix.col([0.0, 1.0, 0.0])
    cz = matrix.col([0.0, 0.0, 1.0])

    fast = matrix.col([__x.elems[0], __x.elems[1], 0.0])
    fast = fast / math.sqrt(fast.dot())

    slow = matrix.col([__y.elems[0], __y.elems[1], 0.0])
    slow = slow / math.sqrt(slow.dot())

    a = 0.5 * (fast.angle(cx) + slow.angle(cy))

    mos_to_up = cz.axis_and_angle_as_r3_rotation_matrix( - a)

    print '%10.7f %10.7f %10.7f' % (mos_to_up * __x).elems
    print '%10.7f %10.7f %10.7f' % (mos_to_up * __y).elems

    tilt = 100.0 * 180.0 * (mos_to_up * __y).angle(cy) / math.pi
    twist = - 100.0 * 180.0 * (mos_to_up * __x).angle(cx) / math.pi

    print 'Tilt and twist ... I think:'
    print '%.1f %.1f' % (tilt, twist)

    # finally really would like to get a clue as to how the rotation axis is
    # misaligned and hence, how to calculate missetting angles as a function of
    # oscillation angle. N.B. will need to assume a datum point, so assert
    # misseting angles at phi 0.0 are 0.0, 0.0, ccomega.
        
if __name__ == '__main__':
    xds_to_cbf(sys.argv[1])
