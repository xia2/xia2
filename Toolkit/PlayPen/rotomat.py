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

def compute_Q(xparm_target, xparm_move):

    a_t, b_t, c_t = parse_xds_xparm(xparm_target)
    a_m, b_m, c_m = parse_xds_xparm(xparm_move)

    m_t = matrix.sqr(a_t + b_t + c_t)

    for op in ['X,Y,Z', '-X,-Y,Z', '-X,Y,-Z', 'X,-Y,-Z',
               'Z,X,Y', 'Z,-X,-Y', '-Z,-X,Y', '-Z,X,-Y',
               'Y,Z,X', '-Y,Z,-X', 'Y,-Z,-X', '-Y,-Z,X']:
        op_m = op_to_mat(op)
        m_m = op_m * matrix.sqr(a_m + b_m + c_m)
        q = m_t.inverse() * m_m
        if math.fabs(q.determinant() - 1) > 0.1:
            print 'rejected %s' % op
            continue
        q_r = r3_rotation_axis_and_angle_from_matrix(q)
        print '%8s' % op, '%6.3f %6.3f %6.3f' % q_r.axis, \
              '%6.2f' % q_r.angle(deg = True)

if __name__ == '__main__':
    compute_Q(sys.argv[1], sys.argv[2])
