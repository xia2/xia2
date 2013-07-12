import os
import sys
if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

def xparm_to_ub(xparm_file):
    from Wrappers.XDS.XDS import xds_read_xparm
    from scitbx import matrix
    xparm_data = xds_read_xparm(xparm_file)
    return matrix.sqr(xparm_data['a'] + xparm_data['b'] + xparm_data['c'])

def derive_axis_angle(xparm0, xparm1):
    if os.path.isdir(xparm0):
        xparm0 = os.path.join(xparm0, 'GXPARM.XDS')
    if os.path.isdir(xparm1):
        xparm1 = os.path.join(xparm1, 'GXPARM.XDS')
    from scitbx.math import r3_rotation_axis_and_angle_from_matrix
    import math
    ub0 = xparm_to_ub(xparm0)
    ub1 = xparm_to_ub(xparm1)
    R = ub1 * ub0.inverse()
    axis_angle = r3_rotation_axis_and_angle_from_matrix(R)
    axis = axis_angle.axis
    angle = axis_angle.angle() * 180.0 / math.pi
    return axis, angle, R

if __name__ == '__main__':
    axis, angle, R = derive_axis_angle(sys.argv[1], sys.argv[2])
    print 'Axis:'
    print '%6.3f %6.3f %6.3f' % axis
    print 'Angle:'
    print '%6.3f' % angle
    print 'R:'
    print '%6.3f %6.3f %6.3f\n%6.3f %6.3f %6.3f\n%6.3f %6.3f %6.3f' % R.elems
