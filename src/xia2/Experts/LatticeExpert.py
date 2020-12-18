import math

lattice_to_spacegroup = {
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

spacegroup_to_lattice = {v: k for k, v in lattice_to_spacegroup.items()}


def ApplyLattice(lattice, cell):
    """Apply lattice constraints for a given lattice to a given input cell.
    This will return a new cell and also compute the distortion required
    to make the match. This assumes that the input cell is in the appropriate
    setting."""

    lattice_class = lattice[0]

    cell2 = ConstrainLattice(lattice_class, cell)

    distortion = ComputeBDistortion(cell, cell2)

    return cell2, distortion


def ComputeBDistortion(cell1, cell2):
    """Compute the distortion required to get from cell1 to cell2."""

    return sum(math.fabs(cell2[j] - cell1[j]) for j in range(6))


def ConstrainLattice(lattice_class, cell):
    """Constrain cell to fit lattice class x."""

    a, b, c, alpha, beta, gamma = cell

    if lattice_class == "a":
        return (a, b, c, alpha, beta, gamma)
    elif lattice_class == "m":
        return (a, b, c, 90.0, beta, 90.0)
    elif lattice_class == "o":
        return (a, b, c, 90.0, 90.0, 90.0)
    elif lattice_class == "t":
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 90.0)
    elif lattice_class == "h":
        e = (a + b) / 2.0
        return (e, e, c, 90.0, 90.0, 120.0)
    elif lattice_class == "c":
        e = (a + b + c) / 3.0
        return (e, e, e, 90.0, 90.0, 90.0)


def SortLattices(lattice_list):
    """Sort a list of lattices into decreasing order of symmetry. One entry
    in the lattice_list should consist of (lattice, (a, b, c, alpha, beta,
    gamma)). It is assumed in this that there will be at most one instance
    of each lattice type. This will also apply the symmetry constraints..."""

    lattices = []
    cells = {}

    for l in lattice_list:
        lattices.append(l[0])
        cells[l[0]] = l[1]

    spacegroups = sorted(lattice_to_spacegroup[l] for l in lattices)
    spacegroups.reverse()
    lattices = [spacegroup_to_lattice[s] for s in spacegroups]

    result = [(l, ConstrainLattice(l[0], cells[l])) for l in lattices]

    return result


def s2l(spacegroup):
    return spacegroup_to_lattice[spacegroup]
