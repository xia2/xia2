#!/usr/bin/env python
# 
# Code to interpret XDS XPARM file and produce the rotation axis and beam 
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

    ra, beam = parse_xparm(xparm_file)

    ra = matrix.col(ra)
    beam = matrix.col(beam)

    x = ra

    z = beam - (beam.dot(ra) * ra)
    z = -1 * z / math.sqrt(z.dot())

    y = z.cross(x)

    m = matrix.sqr([x[0], x[1], x[2],
                    y[0], y[1], y[2],
                    z[0], z[1], z[2]])

    print m.inverse() * (0, 0, - 1)
    print beam / math.sqrt(beam.dot())

    print m.inverse() * (1, 0, 0)
    print ra

if __name__ == '__main__':
    xds_to_cbf(sys.argv[1])
