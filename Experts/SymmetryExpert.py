# A small expert to handle symmetry calculations.

from __future__ import absolute_import, division, print_function

from cctbx import sgtbx
from scitbx import matrix


def _multiply_symmetry_matrix(a, b):
    """compute a * b, for e.g. h_ = a * b * h, e.g. apply b before a."""

    return (matrix.sqr(a) * matrix.sqr(b)).elems


def r_to_rt(r):
    """Convert R matrix to RT, assuming T=0."""

    result = []

    for i in range(3):
        for j in range(3):
            result.append(r[i * 3 + j])
        result.append(0)

    return result


def rt_to_r(rt):
    """Convert RT matrix to R, removing T."""

    result = []
    for i in range(3):
        for j in range(3):
            result.append(rt[4 * i + j])

    return result


def compose_matrices_r(mat_a, mat_b):
    """Compose symmetry matrix applying b then a."""

    mat_c = _multiply_symmetry_matrix(mat_a, mat_b)

    return mat_c


def compose_symops(a, b):
    """Compose operation c, which is applying b then a."""

    return (sgtbx.change_of_basis_op(b) * sgtbx.change_of_basis_op(a)).as_hkl()

    # return mat_to_symop(
    # _multiply_symmetry_matrix(symop_to_mat(a), symop_to_mat(b))).strip()


def symop_to_mat(symop):
    # symop = symop.replace('h', 'x').replace('k', 'y').replace('l', 'z')
    return matrix.sqr(sgtbx.change_of_basis_op(symop).c().as_double_array()[:9]).elems


def mat_to_symop(mat):
    return sgtbx.change_of_basis_op(
        sgtbx.rt_mx(matrix.sqr(mat), (0, 0, 0), r_den=12, t_den=144)
    ).as_hkl()


def lattice_to_spacegroup_number(lattice):
    """Return the spacegroup number corresponding to the lowest symmetry
    possible for a given Bravais lattice."""

    _lattice_to_spacegroup_number = {
        "aP": 1,
        "mP": 3,
        "mC": 5,
        "oP": 16,
        "oC": 20,
        "oF": 22,
        "oI": 23,
        "tP": 75,
        "tI": 79,
        "hP": 143,
        "hR": 146,
        "cP": 195,
        "cF": 196,
        "cI": 197,
    }

    if lattice not in _lattice_to_spacegroup_number:
        raise RuntimeError("lattice %s unknown" % lattice)

    return _lattice_to_spacegroup_number[lattice]
