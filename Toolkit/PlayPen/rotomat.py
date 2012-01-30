import os
import sys
import math
import shutil
from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_from_matrix
from cctbx import sgtbx

def parse_xds_xparm(xparm_file):
    values = map(float, open(xparm_file).read().split())

    assert(len(values) == 42)

    starting_frame = int(values[0])
    phi_start, phi_width = values[1:3]
    axis = values[3:6]

    wavelength = values[6]
    beam = values[7:10]

    nx, ny = map(int, values[10:12])
    px, py = values[12:14]

    distance = values[14]
    ox, oy = values[15:17]

    x, y = values[17:20], values[20:23]
    normal = values[23:26]

    spacegroup = int(values[26])
    cell = values[27:33]

    a, b, c = values[33:36], values[36:39], values[39:42]

    return a, b, c

def op_to_mat(op):
    return matrix.sqr(sgtbx.change_of_basis_op(op).c().as_double_array()[:9])

def determine_rotation_to_dtrek(xparm_file):
    values = map(float, open(xparm_file).read().split())

    assert(len(values) == 42)

    axis = values[3:6]
    beam = values[7:10]
    x, y = values[17:20], values[20:23]

    B = - matrix.col(beam).normalize()
    A = matrix.col(axis).normalize()
    X = matrix.col(x).normalize()
    Y = matrix.col(y).normalize()

    _X = matrix.col([1, 0, 0])
    _Y = matrix.col([0, 1, 0])
    _Z = matrix.col([0, 0, 1])

    if _X.angle(A):
        _M_X = (_X.cross(A)).axis_and_angle_as_r3_rotation_matrix(
            - _X.angle(A))
    else:
        _M_X = matrix.sqr((1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))

    _M_Z = _X.axis_and_angle_as_r3_rotation_matrix(- _Z.angle(_M_X * B))

    _M = _M_Z * _M_X

    return _M

def compute_Q(xparm_target, xparm_move):

    _M = determine_rotation_to_dtrek(xparm_target)

    a_t, b_t, c_t = parse_xds_xparm(xparm_target)
    a_m, b_m, c_m = parse_xds_xparm(xparm_move)

    m_t = matrix.sqr(a_t + b_t + c_t)

    min_r = 180.0
    min_ax = None

    for op in ['X,Y,Z', '-X,-Y,Z', '-X,Y,-Z', 'X,-Y,-Z',
               'Z,X,Y', 'Z,-X,-Y', '-Z,-X,Y', '-Z,X,-Y',
               'Y,Z,X', '-Y,Z,-X', 'Y,-Z,-X', '-Y,-Z,X']:
        op_m = op_to_mat(op)
        m_m = op_m * matrix.sqr(a_m + b_m + c_m)
        q = m_t.inverse() * m_m
        if math.fabs(q.determinant() - 1) > 0.1:
            print 'rejected %s' % op
            continue
        q_r = r3_rotation_axis_and_angle_from_matrix(q.inverse())

        if math.fabs(q_r.angle(deg = True)) < min_r:
            if q_r.angle(deg = True) >= 0:
                min_ax = matrix.col(q_r.axis)
                min_r = q_r.angle(deg = True)
            else:
                min_ax = - matrix.col(q_r.axis)
                min_r = - q_r.angle(deg = True)

    return (_M * min_ax).elems, min_r

if __name__ == '__main__':

    axes = [(1.0, 0.0, 0.0)]
    angles = [0.0]
    names = ['omega', 'kappa', 'phi']

    for j in (2, 3), (1, 2):
        axis, angle = compute_Q(sys.argv[j[0]], sys.argv[j[1]])
        axes.append(axis)
        angles.append(angle)

    for j in range(3):
        print '%6s' % names[j], '%6.3f %6.3f %6.3f' % axes[j], \
              '%6.3f' % angles[j]
