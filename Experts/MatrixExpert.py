# A small expert to handle orientation matrix calculations.

from __future__ import absolute_import, division, print_function

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


def dot(a, b):
    return sum(a[j] * b[j] for j in range(3))


def cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def vecscl(vector, scale):
    return [v * scale for v in vector]


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
