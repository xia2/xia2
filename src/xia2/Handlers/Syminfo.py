# A collection of functions relating to spacegroup symmetry information


import re

from cctbx import sgtbx
from cctbx.sgtbx.bravais_types import bravais_lattice

_int_re = re.compile("^[0-9]*$")


def get_pointgroup(name):
    """Get the pointgroup for this spacegroup, e.g. P422 for P43212."""
    space_group = sgtbx.space_group_info(name).group()
    point_group = (
        space_group.build_derived_patterson_group().build_derived_acentric_group()
    )
    return point_group.type().lookup_symbol().replace(" ", "")


def get_lattice(name):
    """Get the lattice for a named spacegroup."""

    # check that this isn't already a lattice name
    if name in [
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
    ]:
        return name

    if isinstance(name, int):
        lattice = bravais_lattice(number=name)
    elif _int_re.match(name):
        name = int(name)
        lattice = bravais_lattice(number=name)
    else:
        lattice = bravais_lattice(symbol=str(name))

    return str(lattice)


def spacegroup_number_to_name(spacegroup_number):
    """Return the name of this spacegroup."""
    return sgtbx.space_group_info(spacegroup_number).type().lookup_symbol()


def spacegroup_name_to_number(spacegroup):
    """Return the number corresponding to this spacegroup."""

    # check have not had number passed in

    try:
        number = int(spacegroup)
        return number
    except ValueError:
        pass

    return sgtbx.space_group_info(str(spacegroup)).type().number()


def get_num_symops(spacegroup_number):
    """Get the number of symmetry operations that spacegroup
    number has."""
    return len(sgtbx.space_group_info(number=spacegroup_number).group())


class _Syminfo:
    """Legacy method of accessing functions."""


Syminfo = _Syminfo()
Syminfo.get_pointgroup = get_pointgroup
Syminfo.get_lattice = get_lattice
Syminfo.spacegroup_number_to_name = spacegroup_number_to_name
Syminfo.spacegroup_name_to_number = spacegroup_name_to_number
Syminfo.get_num_symops = get_num_symops
