from scitbx import matrix
from cctbx import sgtbx
from cctbx import crystal
from cctbx import uctbx
from cctbx.sgtbx import subgroups
from cctbx.sgtbx import lattice_symmetry
from cctbx.sgtbx import bravais_types
from cctbx.crystal.find_best_cell import find_best_cell
import sys
import math
import os

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

def nint(a):
    if a < 0:
        s = -1
        a = s * a
    else:
        s = 1

    i = int(a)
    if a - i > 0.5:
        i += 1

    return s * i

if __name__ == '__main__':
    results = read_xparm('XPARM.XDS')

    A = results['a']
    B = results['b']
    C = results['c']

    cell = results['cell']
    cell_original = results['cell']
    sg_original = results['spacegroup']
    spacegroup = sgtbx.space_group_symbols(results['spacegroup']).hall()

    sg = sgtbx.space_group(spacegroup)
    uc = uctbx.unit_cell(cell)
    sym = crystal.symmetry(unit_cell = uc, space_group = sg)
    
    # This is how we remove translation elements from the spacegroup
    # sgp = sg.build_derived_group(True, False)
    # print 'Uncentred spacegroup: %d' % sgp.type().number()
    # sg = sgp

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

    uc = uctbx.unit_cell((a, b, c, alpha, beta, gamma))

    bmat = matrix.sqr(uc.orthogonalization_matrix())
    
    sym = crystal.symmetry(unit_cell = uc,
                           space_group = sg)

    best = find_best_cell(sym, angular_tolerance = 3.0)
    best.symmetry().show_summary()
    print best.cb_op().c()

    minop = sym.change_of_basis_op_to_minimum_cell()
    min_cell = sym.change_basis(minop)

    # this determines the highest symmetry compatable with the unit
    # cell constants

    lg = lattice_symmetry.group(min_cell.unit_cell())
    lg_info = sgtbx.space_group_info(group = lg)

    # N.B. these may be in a random order, so will want to perhaps add in
    # some code which will do some sorting and find the best solution for
    # each bravais type.

    sgrps = subgroups.subgroups(lg_info).groups_parent_setting()

    # recipe warning! - ok, this is all wrong and I will need to
    # learn some more before I can get it right. Even so, it is a
    # useful place to start!

    for subg in sgrps:

        # this gets the space group information

        sprgrp = sgtbx.space_group_info(group = subg).type(
            ).expand_addl_generators_of_euclidean_normalizer(
            True, True).build_derived_acentric_group()

        # this sets up the symmetry (unit cell + spacegroup) object -
        # N.B. this will not barf if the cell constants are wrong, which
        # they are!

        subsym = crystal.symmetry(
            unit_cell = min_cell.unit_cell(),
            space_group = sprgrp,
            assert_is_compatible_unit_cell = False)

        # much munching to get the right change of basis operation -
        # first to the right spacegroup / lattice, then to the
        # best choice of cell dimensions

        cb_op_min = subsym.space_group_info().type().cb_op()
        ref_subsym = subsym.change_basis(cb_op_min)
        cb_op_best = ref_subsym.change_of_basis_op_to_best_cell()
        best_subsym = ref_subsym.change_basis(cb_op_best)

        # print a summary of this spacegroup choice

        best_subsym.show_summary()

        # compose these change of basis operations and convert to a
        # matrix to allow application to the crystal orientation
        # matrices
        
        cb_op_all = cb_op_best * cb_op_min

        # surely there must be an easier way to get the transformation
        # than a matrix like this??
        
        M = cb_op_all.c_inv().r().as_rational().as_float(
            ).transpose().inverse()

        # now, transform it back to the original (minimal) setting to
        # see what effect this has had on the primitive cell constants

        equiv_cell = best_subsym.change_basis(
            best_subsym.change_of_basis_op_to_minimum_cell()).unit_cell()
        equiv_bmat = matrix.sqr(equiv_cell.orthogonalization_matrix())

        # reconstruct my original real-space A matrix from the vectors in
        # the XPARM file
        
        Am = matrix.sqr([A[0], A[1], A[2],
                         B[0], B[1], B[2],
                         C[0], C[1], C[2]])

        # transform it to get the reciprocal space A matrix = [a*, b*, c*]
        
        Amr = Am.inverse()

        # multiply this by the orthogonalization matrix from the real-space
        # vectors = reciprocal space orthogonalization matrix inverted
        # (messy but makes sense)

        U = Amr * bmat

        # now multiply this by the reciprocal space B matrix calculated
        # from the back-transformed symmetry-happy cell constants
        
        Anew = ((U * equiv_bmat.inverse()) * M).inverse()

        # now invert the matrix above again (i.e. the one which was transformed
        # to the correct setting) to get the transformed cell constants out
        # for comparison

        Amp = (Amr * M).inverse()

        Ap = matrix.col(Amp.elems[0:3])
        Bp = matrix.col(Amp.elems[3:6])
        Cp = matrix.col(Amp.elems[6:9])

        rtod = 180.0 / math.pi

        # these are the putative symmetry-happy cell vectors computed

        Apn = matrix.col(Anew.elems[0:3])
        Bpn = matrix.col(Anew.elems[3:6])
        Cpn = matrix.col(Anew.elems[6:9])

        # OK, so in here want to derive U B = A; impose lattice constraints
        # on B (i.e. use the correctly transformed cell constants) then
        # reconstruct a new A. Would be interesting to compute A'A-1 to see
        # how different they are... Since XDS will "listen" can also write
        # out the correct unit cell axis to reindex with, for the
        # higher symmetry.
        
        print 'A    %8.3f%8.3f%8.3f%8.3f%8.3f%8.3f' % \
              (math.sqrt(Ap.dot()), math.sqrt(Bp.dot()), math.sqrt(Cp.dot()),
               rtod * Bp.angle(Cp), rtod * Cp.angle(Ap), rtod * Ap.angle(Bp))
        print 'Anwe %8.3f%8.3f%8.3f%8.3f%8.3f%8.3f' % \
              (math.sqrt(Apn.dot()), math.sqrt(Bpn.dot()),
               math.sqrt(Cpn.dot()), rtod * Bpn.angle(Cpn),
               rtod * Cpn.angle(Apn), rtod * Apn.angle(Bpn))

    # Ok, so this is back to the original calculations...

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

    # first gather the average offset (i.e. the RMS) of INDEXED reflections

    sum = 0.0
    n = 0

    for record in open('SPOT.XDS', 'r').readlines():
        l = record.split()

        if not l:
            continue

        X, Y, i = map(float, l[:3])
        h, k, l = map(int, l[-3:])

        if h == 0 and k == 0 and l == 0:
            continue

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

        sh = math.fabs(hkl[0] - nint(hkl[0]))
        sk = math.fabs(hkl[1] - nint(hkl[1]))
        sl = math.fabs(hkl[2] - nint(hkl[2]))

        sum += (sh * sh + sk * sk + sl * sl)
        n += 1

    rmsd = math.sqrt(sum / n)

    # then look at which ones I should be able to index...

    sum2 = 0.0
    n2 = 0

    iabs = 0
        
    for record in open('SPOT.XDS', 'r').readlines():
        l = record.split()

        if not l:
            continue

        X, Y, i = map(float, l[:3])
        h, k, l = map(int, l[-3:])

        if h == 0 and k == 0 and l == 0:
            pass
        else:
            continue

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

        sh = math.fabs(hkl[0] - nint(hkl[0]))
        sk = math.fabs(hkl[1] - nint(hkl[1]))
        sl = math.fabs(hkl[2] - nint(hkl[2]))

        if math.sqrt(sh * sh + sk * sk + sl * sl) < 3.0 * rmsd:

            sum2 += (sh * sh + sk * sk + sl * sl)
            n2 += 1
            
            # print '%4d %4d %4d => %8.4f %8.4f %8.4f' % \
            # (h, k, l, hkl[0], hkl[1], hkl[2])

            ihkl = tuple(map(nint, hkl))

            if sg.is_sys_absent(ihkl):
                # print '%d %d %d %d %d %d' % \
                # (h, k, l, ihkl[0], ihkl[1], ihkl[2])
                iabs += 1

    print 'Over %d indexed reflections RMSD = %.3f' % (n, rmsd)
    print 'Over %d unindexed reflections RMSD = %.3f' % (n2,
                                                         math.sqrt(sum2 / n2))
    print '%d systematic absences' % iabs
