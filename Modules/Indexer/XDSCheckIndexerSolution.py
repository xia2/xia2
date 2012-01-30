#!/usr/bin/env cctbx.python
# XDSCheckIndexerSolution.py
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 11th May 2009
#
# Code to check the XDS solution from IDXREF for being pseudo-centred (i.e.
# comes out as centered when it should not be)
#

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

def s2l(spacegroup):
    lattice_to_spacegroup = {'aP':1, 'mP':3, 'mC':5,
                             'oP':16, 'oC':20, 'oF':22,
                             'oI':23, 'tP':75, 'tI':79,
                             'hP':143, 'hR':146, 'cP':195,
                             'cF':196, 'cI':197}

    spacegroup_to_lattice = { }
    for k in lattice_to_spacegroup.keys():
        spacegroup_to_lattice[lattice_to_spacegroup[k]] = k
    return spacegroup_to_lattice[spacegroup]

def xds_check_indexer_solution(xparm_file,
                               spot_file):
    '''Read XPARM file from XDS IDXREF (assumes that this is in the putative
    correct symmetry, not P1! and test centring operations if present. Note
    that a future version will boost to the putative correct symmetry (or
    an estimate of it) and try this if it is centred. Returns tuple
    (space_group_number, cell).'''

    # parse the XPARM file to a dictionary

    xparm_d = xds_read_xparm(xparm_file)

    A, B, C = xparm_d['a'], xparm_d['b'], xparm_d['c']
    cell = xparm_d['cell']
    space_group_number = xparm_d['spacegroup']
    spacegroup = sgtbx.space_group_symbols(space_group_number).hall()
    sg = sgtbx.space_group(spacegroup)

    # now ask if it is centred - if not, just return the input solution
    # without testing...

    if not is_centred(space_group_number) and False:
        return s2l(space_group_number), tuple(cell)

    # right, now need to read through the SPOT.XDS file and index the
    # reflections with the centred basis. Then I need to remove the lattice
    # translation operations and reindex, comparing the results.

    # first get the information I'll need to transform x, y, i to
    # reciprocal space

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

    # begin to transform these to something more usable (i.e. detector
    # offsets in place of beam vectors &c.)

    N = matrix.col(normal)
    D = distance * N
    S = matrix.col(beam)

    Sd = (wavelength * distance / (wavelength * S.dot(N))) * S
    d = math.sqrt(Sd.dot())

    off = Sd - D

    # FIXME should verify that the offset is confined to the detector
    # plane - i.e. off.normal = 0

    bx = ox + off.elems[0] / px
    by = oy + off.elems[1] / py

    dtor = 180.0 / math.pi

    # then transform the matrix to a helpful form (i.e. the reciprocal
    # space orientation matrix (a*, b*, c*)

    m = matrix.sqr(A + B + C)
    mi = m.inverse()

    # now iterate through the spot file

    present = 0
    absent = 0
    total = 0

    # 20110119 removing references to this half-lattice test as I am not
    # sure I have any test cases where this is used. Perhaps will need to
    # reinstate this at some point in the future. N.B. this used to refer
    # to the harrison clock, removing as a part of the decrufting mandated
    # in trac #1284.

    for record in open(spot_file, 'r').readlines():
        l = record.split()

        if not l:
            continue

        if len(l) != 7:
            raise RuntimeError, 'error reading spot index'

        X, Y, i = map(float, l[:3])
        h, k, l = map(int, l[-3:])

        total += 1

        # transform coordinates to something physical - i.e. degrees and mm.

        phi = (i - start) * phi_width + phi_start
        X = px * (X - bx)
        Y = py * (Y - by)

        # then convert detector position to reciprocal space position -
        # first add the crystal to detector beam vector, then scale, then
        # subtract the beam vector again in reciprocal space...

        P = matrix.col([X, Y, 0]) + Sd

        scale = wavelength * math.sqrt(P.dot())

        x = P.elems[0] / scale
        y = P.elems[1] / scale
        z = P.elems[2] / scale

        Sp = matrix.col([x, y, z]) - S

        # now index the reflection

        hkl = m * Sp.rotate(axis, - 1 * phi / dtor).elems

        ihkl = nint(hkl[0]), nint(hkl[1]), nint(hkl[2])

        # check if we are within 0.1 lattice spacings of the closest
        # lattice point - a for a random point this will be about 0.8% of
        # the time...

        dhkl = [math.fabs(hkl[j] - ihkl[j]) for j in range(3)]

        # is this reflection close to an integral index?

        if dhkl[0] < 0.1 and dhkl[1] < 0.1 and dhkl[2] < 0.1:

            # is it absent?

            if sg.is_sys_absent(ihkl):
                absent += 1
            else:
                present += 1

            continue

    # now, if the number of absences is substantial, need to consider
    # transforming this to a primitive basis

    Debug.write('Absent: %d  vs.  Present: %d Total: %d' % \
                (absent, present, total))

    # now see if this is compatible with a centred lattice or suggests
    # a primitive basis is correct

    sd = math.sqrt(absent)

    if (absent - 3 * sd) / total < 0.008:
        # everything is peachy

        return s2l(space_group_number), tuple(cell)

    # ok if we are here things are not peachy, so need to calculate the
    # spacegroup number without the translation operators

    sg_new = sg.build_derived_group(True, False)
    space_group_number_primitive = sg_new.type().number()

    # also determine the best setting for the new cell ...

    symm = crystal.symmetry(unit_cell = cell,
                            space_group = sg_new)

    rdx = symm.change_of_basis_op_to_best_cell()
    symm_new = symm.change_basis(rdx)
    cell_new = symm_new.unit_cell().parameters()

    return s2l(space_group_number_primitive), tuple(cell_new)

def is_centred(space_group_number):
    '''Test if space group # corresponds to a centred space group.'''

    sg_hall = sgtbx.space_group_symbols(space_group_number).hall()
    sg = sgtbx.space_group(sg_hall)

    if (sg.n_ltr() - 1):
        return True

    return False

def xds_test_indexer_solution(xparm_file,
                              spot_file):
    '''Read XPARM file from XDS IDXREF and investigate how the indexing
    looks...'''

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

        hkl = m * Sp.rotate(axis, - 1 * phi / dtor).elems

        indices.append(hkl)

    h_size = 20

    histogram_i = { }
    for j in range(-h_size, h_size + 1):
        histogram_i[j] = 0

    histogram_j = { }
    for j in range(-h_size, h_size + 1):
        histogram_j[j] = 0

    histogram_k = { }
    for j in range(-h_size, h_size + 1):
        histogram_k[j] = 0

    for hkl in indices:
        ihkl = nint(hkl[0]), nint(hkl[1]), nint(hkl[2])
        offset = [nint(2 * h_size * (hkl[j] - ihkl[j])) for j in range(3)]
        histogram_i[offset[0]] += 1
        histogram_j[offset[1]] += 1
        histogram_k[offset[2]] += 1

    for j in range(-h_size, h_size + 1):
        print '%5d %5d %5d %5d' % \
              (j, histogram_i[j], histogram_j[j], histogram_k[j])

    return

if __name__ == '__main__':

    source = os.getcwd()

    if len(sys.argv) > 1:
        source = sys.argv[1]

    xparm = os.path.join(source, 'XPARM.XDS')
    spot = os.path.join(source, 'SPOT.XDS')

    xds_test_indexer_solution(xparm, spot)
