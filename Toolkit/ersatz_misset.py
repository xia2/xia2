import sys
import math
from scitbx import matrix
from scitbx.math.euler_angles import xyz_angles

def ersatz_misset(integrate_lp):
    a_s = []
    b_s = []
    c_s = []

    for record in open(integrate_lp):
        if 'COORDINATES OF UNIT CELL A-AXIS' in record:
            a = map(float, record.split()[-3:])
            a_s.append(matrix.col(a))
        elif 'COORDINATES OF UNIT CELL B-AXIS' in record:
            b = map(float, record.split()[-3:])
            b_s.append(matrix.col(b))
        elif 'COORDINATES OF UNIT CELL C-AXIS' in record:
            c = map(float, record.split()[-3:])
            c_s.append(matrix.col(c))

    assert(len(a_s) == len(b_s) == len(c_s))

    ub0 = matrix.sqr(a_s[0].elems + b_s[0].elems + c_s[0].elems).inverse()

    for j in range(len(a_s)):
        ub = matrix.sqr(a_s[j].elems + b_s[j].elems + c_s[j].elems).inverse()
        print '%7.3f %7.3f %7.3f' % tuple(xyz_angles(ub.inverse() * ub0))


if __name__ == '__main__':
    ersatz_misset(sys.argv[1])
                                  
