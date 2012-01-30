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

    x = xdata['x']
    y = xdata['y']

    x_to_d = - matrix.col(x) * px * ox + \
             - matrix.col(y) * py * oy + \
             distance * matrix.col(x).cross(matrix.col(y))

    return ra, beam, x_to_d.elems, (px, py), distance, (nx, ny), x, y

def get_abc_from_xparm(xparm_file):

    xdata = xds_read_xparm(xparm_file)

    return xdata['a'], xdata['b'], xdata['c']

def superdoofus(integrate_hkl, xparm_xds):

    ra, beam, x_to_d, pxpy, distance, nxny, x, y = parse_xparm(xparm_xds)
    a, b, c = get_abc_from_xparm(xparm_xds)

    O = matrix.col(x_to_d)
    S0 = matrix.col(beam)
    A = matrix.col(ra)

    UB = matrix.sqr(a + b + c).inverse()

    X = matrix.col(x)
    Y = matrix.col(y)
    N = X.cross(Y)

    distance = O.dot(N)

    start_angle = None
    angle_range = None
    start_frame = None

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

        R = A.axis_and_angle_as_r3_rotation_matrix(math.pi * phi / 180.0)

        q = R * UB * hkl

        p = S0 + q

        p_ = p * (1.0 / math.sqrt(p.dot()))
        P = p_ * (O.dot(N) / (p_.dot(N)))

        R = P - O

        i = R.dot(X)
        j = R.dot(Y)
        k = R.dot(N)

        print '%d %d %d %.3f %.3f %.3f %.3f %.3f %.3f' % \
              (hkl[0], hkl[1], hkl[2], i, j, k,
               xyz[0] * pxpy[0], xyz[1] * pxpy[1], phi)

        break



if __name__ == '__main__':
    superdoofus('INTEGRATE.HKL', 'GXPARM.XDS')
