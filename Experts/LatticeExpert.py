# An expert who knows all about lattices. This will handle the elimination
# of possible lattices as a result of:
#
# - indexing
# - failed cell refinement
# - pointless
# - &c.
#
# To give you what is left...
#

from __future__ import absolute_import, division, print_function

import math

# Hard coded "expertise" - this is encoded by hand, because it is
# easier that way... or is it better to properly encode the
# symmetry constraints and calculate the rest from this? Quite possibly.
#
# Hmm.. perhaps an option here is to interrogate the ccp4 symmetry
# library in the usual way, to make these decisions based on subgroups.
# Subgroups could be defined by symmetry operators - would that make
# sense? This is making use of a mapping between lattice and most-simple
# spacegroup for that lattice... need to check if this is valid & behaves
# as expected...

allowed_lattices = [
    "aP",
    "mP",
    "mC",
    "oP",
    "oC",
    "oI",
    "oF",
    "tP",
    "tI",
    "hR",
    "hP",
    "cP",
    "cI",
    "cF",
]

# How to do this:
#
# (1) read all spacegroups, symmetries from symop.lib
# (2) for each symmetry element, pass through symop2mat to get a
#     numberical representation
# (3) draw a tree of subgroups & supergroups
#
# Then see if this matches up what I would expect from the lattice
# symmetry constraints for the simplest lattices.
#
# Have to think about...
#
# (1) making sure that only immediate subgroups are calculated, to
#     give a proper tree structure
# (2) representing the final tree structure in a manner which is actually
#     useful
#
# Unsurprisingly this doesn't work, because the lattices have different
# settings, and these settings affect the symmetry operators. Ho hum!
# Probably easier to hard-code it based on the IUCR tables volume A..
# Which I will do - see ApplyLattice(lattice, cell) below.
#


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

    spacegroups = sorted(lattice_to_spacegroup[l] for l in lattices)
    spacegroups.reverse()
    lattices = [spacegroup_to_lattice[s] for s in spacegroups]

    result = [(l, ConstrainLattice(l[0], cells[l])) for l in lattices]

    return result


def s2l(spacegroup):
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

    return spacegroup_to_lattice[spacegroup]
