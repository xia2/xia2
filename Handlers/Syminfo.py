#!/usr/bin/env python
# Syminfo.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 13th June 2006
#
# A handler singleton for the information in the CCP4 symmetry library
# syminfo.lib.
#

from __future__ import absolute_import, division, print_function

import copy
import os
import re
import sys

from cctbx import sgtbx


class _Syminfo(object):
    """An object to retain symmetry information."""

    def __init__(self):
        """Initialise everything."""

        self._parse_symop()

        self._int_re = re.compile("^[0-9]*$")

    def _generate_lattice(self, lattice_type, shortname):
        """Generate a lattice name (e.g. tP) from TETRAGONAL and P422."""

        hash = {
            "TRICLINIC": "a",
            "MONOCLINIC": "m",
            "ORTHORHOMBIC": "o",
            "TETRAGONAL": "t",
            "TRIGONAL": "h",
            "HEXAGONAL": "h",
            "CUBIC": "c",
        }

        lattice = "%s%s" % (hash[lattice_type.upper()], shortname[0].upper())

        if lattice[1] != "H":
            return lattice
        else:
            return "%sR" % lattice[0]

    def _parse_symop(self):
        """Parse the CCP4 symop library."""

        self._symop = {}
        self._spacegroup_name_to_lattice = {}
        self._spacegroup_short_to_long = {}
        self._spacegroup_long_to_short = {}
        self._spacegroup_name_to_number = {}
        self._spacegroup_name_to_pointgroup = {}

        current = 0

        for line in open(os.path.join(os.environ["CLIBD"], "symop.lib")).readlines():
            if line[0] != " ":
                list = line.split()
                index = int(list[0])
                shortname = list[3]

                lattice_type = list[5].lower()
                longname = line.split("'")[1]

                lattice = self._generate_lattice(lattice_type, shortname)

                pointgroup = ""
                for token in longname.split():
                    if len(longname.split()) <= 2:
                        pointgroup += token[0]
                    elif token[0] != "1":
                        pointgroup += token[0]

                self._symop[index] = {
                    "index": index,
                    "lattice_type": lattice_type,
                    "lattice": lattice,
                    "name": shortname,
                    "longname": longname,
                    "pointgroup": pointgroup,
                    "symops": 0,
                    "operations": [],
                }

                if shortname not in self._spacegroup_name_to_lattice:
                    self._spacegroup_name_to_lattice[shortname] = lattice

                if shortname not in self._spacegroup_name_to_number:
                    self._spacegroup_name_to_number[shortname] = index

                if longname not in self._spacegroup_long_to_short:
                    self._spacegroup_long_to_short[longname] = shortname

                if shortname not in self._spacegroup_short_to_long:
                    self._spacegroup_short_to_long[shortname] = longname

                if shortname not in self._spacegroup_name_to_pointgroup:
                    self._spacegroup_name_to_pointgroup[shortname] = pointgroup

                current = index

            else:

                self._symop[current]["symops"] += 1
                self._symop[current]["operations"].append(line.strip())

    def get_syminfo(self, spacegroup_number):
        """Return the syminfo for spacegroup number."""
        return copy.deepcopy(self._symop[spacegroup_number])

    def get_pointgroup(self, name):
        """Get the pointgroup for this spacegroup, e.g. P422 for P43212."""
        space_group = sgtbx.space_group_info(name).group()
        point_group = (
            space_group.build_derived_patterson_group().build_derived_acentric_group()
        )
        return point_group.type().lookup_symbol().replace(" ", "")

    def get_lattice(self, name):
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

        from cctbx.sgtbx.bravais_types import bravais_lattice

        if isinstance(name, int):
            lattice = bravais_lattice(number=name)
        elif self._int_re.match(name):
            name = int(name)
            lattice = bravais_lattice(number=name)
        else:
            lattice = bravais_lattice(symbol=str(name))

        return str(lattice)

    def get_spacegroup_numbers(self):
        """Get a list of all spacegroup numbers."""

        numbers = sorted(self._symop.keys())

        return numbers

    def spacegroup_number_to_name(self, spacegroup_number):
        """Return the name of this spacegroup."""
        return sgtbx.space_group_info(spacegroup_number).type().lookup_symbol()

    def spacegroup_name_to_number(self, spacegroup):
        """Return the number corresponding to this spacegroup."""

        # check have not had number passed in

        try:
            number = int(spacegroup)
            return number
        except Exception:
            pass

        return sgtbx.space_group_info(str(spacegroup)).type().number()

    def get_num_symops(self, spacegroup_number):
        """Get the number of symmetry operations that spacegroup
        number has."""
        return len(sgtbx.space_group_info(number=spacegroup_number).group())

    def get_symops(self, spacegroup):
        """Get the operations for spacegroup number N."""

        try:
            number = int(spacegroup)
        except ValueError:
            number = self.spacegroup_name_to_number(spacegroup)

        return self._symop[number]["operations"]

    def get_subgroups(self, spacegroup):
        """Get the list of spacegroups which are included entirely in this
        spacegroup."""

        try:
            number = int(spacegroup)
        except ValueError:
            number = self.spacegroup_name_to_number(spacegroup)

        symops = self._symop[number]["operations"]

        subgroups = []

        for j in range(230):
            sub = True
            for s in self._symop[j + 1]["operations"]:
                if not s in symops:
                    sub = False
            if sub:
                subgroups.append(self.spacegroup_number_to_name(j + 1))

        return subgroups


Syminfo = _Syminfo()

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(Syminfo.get_pointgroup(arg))
        print(Syminfo.get_lattice(arg))
