import os
import math
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# xia2 stuff...

from Wrappers.XDS.XDS import xds_read_xparm
from Handlers.Streams import Debug
from Handlers.Flags import Flags
from lib.bits import nint

# cctbx stuff

from cctbx import sgtbx
from cctbx import crystal
from scitbx import matrix

# check for deprecation, add workaround (thanks to RWGK 21/APR/10)

if (hasattr(matrix.rec, "rotate_around_origin")):
    matrix.rec.rotate = matrix.rec.rotate_around_origin

# end workaround

def spot2q(xparm_file, spot_file):
    '''Read XPARM file from XDS IDXREF and transform all positions to q
    space.'''

    # FIXME in the code which follows below I will need to read the detector
    # axes, not assume that they are aligned along 1,0,0 and 0,1,0! This is
    # however in the xparm file.

    xparm_d = xds_read_xparm(xparm_file)

    A, B, C = xparm_d['a'], xparm_d['b'], xparm_d['c']
    cell = xparm_d['cell']
    space_group_number = xparm_d['spacegroup']
    spacegroup = sgtbx.space_group_symbols(space_group_number).hall()
    sg = sgtbx.space_group(spacegroup)

    wavelength = xparm_d['wavelength']
    distance = xparm_d['distance']
    beam = xparm_d['beam']

    nx = xparm_d['nx']
    ny = xparm_d['ny']
    px = xparm_d['px']
    py = xparm_d['py']
    ox = xparm_d['ox']
    oy = xparm_d['oy']

    normal = xparm_d['normal']

    phi_start = xparm_d['phi_start']
    phi_width = xparm_d['phi_width']
    start = xparm_d['starting_frame'] - 1
    axis = matrix.col(xparm_d['axis'])

    N = matrix.col(normal)
    D = distance * N
    S = matrix.col(beam)

    Sd = (wavelength * distance / (wavelength * S.dot(N))) * S
    d = math.sqrt(Sd.dot())

    off = Sd - D

    bx = ox + off.elems[0] / px
    by = oy + off.elems[1] / py

    dtor = 180.0 / math.pi

    m = matrix.sqr(A + B + C)
    mi = m.inverse()

    indices = []

    for record in open(spot_file, 'r').readlines():
        l = record.split()

        if not l:
            continue

        if len(l) != 7:
            raise RuntimeError, 'error reading spot index'

        X, Y, i = map(float, l[:3])
        h, k, l = map(int, l[-3:])

        # FIXME here the detector axes become important...

        phi = (i - start) * phi_width + phi_start
        X = px * (X - bx)
        Y = py * (Y - by)

        P = matrix.col([X, Y, 0]) + Sd

        scale = wavelength * math.sqrt(P.dot())

        x = P.elems[0] / scale
        y = P.elems[1] / scale
        z = P.elems[2] / scale

        Sp = matrix.col([x, y, z]) - S

        # now index the reflection

        q = Sp.rotate(axis, - 1 * phi / dtor).elems

        print '%.5f %.5f %.5f' % q

    return

if __name__ == '__main__':

    source = os.getcwd()

    if len(sys.argv) > 1:
        source = sys.argv[1]

    xparm = os.path.join(source, 'XPARM.XDS')
    spot = os.path.join(source, 'SPOT.XDS')

    spot2q(xparm, spot)
