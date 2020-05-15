from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Syminfo import Syminfo
from xia2.lib.SymmetryLib import lauegroup_to_lattice


def LatticeSymmetry(DriverType=None):
    """A factory for the LatticeSymmetry wrappers."""

    DriverInstance = DriverFactory.Driver("simple")

    class LatticeSymmetryWrapper(DriverInstance.__class__):
        """A wrapper class for iotbx.lattice_symmetry."""

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("iotbx.lattice_symmetry")

            if "phaser-1.3" in self.get_executable():
                raise RuntimeError("unsupported version of lattice_symmetry")

            self._cell = None
            self._spacegroup = None

            # following on from the othercell wrapper...

            self._lattices = []
            self._distortions = {}
            self._cells = {}
            self._reindex_ops = {}
            self._reindex_ops_basis = {}

        def set_cell(self, cell):
            self._cell = cell

        def set_spacegroup(self, spacegroup):
            self._spacegroup = spacegroup

        def set_lattice(self, lattice):
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

            self._spacegroup = Syminfo.spacegroup_number_to_name(
                lattice_to_spacegroup[lattice]
            )

            # bug 22/JUL/08 latest lattice symmetry no longer recognises
            # the spacegroup H3...

            if self._spacegroup == "H3":
                self._spacegroup = "R3:H"

        def generate(self):
            if not self._cell:
                raise RuntimeError("no unit cell specified")

            if not self._spacegroup:
                raise RuntimeError("no spacegroup specified")

            self.add_command_line("--unit_cell=%f,%f,%f,%f,%f,%f" % tuple(self._cell))
            self.add_command_line("--space_group=%s" % self._spacegroup)

            self.start()
            self.close_wait()

            # now wade through all of the options and see which comes
            # out best for each lattice class... - as defined by the
            # minimum value of Maximal angular difference

            state = {}

            for o in self.get_all_output():
                if ":" in o:
                    count = o.find(":")
                    left = o[:count]
                    right = o[count + 1 :]
                    state[left.strip()] = right.strip()

                if "Maximal angular difference" in o:
                    # transform & digest results

                    distortion = float(state["Maximal angular difference"].split()[0])

                    # this appears to be getting the wrong cell - I want the
                    # one which corresponds to the correct lattice, yes?!
                    # cell = map(float, state[
                    # 'Symmetry-adapted cell'].replace(
                    # '(', ' ').replace(')', ' ').replace(',', ' ').split())

                    cell = list(
                        map(
                            float,
                            state["Unit cell"]
                            .replace("(", " ")
                            .replace(")", " ")
                            .replace(",", " ")
                            .split(),
                        )
                    )

                    lauegroup = ""

                    # FIXME for more recent versions of cctbx the conventional
                    # setting I 1 2/m 1 has appeared -> look at the
                    # 'Symmetry in minimum-lengths cell' instead (equivalent
                    # to changing lkey here to 'Conventional setting'
                    #
                    # No, can't do this because this now reports the Hall
                    # symmetry not the Laue group. Will have to cope with
                    # the I setting instead :o(

                    lkey = "Symmetry in minimum-lengths cell"

                    for token in state[lkey].split("(")[0].split():
                        if token == "1":
                            continue
                        lauegroup += token

                    # FIXME bug 3157 - there appears to be a bug in
                    # recent versions of cctbx (cf. above) which means
                    # a lauegroup of 'R-3m:R' is given -> correct this
                    # in the string. Also :h as well :o(

                    lauegroup = lauegroup.replace(":R", ":H")
                    lauegroup = lauegroup.replace(":h", ":H")
                    lattice = lauegroup_to_lattice(lauegroup)

                    reindex_basis = state["Change of basis"]
                    reindex = state["Inverse"]

                    if lattice not in self._lattices:
                        self._lattices.append(lattice)
                        self._distortions[lattice] = distortion
                        self._cells[lattice] = cell
                        self._reindex_ops[lattice] = reindex
                        self._reindex_ops_basis[lattice] = reindex_basis
                    elif distortion < self._distortions[lattice]:
                        self._distortions[lattice] = distortion
                        self._cells[lattice] = cell
                        self._reindex_ops[lattice] = reindex
                        self._reindex_ops_basis[lattice] = reindex_basis

                    state = {}

        def get_lattices(self):
            return self._lattices

        def get_cell(self, lattice):
            return self._cells[lattice]

        def get_reindex_op(self, lattice):
            return self._reindex_ops[lattice]

    return LatticeSymmetryWrapper()
