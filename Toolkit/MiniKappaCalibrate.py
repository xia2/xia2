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
    RS_ub = matrix.sqr(xparm_data['a'] + xparm_data['b'] + xparm_data['c'])
    return RS_ub.inverse()

def find_xparm(xparm_location):
    assert(os.path.exists(xparm_location))
    if os.path.split(xparm_location)[-1] == 'GXPARM.XDS':
        return xparm_location
    assert(os.path.isdir(xparm_location))
    if os.path.exists(os.path.join(xparm_location, 'GXPARM.XDS')):
        return os.path.join(xparm_location, 'GXPARM.XDS')

    raise RuntimeError, 'no GXPARM.XDS found in %s' % xparm_location
        
def derive_axis_angle(xparm0, xparm1):
    xparm0 = find_xparm(xparm0)
    xparm1 = find_xparm(xparm1)
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

    prefix = os.path.commonprefix(sys.argv[1:])

    for j in range(1, len(sys.argv) - 1):
        print '%s => %s' % (sys.argv[j].replace(prefix, ''),
                            sys.argv[j + 1].replace(prefix, ''))
        axis, angle, R = derive_axis_angle(sys.argv[j], sys.argv[j + 1])
        print 'Axis:'
        print '%6.3f %6.3f %6.3f' % axis
        print 'Angle:'
        print '%6.3f' % angle

