#!/usr/bin/env python
# MatrixExpert.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 24th July 2007
#
# A small expert to handle orientation matrix calculations.
#

from __future__ import absolute_import, division, print_function

import math
import sys

from cctbx import crystal, sgtbx, uctbx
from scitbx import matrix
from xia2.Experts.LatticeExpert import l2s
from xia2.Experts.ReferenceFrame import mosflm_to_xia2
from xia2.Experts.SymmetryExpert import mat_to_symop, symop_to_mat
from xia2.Handlers.Streams import Debug
from xia2.lib.bits import auto_logfiler
from xia2.Wrappers.CCP4.Othercell import Othercell
from xia2.Wrappers.Phenix.LatticeSymmetry import LatticeSymmetry

# jiffies to convert matrix format (messy)


def mat2vec(mat):
    return [
        [mat[0], mat[3], mat[6]],
        [mat[1], mat[4], mat[7]],
        [mat[2], mat[5], mat[8]],
    ]


def vec2mat(vectors):
    return [
        vectors[0][0],
        vectors[1][0],
        vectors[2][0],
        vectors[0][1],
        vectors[1][1],
        vectors[2][1],
        vectors[0][2],
        vectors[1][2],
        vectors[2][2],
    ]


# generic mathematical calculations for 3-vectors

# FIXME cite PRE as the source here for these rotns - N.B. these should be
# replaced with CCTBX code.


def rot_x(theta):
    """Rotation matrix about Y of theta degrees."""

    dtor = 180.0 / (4.0 * math.atan(1.0))

    c = math.cos(theta / dtor)
    s = math.sin(theta / dtor)

    return [1.0, 0.0, 0.0, 0.0, c, s, 0.0, -s, c]


def rot_y(theta):
    """Rotation matrix about Y of theta degrees."""

    dtor = 180.0 / (4.0 * math.atan(1.0))

    c = math.cos(theta / dtor)
    s = math.sin(theta / dtor)

    return [c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c]


def rot_z(theta):
    """Rotation matrix about Y of theta degrees."""

    dtor = 180.0 / (4.0 * math.atan(1.0))

    c = math.cos(theta / dtor)
    s = math.sin(theta / dtor)

    return [c, -s, 0.0, s, c, 0.0, 0.0, 0.0, 1.0]


def b_matrix(a, b, c, alpha, beta, gamma):
    """Generate a B matric from a unit cell. Cite: Pflugrath in Methods
    Enzymology 276."""

    dtor = 180.0 / (4.0 * math.atan(1.0))

    ca = math.cos(alpha / dtor)
    sa = math.sin(alpha / dtor)
    cb = math.cos(beta / dtor)
    sb = math.sin(beta / dtor)
    cg = math.cos(gamma / dtor)
    sg = math.sin(gamma / dtor)

    # invert the cell parameters
    # CITE: International Tables C Section 1.1

    V = a * b * c * math.sqrt(1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg)

    a_ = b * c * sa / V
    b_ = a * c * sb / V
    c_ = a * b * sg / V

    # NOTE well - these angles are in radians

    alpha_ = math.acos((cb * cg - ca) / (sb * sg))
    beta_ = math.acos((ca * cg - cb) / (sa * sg))
    gamma_ = math.acos((ca * cb - cg) / (sa * sb))

    ca_ = math.cos(alpha_)
    sa_ = math.sin(alpha_)
    cb_ = math.cos(beta_)
    sb_ = math.sin(beta_)
    cg_ = math.cos(gamma_)
    sg_ = math.sin(gamma_)

    # NEXT construct the B matrix - CITE Pflugrath in Methods E 276

    return [
        a_,
        b_ * cg_,
        c_ * cb_,
        0.0,
        b_ * sg_,
        -c_ * sb_ * ca_,
        0.0,
        0.0,
        c_ * sb_ * sa_,
    ]


def dot(a, b):
    return sum([a[j] * b[j] for j in range(3)])


def cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def vecscl(vector, scale):
    return [vector[j] * scale for j in range(len(vector))]


def matscl(matrix, scale):
    return [matrix[j] * scale for j in range(len(matrix))]


def invert(matrix):
    vecs = mat2vec(matrix)
    scl = 1.0 / dot(vecs[0], cross(vecs[1], vecs[2]))

    return transpose(
        vec2mat(
            [
                vecscl(cross(vecs[1], vecs[2]), scl),
                vecscl(cross(vecs[2], vecs[0]), scl),
                vecscl(cross(vecs[0], vecs[1]), scl),
            ]
        )
    )


def transpose(matrix):
    return [
        matrix[0],
        matrix[3],
        matrix[6],
        matrix[1],
        matrix[4],
        matrix[7],
        matrix[2],
        matrix[5],
        matrix[8],
    ]


def det(matrix):
    vecs = mat2vec(matrix)
    return dot(vecs[0], cross(vecs[1], vecs[2]))


def matmul(b, a):
    avec = mat2vec(transpose(a))
    bvec = mat2vec(b)

    result = []
    for i in range(3):
        for j in range(3):
            result.append(dot(avec[i], bvec[j]))

    return result


def matvecmul(M, v):
    """Multiply a vector v by a matrix M -> return M v."""

    Mvec = mat2vec(transpose(M))
    result = []
    for i in range(3):
        result.append(dot(Mvec[i], v))
    return result


# things specific to mosflm matrix files...


def parse_matrix(matrix_text):
    """Parse a matrix returning cell, a and u matrix."""

    # this will need to be able to cope with the times
    # when the matrix includes columns merging together
    # (which sucks)

    # therefore parse this manually... or just add
    # a space before all '-'

    tokens = map(float, matrix_text.replace("-", " -").split()[:30])

    cell = tokens[21:27]
    a = tokens[0:9]
    u = tokens[12:21]

    return cell, a, u


def format_matrix(cell, a, u):
    matrix_format = (
        " %11.8f %11.8f %11.8f\n"
        + " %11.8f %11.8f %11.8f\n"
        + " %11.8f %11.8f %11.8f\n"
    )

    cell_format = " %11.4f %11.4f %11.4f %11.4f %11.4f %11.4f\n"

    misset = "       0.000       0.000       0.000\n"

    return (
        matrix_format % tuple(a)
        + misset
        + matrix_format % tuple(u)
        + cell_format % tuple(cell)
        + misset
    )


def transmogrify_matrix(lattice, matrix, target_lattice, wavelength, wd=None):
    """Transmogrify a matrix for lattice X into a matrix for lattice
    Y. This should work find for Mosflm... Will also return the new
    unit cell."""

    cell, a, u = parse_matrix(matrix)

    o = _Othercell()

    if wd:
        o.set_working_directory(wd)
        auto_logfiler(o)

    o.set_cell(cell)
    o.set_lattice(lattice)
    o.generate()

    new_cell = o.get_cell(target_lattice)
    op = symop_to_mat(o.get_reindex_op(target_lattice))

    # HACK! again - bug # 3193

    if "lattice_symmetry" in o.get_executable():
        op = transpose(op)

    # why is only one of the matrices inverted?!

    a = matmul(invert(op), a)
    u = matmul(op, u)

    # in here test that the given unit cell corresponds to the
    # one calculated from the A matrix.

    anew = matscl(a, 1.0 / wavelength)
    reala = transpose(invert(anew))
    _a, _b, _c = mat2vec(reala)

    la = math.sqrt(dot(_a, _a))
    lb = math.sqrt(dot(_b, _b))
    lc = math.sqrt(dot(_c, _c))

    if (
        math.fabs(la - new_cell[0]) / new_cell[0] > 0.01
        or math.fabs(lb - new_cell[1]) / new_cell[1] > 0.01
        or math.fabs(lc - new_cell[2]) / new_cell[2] > 0.01
    ):
        raise RuntimeError("cell check failed (wavelength != %f)" % wavelength)

    return format_matrix(new_cell, a, u)


def _Othercell():
    """A factory to produce either a wrapper for LaticeSymmetry or
    OtherCell depending on what is available."""

    try:
        return LatticeSymmetry()
    except Exception:
        return Othercell()


def get_real_space_primitive_matrix(lattice, matrix, wd=None):
    """Get the primitive real space vectors for the unit cell and
    lattice type. Note that the resulting matrix will need to be
    scaled by a factor equal to the wavelength in Angstroms."""

    # parse the orientation matrix

    cell, a, u = parse_matrix(matrix)

    # generate other possibilities

    o = _Othercell()

    if wd:
        o.set_working_directory(wd)
        auto_logfiler(o)

    o.set_cell(cell)
    o.set_lattice(lattice)
    o.generate()

    # transform the possibly centred cell to the primitive setting

    op = symop_to_mat(o.get_reindex_op("aP"))

    primitive_a = matmul(invert(op), a)

    # then convert to real space

    real_a = invert(primitive_a)

    return real_a[0:3], real_a[3:6], real_a[6:9]


def get_reciprocal_space_primitive_matrix(lattice, matrix, wd=None):
    """Get the primitive reciprocal space vectors for this matrix."""

    # parse the orientation matrix

    cell, a, u = parse_matrix(matrix)

    # generate other possibilities

    o = _Othercell()

    if wd:
        o.set_working_directory(wd)
        auto_logfiler(o)

    o.set_cell(cell)
    o.set_lattice(lattice)
    o.generate()

    # transform the possibly centred cell to the primitive setting

    op = symop_to_mat(o.get_reindex_op("aP"))

    primitive_a = matmul(invert(op), a)

    return mat2vec(primitive_a)


def find_primitive_axes(lattice, matrix, wd=None):
    """From an orientation matrix file, calculate the angles (phi) where
    the primitive cell axes a, b, c are in the plane of the detector
    (that is, orthogonal to the direct beam vector."""

    a, b, c = get_real_space_primitive_matrix(lattice, matrix, wd)

    dtor = 180.0 / (4.0 * math.atan(1.0))

    return (
        dtor * math.atan(-a[2] / a[0]),
        dtor * math.atan(-b[2] / b[0]),
        dtor * math.atan(-c[2] / c[0]),
    )


def find_primitive_reciprocal_axes(lattice, matrix, wd=None):
    """From an orientation matrix file, calculate the angles (phi) where
    the primitive reciprical space cell axes a, b, c are in the plane of
    the detector (that is, orthogonal to the direct beam vector."""

    a, b, c = get_reciprocal_space_primitive_matrix(lattice, matrix, wd)

    dtor = 180.0 / (4.0 * math.atan(1.0))

    return (
        dtor * math.atan(-a[2] / a[0]),
        dtor * math.atan(-b[2] / b[0]),
        dtor * math.atan(-c[2] / c[0]),
    )


def mosflm_a_matrix_to_real_space(wavelength, lattice, matrix):
    """Given a Mosflm A matrix and the associated spacegroup (think of this
    Bravais lattice (which will be converted to a spacegroup for the benefit
    of the CCTBX program lattice_symmetry) return the real space primative
    crystal lattice vectors in the xia2 reference frame. This reference frame
    corresponds to that defined for imgCIF."""

    # get the a, u, matrices and the unit cell
    cell, a, u = parse_matrix(matrix)

    # use iotbx.latice_symmetry to obtain the reindexing operator to
    # a primative triclinic lattice - this should not be specific to
    # using iotbx - othercell should be optionally supported too...
    ls = _Othercell()
    ls.set_cell(cell)
    ls.set_lattice(lattice)
    ls.generate()

    cell = ls.get_cell("aP")
    reindex = ls.get_reindex_op("aP")
    reindex_matrix = symop_to_mat(reindex)

    # grim hack warning! - this is because for some reason (probably to
    # do with LS getting the inverse operation) othercell is returning
    # the transpose of the operator or something... FIXME bug # 3193

    if "othercell" in ls.get_executable():
        reindex_matrix = transpose(reindex_matrix)

    # scale the a matrix
    a = matscl(a, 1.0 / wavelength)

    # convert to real space (invert) and apply this reindex operator to the a
    # matrix to get the primative real space triclinic cell axes
    real_a = matmul(reindex_matrix, transpose(invert(a)))

    # convert these to the xia2 reference frame
    a, b, c = mat2vec(real_a)

    ax = mosflm_to_xia2(a)
    bx = mosflm_to_xia2(b)
    cx = mosflm_to_xia2(c)

    # FIXME in here add check that the unit cell lengths are within 1% of
    # the correct value - if they are not, raise an exception as the wavelength
    # provided is probably wrong...

    la = math.sqrt(dot(ax, ax))
    lb = math.sqrt(dot(bx, bx))
    lc = math.sqrt(dot(cx, cx))

    # print out values - the cell may have been reindexed.

    Debug.write("Reindexed cell lengths: %.3f %.3f %.3f" % (cell[0], cell[1], cell[2]))
    Debug.write("Calculated from matrix: %.3f %.3f %.3f" % (la, lb, lc))

    if (
        math.fabs(la - cell[0]) / cell[0] > 0.01
        or math.fabs(lb - cell[1]) / cell[1] > 0.01
        or math.fabs(lc - cell[2]) / cell[2] > 0.01
    ):
        raise RuntimeError("cell check failed (wavelength != %f)" % wavelength)

    # return these vectors
    return ax, bx, cx


def reindex_sym_related(A, A_ref):
    """Calculate a reindexing matrix to move the indices referred to in
    A to the reference frame in A_ref: both are orientation matrices from
    Mosflm."""

    Amat = matrix.sqr(parse_matrix(A)[1])
    Amat_ref = matrix.sqr(parse_matrix(A_ref)[1])
    R = Amat_ref.inverse() * Amat
    Debug.write("%5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f" % R.elems)

    reindex = mat_to_symop(R)
    return reindex


def mosflm_matrix_centred_to_primitive(lattice, mosflm_a_matrix):
    """Convert a mosflm orientation matrix from a centred setting to a
    primitive one (i.e. same lattice, but without the centering operations,
    which therefore corresponds to a different basis)."""

    space_group_number = l2s(lattice)
    spacegroup = sgtbx.space_group_symbols(space_group_number).hall()
    sg = sgtbx.space_group(spacegroup)

    rtod = 180.0 / math.pi

    if not (sg.n_ltr() - 1):
        return mosflm_a_matrix

    cell, amat, umat = parse_matrix(mosflm_a_matrix)

    # first derive the wavelength

    mi = matrix.sqr(amat)
    m = mi.inverse()

    A = matrix.col(m.elems[0:3])
    B = matrix.col(m.elems[3:6])
    C = matrix.col(m.elems[6:9])

    a = math.sqrt(A.dot())
    b = math.sqrt(B.dot())
    c = math.sqrt(C.dot())

    # alpha = rtod * B.angle(C)
    # beta = rtod * C.angle(A)
    # gamma = rtod * A.angle(B)

    wavelength = ((cell[0] / a) + (cell[1] / b) + (cell[2] / c)) / 3.0

    # then use this to rescale the A matrix

    mi = matrix.sqr([a / wavelength for a in amat])

    sgp = sg.build_derived_group(True, False)
    symm = crystal.symmetry(unit_cell=cell, space_group=sgp)

    rdx = symm.change_of_basis_op_to_best_cell()
    # symm_new = symm.change_basis(rdx)

    # now apply this to the reciprocal-space orientation matrix mi

    cb_op = rdx
    R = cb_op.c_inv().r().as_rational().as_float().transpose().inverse()
    mi_r = mi * R

    # now re-derive the cell constants, just to be sure

    m_r = mi_r.inverse()
    Ar = matrix.col(m_r.elems[0:3])
    Br = matrix.col(m_r.elems[3:6])
    Cr = matrix.col(m_r.elems[6:9])

    a = math.sqrt(Ar.dot())
    b = math.sqrt(Br.dot())
    c = math.sqrt(Cr.dot())

    alpha = rtod * Br.angle(Cr)
    beta = rtod * Cr.angle(Ar)
    gamma = rtod * Ar.angle(Br)

    cell = uctbx.unit_cell((a, b, c, alpha, beta, gamma))

    amat = [wavelength * e for e in mi_r.elems]
    bmat = matrix.sqr(cell.fractionalization_matrix())
    umat = mi_r * bmat.inverse()

    new_matrix = [
        "%s\n" % r
        for r in format_matrix((a, b, c, alpha, beta, gamma), amat, umat.elems).split(
            "\n"
        )
    ]

    return new_matrix


if __name__ == "__main__":

    lattice = sys.argv[1]
    mosflm_a_matrix = open(sys.argv[2]).read()

    result = mosflm_matrix_centred_to_primitive(lattice, mosflm_a_matrix)

    for r in result:
        print(r[:-1])
