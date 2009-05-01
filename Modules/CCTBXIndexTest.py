from scitbx import matrix
import sys
import math

# read in XPARM.XDS - get the real-space cell vectors, distance, rotation
# axis and so on...

def read_xparm(xparm_file):
    '''Parse the XPARM file to a dictionary.'''

    records = open(xparm_file, 'r').readlines()

    data = map(float, open(xparm_file, 'r').read().split())

    if not len(data) == 42:
        raise RuntimeError, 'error parsing %s' % xparm_file

    starting_frame = int(data[0])
    phi_start = data[1]
    phi_width = data[2]
    axis = data[3:6]

    wavelength = data[6]
    beam = data[7:10]

    nx = int(data[10])
    ny = int(data[11])
    px = data[12]
    py = data[13]

    distance = data[14]
    ox = data[15]
    oy = data[16]

    x = data[17:20]
    y = data[20:23]
    normal = data[23:26]

    spacegroup = int(data[26])
    cell = data[27:33]

    a = data[33:36]
    b = data[36:39]
    c = data[39:42]

    results = {
        'starting_frame':starting_frame,
        'phi_start':phi_start,
        'phi_width':phi_width,
        'axis':axis,
        'wavelength':wavelength,
        'beam':beam,
        'nx':nx,
        'ny':ny,
        'px':px,
        'py':py,
        'distance':distance,
        'ox':ox,
        'oy':oy,
        'x':x,
        'y':y,
        'normal':normal,
        'spacegroup':spacegroup,
        'cell':cell,
        'a':a,
        'b':b,
        'c':c
        }

    return results

def keep():
    
    print '%6d%12.6f%12.6f%12.6f%12.6f%12.6f' % (starting_frame, phi_start,
                                                 phi_width,
                                                 axis[0], axis[1], axis[2])
    print '%15.6f%15.6f%15.6f%15.6f' % (wavelength, beam[0], beam[1], beam[2])
    print '%10d%10d%10.5f%10.5f' % (nx, ny, px, py)
    print '%15.6f%15.6f%15.6f' % (distance, ox, oy)
    print '%15.6f%15.6f%15.6f' % tuple(x)
    print '%15.6f%15.6f%15.6f' % tuple(y)
    print '%15.6f%15.6f%15.6f' % tuple(normal)
    print '%10d%10.3f%10.3f%10.3f%10.3f%10.3f%10.3f' % \
          (spacegroup, cell[0], cell[1], cell[2], cell[3], cell[4], cell[5])
    print '%15.6f%15.6f%15.6f' % tuple(a)
    print '%15.6f%15.6f%15.6f' % tuple(b)
    print '%15.6f%15.6f%15.6f' % tuple(c)

if __name__ == '__main__':
    results = read_xparm('XPARM.XDS')

    A = results['a']
    B = results['b']
    C = results['c']

    cell = results['cell']
    wavelength = results['wavelength']
    distance = results['distance']
    beam = results['beam']

    nx = results['nx']
    ny = results['ny']
    px = results['px']
    py = results['py']
    ox = results['ox']
    oy = results['oy']

    normal = results['normal']

    m = matrix.sqr(A + B + C)

    mi = m.inverse()

    A = matrix.col(A)
    B = matrix.col(B)
    C = matrix.col(C)

    axis = matrix.col(results['axis'])

    a = math.sqrt(A.dot())
    b = math.sqrt(B.dot())
    c = math.sqrt(C.dot())

    dtor = 180.0 / math.pi

    alpha = dtor * B.angle(C)
    beta = dtor * C.angle(A)
    gamma = dtor * A.angle(B)

    print '%8.3f%8.3f%8.3f%8.3f%8.3f%8.3f' % tuple(cell)
    print '%8.3f%8.3f%8.3f%8.3f%8.3f%8.3f' % (a, b, c, alpha, beta, gamma)
    
    phi_start = results['phi_start']
    phi_width = results['phi_width']
    start = results['starting_frame'] - 1

    # compute where the direct beam strikes the detector - this gives the
    # primary origin for the calculation of the reciprocal space
    # vectors - at this stage need the offset in pixels not mm

    N = matrix.col(normal)
    D = distance * N
    S = matrix.col(beam)

    Sd = (wavelength * distance / (wavelength * S.dot(N))) * S
    d = math.sqrt(Sd.dot())

    off = Sd - D

    bx = ox + off.elems[0] / px
    by = oy + off.elems[1] / py

    for record in open('SPOT.XDS', 'r').readlines():
        l = record.split()

        if not l:
            continue

        X, Y, i = map(float, l[:3])
        h, k, l = map(int, l[-3:])

        phi = (i - start) * phi_width + phi_start

        X = px * (X - bx)
        Y = py * (Y - by)

        # first convert detector position to reciprocal space position

        P = matrix.col([X, Y, 0]) + Sd

        scale = wavelength * math.sqrt(P.dot())

        x = P.elems[0] / scale
        y = P.elems[1] / scale
        z = P.elems[2] / scale

        Sp = matrix.col([x, y, z]) - S

        hkl = m * Sp.rotate(axis, - 1 * phi / dtor).elems

        print '%4d %4d %4d => %8.4f %8.4f %8.4f' % \
              (h, k, l, hkl[0], hkl[1], hkl[2])


