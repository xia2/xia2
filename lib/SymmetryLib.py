import os

from xia2.Experts.LatticeExpert import lattice_to_spacegroup as _l2s


def lattice_to_spacegroup(lattice):

    if lattice not in _l2s:
        raise RuntimeError('lattice "%s" unknown' % lattice)

    return _l2s[lattice]


def spacegroup_name_xHM_to_old(xHM):
    """Convert to an old name."""

    # generate mapping table

    mapping = {}
    current_old = ""
    current_xHM = ""

    old_names = set()

    syminfo = os.path.join(os.environ["CCP4"], "lib", "data", "syminfo.lib")
    for line in open(syminfo, "r").readlines():
        if line[0] == "#":
            continue

        if "symbol old" in line:
            current_old = line.split("'")[1]

        if "symbol xHM" in line:
            current_xHM = line.split("'")[1]

        if "end_spacegroup" in line:
            mapping[current_xHM] = current_old
            old_names.add(current_old)

    xHM = xHM.upper()

    if xHM not in mapping:
        if xHM in old_names:
            return xHM
        raise RuntimeError("spacegroup %s unknown" % xHM)

    return mapping[xHM]


def clean_reindex_operator(symop):
    return str(symop).replace("[", "").replace("]", "")


def lattices_in_order():
    """Return a list of possible crystal lattices (e.g. tP) in order of
    increasing symmetry..."""

    return [l[1] for l in sorted({v: k for k, v in _l2s.items()}.items())]


def sort_lattices(lattices):
    ordered_lattices = []

    for l in lattices_in_order():
        if l in lattices:
            ordered_lattices.append(l)

    return ordered_lattices


def lauegroup_to_lattice(lauegroup):
    """Convert a Laue group representation (from pointless, e.g. I m m m)
    to something useful, like the implied crystal lattice (in this
    case, oI.)"""

    lauegroup_to_lattice = {
        "Ammm": "oA",
        "C2/m": "mC",
        "Cmmm": "oC",
        "Fm-3": "cF",
        "Fm-3m": "cF",
        "Fmmm": "oF",
        "H-3": "hR",
        "H-3m": "hR",
        "R-3:H": "hR",
        "R-3m:H": "hR",
        "I4/m": "tI",
        "I4/mmm": "tI",
        "Im-3": "cI",
        "Im-3m": "cI",
        "Immm": "oI",
        "P-1": "aP",
        "P-3": "hP",
        "P-3m": "hP",
        "P2/m": "mP",
        "P4/m": "tP",
        "P4/mmm": "tP",
        "P6/m": "hP",
        "P6/mmm": "hP",
        "Pm-3": "cP",
        "Pm-3m": "cP",
        "Pmmm": "oP",
    }

    updated_laue = ""

    for l in lauegroup.split():
        if not l == "1":
            updated_laue += l

    return lauegroup_to_lattice[updated_laue]
