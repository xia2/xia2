import logging
import math
import os
import shutil

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Experts.LatticeExpert import SortLattices, s2l

# helpful expertise from elsewhere
from xia2.Experts.SymmetryExpert import lattice_to_spacegroup_number
from xia2.Handlers.Phil import PhilIndex

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from xia2.Wrappers.XDS.XDS import (
    imageset_to_xds,
    template_to_xds,
    xds_check_error,
    xds_check_version_supported,
)

# specific helper stuff
from xia2.Wrappers.XDS.XDSIdxrefHelpers import (
    _parse_idxref_index_origin,
    _parse_idxref_lp,
    _parse_idxref_lp_distance_etc,
    _parse_idxref_lp_quality,
    _parse_idxref_lp_subtree,
)

logger = logging.getLogger("xia2.Wrappers.XDS.XDSIdxref")


def XDSIdxref(DriverType=None, params=None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSIdxrefWrapper(DriverInstance.__class__, FrameProcessor):
        """A wrapper for wrapping XDS in idxref mode."""

        def __init__(self, params=None):
            super().__init__()

            # phil parameters

            if not params:
                from xia2.Handlers.Phil import master_phil

                params = master_phil.extract().xds.index
            self._params = params

            # now set myself up...

            self._parallel = PhilIndex.params.xia2.settings.multiprocessing.nproc
            self.set_cpu_threads(self._parallel)

            if isinstance(self._parallel, int) and self._parallel <= 1:
                self.set_executable("xds")
            else:
                self.set_executable("xds_par")

            # generic bits

            self._data_range = (0, 0)
            self._spot_range = []
            self._background_range = (0, 0)
            self._resolution_range = (0, 0)

            self._org = [0.0, 0.0]

            self._refined_origin = None
            self._refined_beam_vector = None
            self._refined_rotation_axis = None

            self._starting_angle = 0.0
            self._starting_frame = 0

            self._cell = None
            self._symm = 0

            self._a_axis = None
            self._b_axis = None
            self._c_axis = None

            # results

            self._refined_beam = (0, 0)
            self._refined_distance = 0

            self._indexing_solutions = {}

            self._indxr_input_lattice = None
            self._indxr_input_cell = None
            self._indxr_user_input_lattice = False

            self._indxr_lattice = None
            self._indxr_cell = None
            self._indxr_mosaic = None

            self._input_data_files = {}
            self._output_data_files = {}

            self._input_data_files_list = ["SPOT.XDS"]

            self._output_data_files_list = ["SPOT.XDS", "XPARM.XDS"]

            self._index_tree_problem = False

            self._fraction_rmsd_rmsphi = None

        # getter and setter for input / output data

        def set_starting_frame(self, starting_frame):
            self._starting_frame = starting_frame

        def set_starting_angle(self, starting_angle):
            self._starting_angle = starting_angle

        def set_indexer_input_lattice(self, lattice):
            self._indxr_input_lattice = lattice

        def set_indexer_user_input_lattice(self, user):
            self._indxr_user_input_lattice = user

        def set_indexer_input_cell(self, cell):
            if not isinstance(cell, type(())):
                raise RuntimeError("cell must be a 6-tuple de floats")

            if len(cell) != 6:
                raise RuntimeError("cell must be a 6-tuple de floats")

            self._indxr_input_cell = tuple(map(float, cell))

        def set_a_axis(self, a_axis):
            self._a_axis = a_axis

        def set_b_axis(self, b_axis):
            self._b_axis = b_axis

        def set_c_axis(self, c_axis):
            self._c_axis = c_axis

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def get_indexing_solutions(self):
            return self._indexing_solutions

        def get_indexing_solution(self):
            return self._indxr_lattice, self._indxr_cell, self._indxr_mosaic

        def get_index_tree_problem(self):
            return self._index_tree_problem

        def get_fraction_rmsd_rmsphi(self):
            return self._fraction_rmsd_rmsphi

        def _compare_cell(self, c_ref, c_test):
            """Compare two sets of unit cell constants: if they differ by
            less than 5% / 5 degrees return True, else False. Now configured
            by xia2.settings.xds_cell_deviation in Phil input."""

            from xia2.Handlers.Phil import PhilIndex

            if PhilIndex.params.xia2.settings.xds_cell_deviation:
                dev_l, dev_a = PhilIndex.params.xia2.settings.xds_cell_deviation
            else:
                dev_l = 0.05
                dev_a = 5.0

            for j in range(3):
                if math.fabs((c_test[j] - c_ref[j]) / c_ref[j]) > dev_l:
                    return False

            for j in range(3, 6):
                if math.fabs(c_test[j] - c_ref[j]) > dev_a:
                    return False

            return True

        # this needs setting up from setup_from_image in FrameProcessor

        def set_beam_centre(self, x, y):
            self._org = float(x), float(y)

        # this needs setting up (optionally) from refined results from
        # elsewhere

        def set_refined_distance(self, refined_distance):
            self._refined_distance = refined_distance

        def set_refined_origin(self, refined_origin):
            self._refined_origin = refined_origin

        def set_refined_beam_vector(self, refined_beam_vector):
            self._refined_beam_vector = refined_beam_vector

        def set_refined_rotation_axis(self, refined_rotation_axis):
            self._refined_rotation_axis = refined_rotation_axis

        def set_data_range(self, start, end):
            offset = self.get_frame_offset()
            self._data_range = (start - offset, end - offset)

        def add_spot_range(self, start, end):
            offset = self.get_frame_offset()
            self._spot_range.append((start - offset, end - offset))

        def set_background_range(self, start, end):
            offset = self.get_frame_offset()
            self._background_range = (start - offset, end - offset)

        def run(self, ignore_errors=False):
            """Run idxref."""

            # image_header = self.get_header()

            ## crank through the header dictionary and replace incorrect
            ## information with updated values through the indexer
            ## interface if available...

            ## need to add distance, wavelength - that should be enough...

            # if self.get_distance():
            # image_header['distance'] = self.get_distance()

            # if self.get_wavelength():
            # image_header['wavelength'] = self.get_wavelength()

            # if self.get_two_theta():
            # image_header['two_theta'] = self.get_two_theta()

            header = imageset_to_xds(
                self.get_imageset(),
                refined_beam_vector=self._refined_beam_vector,
                refined_rotation_axis=self._refined_rotation_axis,
                refined_distance=self._refined_distance,
            )

            xds_inp = open(os.path.join(self.get_working_directory(), "XDS.INP"), "w")

            # what are we doing?
            xds_inp.write("JOB=IDXREF\n")
            xds_inp.write("MAXIMUM_NUMBER_OF_PROCESSORS=%d\n" % self._parallel)

            # FIXME this needs to be calculated from the beam centre...

            if self._refined_origin:
                xds_inp.write("ORGX=%f ORGY=%f\n" % tuple(self._refined_origin))
            else:
                xds_inp.write("ORGX=%f ORGY=%f\n" % tuple(self._org))

            # FIXME in here make sure sweep is wider than 5 degrees
            # before specifying AXIS: if <= 5 degrees replace AXIS with
            # nothing - base this on the maximum possible angular separation

            min_frame = self._spot_range[0][0]
            max_frame = self._spot_range[-1][1]

            refine_params = [p for p in self._params.refine]

            phi_width = self.get_phi_width()
            if "AXIS" in refine_params and (max_frame - min_frame) * phi_width < 5.0:
                refine_params.remove("AXIS")

            xds_inp.write("REFINE(IDXREF)=%s\n" % " ".join(refine_params))

            if self._starting_frame and self._starting_angle:
                xds_inp.write("STARTING_FRAME=%d\n" % self._starting_frame)
                xds_inp.write("STARTING_ANGLE=%f\n" % self._starting_angle)

            # FIXME this looks like a potential bug - what will
            # happen if the input lattice has not been set??
            if self._indxr_input_cell:
                self._cell = self._indxr_input_cell
            if self._indxr_input_lattice:
                self._symm = lattice_to_spacegroup_number(self._indxr_input_lattice)

            if self._cell:
                xds_inp.write("SPACE_GROUP_NUMBER=%d\n" % self._symm)
                cell_format = "%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
                xds_inp.write("UNIT_CELL_CONSTANTS=%s\n" % cell_format % self._cell)

            if self._a_axis:
                xds_inp.write("UNIT_CELL_A-AXIS=%.2f %.2f %.2f\n" % tuple(self._a_axis))

            if self._b_axis:
                xds_inp.write("UNIT_CELL_B-AXIS=%.2f %.2f %.2f\n" % tuple(self._b_axis))

            if self._c_axis:
                xds_inp.write("UNIT_CELL_C-AXIS=%.2f %.2f %.2f\n" % tuple(self._c_axis))

            for record in header:
                xds_inp.write("%s\n" % record)

            name_template = template_to_xds(
                os.path.join(self.get_directory(), self.get_template())
            )

            record = "NAME_TEMPLATE_OF_DATA_FRAMES=%s\n" % name_template

            xds_inp.write(record)

            xds_inp.write("DATA_RANGE=%d %d\n" % self._data_range)
            for spot_range in self._spot_range:
                xds_inp.write("SPOT_RANGE=%d %d\n" % spot_range)
            xds_inp.write("BACKGROUND_RANGE=%d %d\n" % self._background_range)

            xds_inp.close()

            # copy the input file...
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "XDS.INP"),
                os.path.join(
                    self.get_working_directory(), "%d_IDXREF.INP" % self.get_xpid()
                ),
            )

            # write the input data files...
            for file_name in self._input_data_files_list:
                src = self._input_data_files[file_name]
                dst = os.path.join(self.get_working_directory(), file_name)
                if src != dst:
                    shutil.copyfile(src, dst)

            self.start()
            self.close_wait()

            xds_check_version_supported(self.get_all_output())
            if not ignore_errors:
                xds_check_error(self.get_all_output())

            # If xds_check_error detects any errors it will raise an exception
            # The caller can then continue using the run_continue_from_error()
            # function. If XDS does not throw any errors we just plow on.

            return self.continue_from_error()

        def continue_from_error(self):
            # copy the LP file
            shutil.copyfile(
                os.path.join(self.get_working_directory(), "IDXREF.LP"),
                os.path.join(
                    self.get_working_directory(), "%d_IDXREF.LP" % self.get_xpid()
                ),
            )

            # parse the output
            with open(os.path.join(self.get_working_directory(), "IDXREF.LP")) as fh:
                lp = fh.readlines()

            self._fraction_rmsd_rmsphi = _parse_idxref_lp_quality(lp)

            self._idxref_data = _parse_idxref_lp(lp)

            if not self._idxref_data:
                raise RuntimeError("indexing failed")

            st = _parse_idxref_lp_subtree(lp)

            if 2 in st:
                if st[2] > st[1] / 10.0:
                    logger.debug("Look closely at autoindexing solution!")
                    self._index_tree_problem = True
                    for j in sorted(st):
                        logger.debug("%2d: %5d" % (j, st[j]))

            # print out some (perhaps dire) warnings about the beam centre
            # if there is really any ambiguity...

            origins = _parse_idxref_index_origin(lp)

            assert (0, 0, 0) in origins

            quality_0 = origins[(0, 0, 0)][0]

            alternatives = []

            for hkl in origins:
                if hkl == (0, 0, 0):
                    continue
                if origins[hkl][0] < 4 * quality_0:
                    quality, delta, beam_x, beam_y = origins[hkl]
                    alternatives.append(
                        (hkl[0], hkl[1], hkl[2], quality, beam_x, beam_y)
                    )

            if alternatives:
                logger.debug("Alternative indexing possible:")
                for alternative in alternatives:
                    logger.debug("... %3d %3d %3d %4.1f %6.1f %6.1f" % alternative)

            # New algorithm in here - now use iotbx.lattice_symmetry with the
            # P1 indexing solution (solution #1) to determine the list of
            # allowable solutions - only consider those lattices in this
            # allowed list (unless we have user input)

            from xia2.Wrappers.Phenix.LatticeSymmetry import LatticeSymmetry

            ls = LatticeSymmetry()
            ls.set_lattice("aP")
            ls.set_cell(tuple(self._idxref_data[44]["cell"]))
            ls.generate()

            allowed_lattices = ls.get_lattices()

            for j in range(1, 45):
                if j not in self._idxref_data:
                    continue
                data = self._idxref_data[j]
                lattice = data["lattice"]
                fit = data["fit"]
                cell = data["cell"]
                mosaic = data["mosaic"]

                if self._symm and self._cell and self._indxr_user_input_lattice:

                    if (
                        self._compare_cell(self._cell, cell)
                        and lattice_to_spacegroup_number(lattice) == self._symm
                    ):
                        if lattice in self._indexing_solutions:
                            if self._indexing_solutions[lattice]["goodness"] < fit:
                                continue

                        self._indexing_solutions[lattice] = {
                            "goodness": fit,
                            "cell": cell,
                        }

                else:
                    if lattice in allowed_lattices or (self._symm and fit < 200.0):
                        # bug 2417 - if we have an input lattice then we
                        # don't want to include anything higher symmetry
                        # in the results table...

                        if self._symm:
                            if lattice_to_spacegroup_number(lattice) > self._symm:
                                logger.debug(
                                    "Ignoring solution with lattice %s" % lattice
                                )
                                continue

                        if lattice in self._indexing_solutions:
                            if self._indexing_solutions[lattice]["goodness"] < fit:
                                continue

                        self._indexing_solutions[lattice] = {
                            "goodness": fit,
                            "cell": cell,
                        }

            # postprocess this list, to remove lattice solutions which are
            # lower symmetry but higher penalty than the putative correct
            # one, if self._symm is set...

            if self._symm:
                assert (
                    self._indexing_solutions
                ), "No remaining indexing solutions (%s, %s)" % (
                    s2l(self._symm),
                    self._symm,
                )
            else:
                assert self._indexing_solutions, "No remaining indexing solutions"

            if self._symm:
                max_p = 2.0 * self._indexing_solutions[s2l(self._symm)]["goodness"]
                to_remove = []
                for lattice in self._indexing_solutions:
                    if self._indexing_solutions[lattice]["goodness"] > max_p:
                        to_remove.append(lattice)
                for lattice in to_remove:
                    logger.debug("Ignoring solution with lattice %s" % lattice)
                    del self._indexing_solutions[lattice]

            # get the highest symmetry "acceptable" solution

            items = [
                (k, self._indexing_solutions[k]["cell"])
                for k in self._indexing_solutions
            ]

            # if there was a preassigned cell and symmetry return now
            # with everything done, else select the "top" solution and
            # reindex, resetting the input cell and symmetry.

            if self._cell:

                # select the solution which matches the input unit cell
                # actually after the changes above this should now be the
                # only solution in the table..

                logger.debug(
                    "Target unit cell: %.2f %.2f %.2f %.2f %.2f %.2f" % self._cell
                )

                for l in items:
                    if lattice_to_spacegroup_number(l[0]) == self._symm:
                        # this should be the correct solution...
                        # check the unit cell...
                        cell = l[1]

                        cell_str = "%.2f %.2f %.2f %.2f %.2f %.2f" % cell
                        logger.debug("Chosen unit cell: %s" % cell_str)

                        self._indxr_lattice = l[0]
                        self._indxr_cell = l[1]
                        self._indxr_mosaic = mosaic

            else:

                # select the top solution as the input cell and reset the
                # "indexing done" flag

                sorted_list = SortLattices(items)
                #       print sorted_list

                self._symm = lattice_to_spacegroup_number(sorted_list[0][0])
                self._cell = sorted_list[0][1]

                return False

            # get the refined distance &c.

            beam, distance = _parse_idxref_lp_distance_etc(lp)

            self._refined_beam = beam
            self._refined_distance = distance

            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = os.path.join(
                    self.get_working_directory(), file
                )

            return True

    return XDSIdxrefWrapper(params)
