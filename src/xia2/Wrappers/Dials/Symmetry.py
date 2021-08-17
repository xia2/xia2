import json
import os
import sys

from cctbx import sgtbx, crystal, uctbx
from cctbx.sgtbx import bravais_types

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex


def DialsSymmetry(DriverType=None):
    """A factory for DialsSymmetryWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsSymmetryWrapper(DriverInstance.__class__):
        """A wrapper for dials.symmetry"""

        def __init__(self):
            # generic things
            super().__init__()

            self.set_executable("dials.symmetry")

            self._input_laue_group = None

            self._experiments_filenames = []
            self._reflections_filenames = []
            self._output_experiments_filename = None
            self._output_reflections_filename = None

            self._hklin = None
            self._hklout = None
            self._pointgroup = None
            self._spacegroup = None
            self._reindex_matrix = None
            self._reindex_operator = None
            self._spacegroup_reindex_matrix = None
            self._spacegroup_reindex_operator = None
            self._confidence = 0.0
            self._hklref = None
            self._xdsin = None
            self._probably_twinned = False
            self._allow_out_of_sequence_files = False

            self._relative_length_tolerance = 0.05
            self._absolute_angle_tolerance = 2
            self._laue_group = "auto"
            self._sys_abs_check = True

            # space to store all possible solutions, to allow discussion of
            # the correct lattice with the indexer... this should be a
            # list containing e.g. 'tP'
            self._possible_lattices = []

            self._lattice_to_laue = {}

            # all "likely" spacegroups...
            self._likely_spacegroups = []

            # and unit cell information
            self._cell_info = {}
            self._cell = None

            self._json = None

        def set_mode_absences_only(self):
            self._laue_group = None
            self._sys_abs_check = True

        def set_hklin(self, hklin):
            self._hklin = hklin

        def get_hklin(self):
            return self._hklin

        def add_experiments(self, experiments):
            self._experiments_filenames.append(experiments)

        def add_reflections(self, reflections):
            self._reflections_filenames.append(reflections)

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filenames = [experiments_filename]

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filenames = [reflections_filename]

        def set_output_experiments_filename(self, experiments_filename):
            self._output_experiments_filename = experiments_filename

        def set_output_reflections_filename(self, reflections_filename):
            self._output_reflections_filename = reflections_filename

        def get_output_reflections_filename(self):
            return self._output_reflections_filename

        def get_output_experiments_filename(self):
            return self._output_experiments_filename

        def set_json(self, json):
            self._json = json

        def set_allow_out_of_sequence_files(self, allow=True):
            self._allow_out_of_sequence_files = allow

        def set_tolerance(
            self, relative_length_tolerance=0.05, absolute_angle_tolerance=2
        ):
            self._relative_length_tolerance = relative_length_tolerance
            self._absolute_angle_tolerance = absolute_angle_tolerance

        def set_correct_lattice(self, lattice):
            """In a rerunning situation, set the correct lattice, which will
            assert a correct lauegroup based on the previous run of the
            program..."""

            if self._lattice_to_laue == {}:
                raise RuntimeError("no lattice to lauegroup mapping")

            if lattice not in self._lattice_to_laue:
                raise RuntimeError("lattice %s not possible" % lattice)
            self._input_laue_group = self._lattice_to_laue[lattice]

            with open(self._json, "rb") as f:
                d = json.load(f)
            for soln in d["subgroup_scores"]:
                patterson_group = sgtbx.space_group(str(soln["patterson_group"]))
                if PhilIndex.params.xia2.settings.symmetry.chirality in (
                    None,
                    "chiral",
                ):
                    patterson_group = patterson_group.build_derived_acentric_group()

                if patterson_group == self._input_laue_group:
                    # set this as correct solution
                    self.set_best_solution(d, soln)
                    break
            # okay so now set pg and lattices, but need to update output file by reindexing

        def decide_pointgroup(self, ignore_errors=False, batches=None):
            """Decide on the correct pointgroup/spacegroup for hklin."""

            self.clear_command_line()

            if self._hklref:
                self.add_command_line("hklref")
                self.add_command_line(self._hklref)

            if self._hklin is not None:
                assert os.path.isfile(self._hklin)
                self.add_command_line(self._hklin)
            else:
                assert self._experiments_filenames  # is not None
                assert self._reflections_filenames  # is not None
                for exp in self._experiments_filenames:
                    self.add_command_line(exp)
                for refl in self._reflections_filenames:
                    self.add_command_line(refl)

                if not self._output_experiments_filename:
                    self._output_experiments_filename = os.path.join(
                        self.get_working_directory(),
                        "%d_symmetrized.expt" % self.get_xpid(),
                    )
                if not self._output_reflections_filename:
                    self._output_reflections_filename = os.path.join(
                        self.get_working_directory(),
                        "%d_symmetrized.refl" % self.get_xpid(),
                    )

                self.add_command_line(
                    "output.experiments=%s" % self._output_experiments_filename
                )
                self.add_command_line(
                    "output.reflections=%s" % self._output_reflections_filename
                )
            if self._laue_group is None:
                self.add_command_line("laue_group=None")
            if not self._sys_abs_check:
                self.add_command_line("systematic_absences.check=False")
            self.add_command_line(
                "relative_length_tolerance=%s" % self._relative_length_tolerance
            )
            self.add_command_line(
                "absolute_angle_tolerance=%s" % self._absolute_angle_tolerance
            )
            self.add_command_line("best_monoclinic_beta=False")
            if not self._json:
                self._json = os.path.join(
                    self.get_working_directory(),
                    "%d_dials_symmetry.json" % self.get_xpid(),
                )

            self.add_command_line("output.json=%s" % self._json)

            if self._input_laue_group:
                self.add_command_line("lattice_group=%s" % self._input_laue_group)

            self.start()

            self.close_wait()

            # check for errors
            self.check_for_errors()

            if self._laue_group is not None:
                with open(self._json) as fh:
                    d = json.load(fh)
                best_solution = d["subgroup_scores"][0]

                self.set_best_solution(d, best_solution)

        def set_best_solution(self, d, best_solution):
            patterson_group = sgtbx.space_group(str(best_solution["patterson_group"]))
            if PhilIndex.params.xia2.settings.symmetry.chirality in (None, "chiral"):
                patterson_group = patterson_group.build_derived_acentric_group()
            cb_op_min_best = sgtbx.change_of_basis_op(str(best_solution["cb_op"]))
            # This should only be called with multiple sweeps if they're already
            # consistently indexed, so assert that they all have the same
            # cb_op_inp_min
            assert len(set(d["cb_op_inp_min"])) == 1
            cb_op_inp_min = sgtbx.change_of_basis_op(str(d["cb_op_inp_min"][0]))

            min_cell = uctbx.unit_cell(d["min_cell_symmetry"]["unit_cell"])
            best_cell = min_cell.change_basis(cb_op=cb_op_min_best)

            cs = crystal.symmetry(
                unit_cell=best_cell,
                space_group=patterson_group,
                assert_is_compatible_unit_cell=False,
            )
            self._pointgroup = cs.space_group().type().lookup_symbol()

            self._confidence = best_solution["confidence"]
            self._totalprob = best_solution["likelihood"]
            cb_op_inp_best = cb_op_min_best * cb_op_inp_min
            self._reindex_operator = cb_op_inp_best.as_xyz()
            self._reindex_matrix = cb_op_inp_best.c().r().as_double()

            if not self._input_laue_group and not self._hklref:
                for score in d["subgroup_scores"]:
                    patterson_group = sgtbx.space_group(str(score["patterson_group"]))
                    if PhilIndex.params.xia2.settings.symmetry.chirality in (
                        None,
                        "chiral",
                    ):
                        patterson_group = patterson_group.build_derived_acentric_group()

                    cb_op_inp_this = sgtbx.change_of_basis_op(str(score["cb_op"]))
                    unit_cell = min_cell.change_basis(
                        cb_op=sgtbx.change_of_basis_op(str(cb_op_inp_this))
                    )
                    cs = crystal.symmetry(
                        unit_cell=unit_cell,
                        space_group=patterson_group,
                        assert_is_compatible_unit_cell=False,
                    )
                    patterson_group = cs.space_group()

                    netzc = score["z_cc_net"]
                    # record this as a possible lattice if its Z score is positive
                    lattice = str(bravais_types.bravais_lattice(group=patterson_group))
                    if lattice not in self._possible_lattices:
                        if netzc > 0.0:
                            self._possible_lattices.append(lattice)
                        self._lattice_to_laue[lattice] = patterson_group
                    self._likely_spacegroups.append(
                        patterson_group.type().lookup_symbol()
                    )

            elif self._input_laue_group:
                self._possible_lattices = [
                    str(bravais_types.bravais_lattice(group=patterson_group))
                ]
                self._likely_spacegroups = [patterson_group.type().lookup_symbol()]

        def get_reindex_matrix(self):
            return self._reindex_matrix

        def get_reindex_operator(self):
            return self._reindex_operator

        def get_pointgroup(self):
            return self._pointgroup

        def get_cell(self):
            return self._cell

        def get_probably_twinned(self):
            return self._probably_twinned

        # FIXME spacegroup != pointgroup
        decide_spacegroup = decide_pointgroup
        get_spacegroup = get_pointgroup
        get_spacegroup_reindex_operator = get_reindex_operator
        get_spacegroup_reindex_matrix = get_reindex_matrix

        def get_likely_spacegroups(self):
            return self._likely_spacegroups

        def get_confidence(self):
            return self._confidence

        def get_possible_lattices(self):
            return self._possible_lattices

    return DialsSymmetryWrapper()


if __name__ == "__main__":
    p = DialsSymmetry()

    hklin = sys.argv[1]

    p.set_hklin(hklin)

    p.decide_pointgroup()
