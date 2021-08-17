# A library of things to help with simple symmetry operation stuff.
#
# FIXED 17/NOV/06 add a method in here to give a list of likely, and then
#                 less likely, spacegroups based on an input spacegroup.
#                 For instance, if the input spacegroup is P 41 21 2 then
#                 another likely spacegroup is P 43 21 2 and less likely
#                 spacegroups are all those in the same pointgroup with
#                 different screw axes - e.g. P 41 2 2 (thinking of an Ed
#                 Mitchell example.) This should also allow in the likely
#                 case for body centred spacegroups where the screw axes
#                 are hidden, for example I 2 2 2/I 21 21 21 and I 2 3/I 21 3.
#                 This is now handled by Pointless in the "likely spacegroups"
#                 section.
#
# FIXME 06/DEC/06 need a mapping table from "old" spacegroup names to e.g. xHM
#                 for use with phenix.hyss.


import os


def lattice_to_spacegroup(lattice):
    """Convert a lattice e.g. tP into the minimal spacegroup number
    to represent this."""

    _lattice_to_spacegroup = {
        "aP": 1,
        "mP": 3,
        "mC": 5,
        "mI": 5,
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

    if lattice not in _lattice_to_spacegroup:
        raise RuntimeError('lattice "%s" unknown' % lattice)

    return _lattice_to_spacegroup[lattice]


def spacegroup_name_xHM_to_old(xHM):
    """Convert to an old name."""

    # generate mapping table

    mapping = {}
    current_old = ""
    current_xHM = ""

    old_names = set()

    syminfo = os.path.join(os.environ["CCP4"], "lib", "data", "syminfo.lib")
    with open(syminfo) as fh:
        for line in fh.readlines():
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

    # eliminated this entry ... 'oA': 38,

    lattices = [
        "aP",
        "mP",
        "mC",
        "oP",
        "oC",
        "oF",
        "oI",
        "tP",
        "tI",
        "hP",
        "hR",
        "cP",
        "cF",
        "cI",
    ]

    # FIXME this should = lattice!
    spacegroup_to_lattice = {
        lattice_to_spacegroup(lattice): lattice for lattice in lattices
    }
    # lattice_to_spacegroup(lattice)

    spacegroups = sorted(spacegroup_to_lattice)

    return [spacegroup_to_lattice[s] for s in spacegroups]


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

    # this has been calculated from the results of Ralf GK's sginfo and a
    # little fiddling...
    #
    # 19/feb/08 added mI record as pointless has started producing this -
    # why??? this is not a "real" spacegroup... may be able to switch this
    # off...
    #                             'I2/m': 'mI',

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
