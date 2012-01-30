import os
import sys
import math
from scitbx import matrix

def densmap(xparm_file, i, j, k):
    '''Transform positions (21 x 21 x 21) in pixel i, j on image k (fast, slow)
    to reciprocal space, based on contents of XDS global postrefinement file.
    Nice illustration of the funny shapes that come from the transformation.'''

    values = map(float, open(xparm_file, 'r').read().split())

    istart = int(values[0])
    phistart = values[1]
    phiwidth = values[2]
    phiaxis = matrix.col(values[3:6])
    wavelength = values[6]
    beam = matrix.col(values[7:10]).normalize()

    nx, ny = int(values[10]), int(values[11])
    qx, qy = values[12], values[13]
    d = values[14]
    ox, oy = values[15], values[16]
    x = matrix.col(values[17:20]).normalize()
    y = matrix.col(values[20:23]).normalize()
    n = matrix.col(values[23:26]).normalize()

    sg = int(values[26])
    cell = values[27:33]
    a = matrix.col(values[33:36])
    b = matrix.col(values[36:39])
    c = matrix.col(values[39:42])

    UBi = matrix.sqr(values[33:42])

    origin = d * n - ox * qx * x - oy * qy * y
    fast = qx * x
    slow = qy * y

    s0 = (1 / wavelength) * beam

    d2r = math.pi / 180.0

    for _i in range(21):
        for _j in range(21):
            for _k in range(21):
                __i = i + 0.05 * _i
                __j = j + 0.05 * _j
                __k = k + 0.05 * _k

                r = origin + __i * fast + __j * slow
                s = (1 / wavelength) * r.normalize()
                R = phiaxis.axis_and_angle_as_r3_rotation_matrix(
                    d2r * (phistart + __k * phiwidth))
                q = R.inverse() * (s - s0)
                print '%f %f %f' % (__i, __j, __k), '%f %f %f' % q.elems, \
                      '%f %f %f' % (UBi * q).elems

def densmap2(xparm_file, image):

    values = map(float, open(xparm_file, 'r').read().split())

    istart = int(values[0])
    phistart = values[1]
    phiwidth = values[2]
    phiaxis = matrix.col(values[3:6])
    wavelength = values[6]
    beam = matrix.col(values[7:10]).normalize()

    nx, ny = int(values[10]), int(values[11])
    qx, qy = values[12], values[13]
    d = values[14]
    ox, oy = values[15], values[16]
    x = matrix.col(values[17:20]).normalize()
    y = matrix.col(values[20:23]).normalize()
    n = matrix.col(values[23:26]).normalize()

    sg = int(values[26])
    cell = values[27:33]
    a = matrix.col(values[33:36])
    b = matrix.col(values[36:39])
    c = matrix.col(values[39:42])

    UBi = matrix.sqr(values[33:42])

    origin = d * n - ox * qx * x - oy * qy * y
    fast = qx * x
    slow = qy * y

    s0 = (1 / wavelength) * beam

    d2r = math.pi / 180.0

    __k = image + 0.5
    Ri = phiaxis.axis_and_angle_as_r3_rotation_matrix(
        d2r * (phistart + __k * phiwidth)).inverse()

    for _i in range(0, ny + 1, 8):
        for _j in range(0, nx + 1, 8):
            __i = 0.5 + _i
            __j = 0.5 + _j

            r = origin + __i * fast + __j * slow
            s = (1 / wavelength) * r.normalize()
            q = Ri * (s - s0)
            print '%f %f %f' % (__i, __j, __k), '%f %f %f' % q.elems, \
                  '%f %f %f' % (UBi * q).elems

if __name__ == '__main__':

    image = int(sys.argv[1])

    densmap2('gxparm.xds', image)
