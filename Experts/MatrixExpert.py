# A small expert to handle orientation matrix calculations.

from __future__ import absolute_import, division, print_function

from builtins import range
import math

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
