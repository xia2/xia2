#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.lib.SymmetryLib import lauegroup_to_lattice


def Othercell(DriverType=None):
    """Factory for Othercell wrapper classes, with the specified
    Driver type."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class OthercellWrapper(DriverInstance.__class__):
        """A wrapper for the program othercell - which will provide
        functionality for presenting other indexing possibilities..."""

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "othercell"))

            self._initial_cell = []
            self._initial_lattice_type = None

            # results storage

            self._lattices = []
            self._distortions = {}
            self._cells = {}
            self._reindex_ops = {}

        def set_cell(self, cell):
            self._initial_cell = cell

        def set_lattice(self, lattice):
            """Set the full lattice - not just the centering operator!."""

            self._initial_lattice_type = lattice[1].lower()

        def generate(self):
            if not self._initial_cell:
                raise RuntimeError("must set the cell")
            if not self._initial_lattice_type:
                raise RuntimeError("must set the lattice")

            self.start()

            self.input("%f %f %f %f %f %f" % tuple(self._initial_cell))
            self.input("%s" % self._initial_lattice_type)
            self.input("")

            self.close_wait()

            # parse the output of the program...

            for o in self.get_all_output():

                if not "[" in o:
                    continue
                if "Reindex op" in o:
                    continue
                if "Same cell" in o:
                    continue
                if "Other cell" in o:
                    continue
                if "within angular tolerance" in o:
                    continue

                lauegroup = o[:11].strip()
                if not lauegroup:
                    continue

                if lauegroup[0] == "[":
                    continue

                modded_lauegroup = ""
                for token in lauegroup.split():
                    if token == "1":
                        continue
                    modded_lauegroup += token

                try:
                    lattice = lauegroup_to_lattice(modded_lauegroup)
                except KeyError:
                    # there was some kind of mess made of the othercell
                    # output - this happens!
                    continue

                cell = tuple(map(float, o[11:45].split()))
                distortion = float(o.split()[-2])
                operator = o.split()[-1][1:-1]

                if not lattice in self._lattices:
                    self._lattices.append(lattice)
                    self._distortions[lattice] = distortion
                    self._cells[lattice] = cell
                    self._reindex_ops[lattice] = operator
                else:
                    if distortion > self._distortions[lattice]:
                        continue
                    self._distortions[lattice] = distortion
                    self._cells[lattice] = cell
                    self._reindex_ops[lattice] = operator

        def get_lattices(self):
            return self._lattices

        def get_cell(self, lattice):
            return self._cells[lattice]

        def get_reindex_op(self, lattice):
            return self._reindex_ops[lattice]

    return OthercellWrapper()
