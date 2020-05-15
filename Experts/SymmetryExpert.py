from cctbx import sgtbx
from scitbx import matrix

from xia2.Experts.LatticeExpert import lattice_to_spacegroup


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


def compose_symops(a, b):
    """Compose operation c, which is applying b then a."""

    return (sgtbx.change_of_basis_op(b) * sgtbx.change_of_basis_op(a)).as_hkl()


def symop_to_mat(symop):
    return matrix.sqr(sgtbx.change_of_basis_op(symop).c().as_double_array()[:9]).elems


def mat_to_symop(mat):
    return sgtbx.change_of_basis_op(
        sgtbx.rt_mx(matrix.sqr(mat), (0, 0, 0), r_den=12, t_den=144)
    ).as_hkl()


def lattice_to_spacegroup_number(lattice):
    """Return the spacegroup number corresponding to the lowest symmetry
    possible for a given Bravais lattice."""

    if lattice not in lattice_to_spacegroup:
        raise RuntimeError("lattice %s unknown" % lattice)

    return lattice_to_spacegroup[lattice]
