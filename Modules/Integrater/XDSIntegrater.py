# An implementation of the Integrater interface using XDS. This depends on the
# XDS wrappers to actually implement the functionality.
#
# This will "wrap" the XDS programs DEFPIX and INTEGRATE - CORRECT is
# considered to be a part of the scaling - see XDSScaler.py.


import copy
import inspect
import logging
import math
import os
import shutil
import time

import scitbx.matrix
from dials.array_family import flex
from iotbx.xds import xparm
from xia2.Experts.SymmetryExpert import (
    lattice_to_spacegroup_number,
    mat_to_symop,
    r_to_rt,
    rt_to_r,
)
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import auto_logfiler
from xia2.Modules.Indexer.XDSIndexer import XDSIndexer
from xia2.Schema.Exceptions.BadLatticeError import BadLatticeError
from xia2.Schema.Interfaces.Integrater import Integrater
from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory
from xia2.Wrappers.CCP4.Reindex import Reindex
from xia2.Wrappers.Dials.ImportXDS import ImportXDS
from xia2.Wrappers.XDS.XDSCorrect import XDSCorrect as _Correct
from xia2.Wrappers.XDS.XDSDefpix import XDSDefpix as _Defpix
from xia2.Wrappers.XDS.XDSIntegrate import XDSIntegrate as _Integrate

logger = logging.getLogger("xia2.Modules.Integrater.XDSIntegrater")


class XDSIntegrater(Integrater):
    """A class to implement the Integrater interface using *only* XDS
    programs."""

    def __init__(self):
        super().__init__()

        # check that the programs exist - this will raise an exception if
        # they do not...

        _Integrate()

        # place to store working data
        self._xds_data_files = {}
        self._intgr_experiments_filename = None

        # internal parameters to pass around
        self._xds_integrate_parameters = {}

        # factory for pointless -used for converting INTEGRATE.HKL to .mtz
        self._factory = CCP4Factory()

    def to_dict(self):
        obj = Integrater.to_dict(self)

        attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
        for a in attributes:
            if a[0].startswith("_xds_"):
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        return_obj = super().from_dict(obj)
        return_obj._factory = CCP4Factory()
        return return_obj

    # overload these methods as we don't want the resolution range
    # feeding back... aha - but we may want to assign them
    # from outside!

    def set_integrater_resolution(self, dmin, dmax, user=False):
        if user:
            Integrater.set_integrater_resolution(self, dmin, dmax, user)

    def set_integrater_high_resolution(self, dmin, user=False):
        if user:
            Integrater.set_integrater_high_resolution(self, dmin, user)

    def set_integrater_low_resolution(self, dmax, user=False):
        self._intgr_reso_low = dmax

    def get_integrater_corrected_intensities(self):
        self.integrate()
        return self._intgr_corrected_hklout

    # admin functions

    def _set_integrater_reindex_operator_callback(self):
        """If a REMOVE.HKL file exists in the working
        directory, remove it..."""
        if os.path.exists(os.path.join(self.get_working_directory(), "REMOVE.HKL")):
            os.remove(os.path.join(self.get_working_directory(), "REMOVE.HKL"))
            logger.debug("Deleting REMOVE.HKL as reindex op set.")

    # factory functions

    def Defpix(self):
        defpix = _Defpix()
        defpix.set_working_directory(self.get_working_directory())

        defpix.setup_from_imageset(self.get_imageset())

        if self.get_distance():
            defpix.set_distance(self.get_distance())

        if self.get_wavelength():
            defpix.set_wavelength(self.get_wavelength())

        value_range_for_trusted_detector_pixels = (
            PhilIndex.params.xds.defpix.value_range_for_trusted_detector_pixels
        )
        if value_range_for_trusted_detector_pixels is not None:
            defpix.set_value_range_for_trusted_detector_pixels(
                value_range_for_trusted_detector_pixels
            )

        auto_logfiler(defpix, "DEFPIX")

        return defpix

    def Integrate(self):
        integrate = _Integrate(params=PhilIndex.params.xds.integrate)
        integrate.set_working_directory(self.get_working_directory())

        integrate.setup_from_imageset(self.get_imageset())

        if self.get_distance():
            integrate.set_distance(self.get_distance())

        if self.get_wavelength():
            integrate.set_wavelength(self.get_wavelength())

        auto_logfiler(integrate, "INTEGRATE")

        return integrate

    def Correct(self):
        correct = _Correct(params=PhilIndex.params.xds.correct)
        correct.set_working_directory(self.get_working_directory())

        correct.setup_from_imageset(self.get_imageset())

        if self.get_distance():
            correct.set_distance(self.get_distance())

        if self.get_wavelength():
            correct.set_wavelength(self.get_wavelength())

        if self.get_integrater_ice():
            correct.set_ice(self.get_integrater_ice())

        if self.get_integrater_excluded_regions():
            correct.set_excluded_regions(self.get_integrater_excluded_regions())

        if self.get_integrater_anomalous():
            correct.set_anomalous(True)

        if self.get_integrater_low_resolution() > 0.0:
            logger.debug(
                "Using low resolution limit: %.2f"
                % self.get_integrater_low_resolution()
            )
            correct.set_resolution_high(0.0)
            correct.set_resolution_low(self.get_integrater_low_resolution())

        auto_logfiler(correct, "CORRECT")

        return correct

    # now some real functions, which do useful things

    def _integrater_reset_callback(self):
        """Delete all results on a reset."""
        logger.debug("Deleting all stored results.")
        self._xds_data_files = {}
        self._xds_integrate_parameters = {}

    def _integrate_prepare(self):
        """Prepare for integration - in XDS terms this may mean rerunning
        IDXREF to get the XPARM etc. DEFPIX is considered part of the full
        integration as it is resolution dependent."""

        Citations.cite("xds")

        # decide what images we are going to process, if not already
        # specified
        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(
                min(images) + self.get_frame_offset(),
                max(images) + self.get_frame_offset(),
            )

        logger.debug("XDS INTEGRATE PREPARE:")
        logger.debug("Wavelength: %.6f" % self.get_wavelength())
        logger.debug("Distance: %.2f" % self.get_distance())

        idxr = self._intgr_refiner.get_refiner_indexer(self.get_integrater_epoch())

        if idxr is None:
            idxr = XDSIndexer()
            self._intgr_refiner.add_refiner_indexer(self.get_integrater_epoch(), idxr)
            self.set_integrater_prepare_done(False)
            # self.set_integrater_indexer()
            idxr.set_indexer_sweep(self.get_integrater_sweep())

            idxr.set_working_directory(self.get_working_directory())

            idxr.setup_from_imageset(self.get_imageset())

            if self.get_frame_wedge():
                wedge = self.get_frame_wedge()
                logger.debug("Propogating wedge limit: %d %d" % wedge)
                idxr.set_frame_wedge(wedge[0], wedge[1], apply_offset=False)

            # this needs to be set up from the contents of the
            # Integrater frame processer - wavelength &c.

            if self.get_beam_centre():
                idxr.set_beam_centre(self.get_beam_centre())

            if self.get_distance():
                idxr.set_distance(self.get_distance())

            if self.get_wavelength():
                idxr.set_wavelength(self.get_wavelength())

        # get the unit cell from this indexer to initiate processing
        # if it is new... and also copy out all of the information for
        # the XDS indexer if not...

        # copy the data across
        self._xds_data_files = copy.deepcopy(
            self._intgr_refiner.get_refiner_payload(self.get_integrater_epoch())
        )
        if self._xds_data_files is None:
            self._xds_data_files = {}

        logger.debug("Files available at the end of XDS integrate prepare:")
        for f in self._xds_data_files:
            logger.debug("%s" % f)

        experiment = self._intgr_refiner.get_refined_experiment_list(
            self.get_integrater_epoch()
        )[0]
        # copy across the trusted_range - it got lost along the way
        old_detector = self.get_detector()
        self.set_detector(experiment.detector)
        for p1, p2 in zip(old_detector, self.get_detector()):
            p2.set_trusted_range(p1.get_trusted_range())
        self.set_beam_obj(experiment.beam)
        self.set_goniometer(experiment.goniometer)

        # set a low resolution limit (which isn't really used...)
        # this should perhaps be done more intelligently from an
        # analysis of the spot list or something...?

        if not self.get_integrater_low_resolution():

            dmax = self._intgr_refiner.get_indexer_low_resolution(
                self.get_integrater_epoch()
            )
            self.set_integrater_low_resolution(dmax)

            logger.debug(
                "Low resolution set to: %s" % self.get_integrater_low_resolution()
            )

        # delete things we should not know e.g. the postrefined cell from
        # CORRECT - c/f bug # 2695
        self._intgr_cell = None
        self._intgr_spacegroup_number = None

    def _integrate(self):
        """Actually do the integration - in XDS terms this will mean running
        DEFPIX and INTEGRATE to measure all the reflections."""

        experiment = self._intgr_refiner.get_refined_experiment_list(
            self.get_integrater_epoch()
        )[0]
        crystal_model = experiment.crystal
        self._intgr_refiner_cell = crystal_model.get_unit_cell().parameters()

        defpix = self.Defpix()

        # pass in the correct data

        for file in (
            "X-CORRECTIONS.cbf",
            "Y-CORRECTIONS.cbf",
            "BKGINIT.cbf",
            "XPARM.XDS",
        ):
            defpix.set_input_data_file(file, self._xds_data_files[file])

        defpix.set_data_range(
            self._intgr_wedge[0] + self.get_frame_offset(),
            self._intgr_wedge[1] + self.get_frame_offset(),
        )

        if (
            self.get_integrater_high_resolution() > 0.0
            and self.get_integrater_user_resolution()
        ):
            logger.debug(
                "Setting resolution limit in DEFPIX to %.2f"
                % self.get_integrater_high_resolution()
            )
            defpix.set_resolution_high(self.get_integrater_high_resolution())
            defpix.set_resolution_low(self.get_integrater_low_resolution())

        elif self.get_integrater_low_resolution():
            logger.debug(
                "Setting low resolution limit in DEFPIX to %.2f"
                % self.get_integrater_low_resolution()
            )
            defpix.set_resolution_high(0.0)
            defpix.set_resolution_low(self.get_integrater_low_resolution())

        defpix.run()

        # and gather the result files
        for file in ("BKGPIX.cbf", "ABS.cbf"):
            self._xds_data_files[file] = defpix.get_output_data_file(file)

        integrate = self.Integrate()

        if self._xds_integrate_parameters:
            integrate.set_updates(self._xds_integrate_parameters)

        # decide what images we are going to process, if not already
        # specified

        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images), max(images))

        integrate.set_data_range(
            self._intgr_wedge[0] + self.get_frame_offset(),
            self._intgr_wedge[1] + self.get_frame_offset(),
        )

        for file in (
            "X-CORRECTIONS.cbf",
            "Y-CORRECTIONS.cbf",
            "BLANK.cbf",
            "BKGPIX.cbf",
            "GAIN.cbf",
        ):
            integrate.set_input_data_file(file, self._xds_data_files[file])

        if "GXPARM.XDS" in self._xds_data_files:
            logger.debug("Using globally refined parameters")
            integrate.set_input_data_file(
                "XPARM.XDS", self._xds_data_files["GXPARM.XDS"]
            )
            integrate.set_refined_xparm()
        else:
            integrate.set_input_data_file(
                "XPARM.XDS", self._xds_data_files["XPARM.XDS"]
            )

        integrate.run()

        self._intgr_per_image_statistics = integrate.get_per_image_statistics()
        logger.info(self.show_per_image_statistics())

        # record the log file -

        pname, xname, dname = self.get_integrater_project_info()
        sweep = self.get_integrater_sweep_name()
        FileHandler.record_log_file(
            f"{pname} {xname} {dname} {sweep} INTEGRATE",
            os.path.join(self.get_working_directory(), "INTEGRATE.LP"),
        )

        # and copy the first pass INTEGRATE.HKL...

        lattice = self._intgr_refiner.get_refiner_lattice()
        if not os.path.exists(
            os.path.join(self.get_working_directory(), "INTEGRATE-%s.HKL" % lattice)
        ):
            here = self.get_working_directory()
            shutil.copyfile(
                os.path.join(here, "INTEGRATE.HKL"),
                os.path.join(here, "INTEGRATE-%s.HKL" % lattice),
            )

        # record INTEGRATE.HKL
        FileHandler.record_more_data_file(
            f"{pname} {xname} {dname} {sweep} INTEGRATE",
            os.path.join(self.get_working_directory(), "INTEGRATE.HKL"),
        )

        # should the existence of these require that I rerun the
        # integration or can we assume that the application of a
        # sensible resolution limit will achieve this??

        self._xds_integrate_parameters = integrate.get_updates()

        # record the mosaic spread &c.

        m_min, m_mean, m_max = integrate.get_mosaic()
        self.set_integrater_mosaic_min_mean_max(m_min, m_mean, m_max)

        logger.info(
            "Mosaic spread: %.3f < %.3f < %.3f"
            % self.get_integrater_mosaic_min_mean_max()
        )

        return os.path.join(self.get_working_directory(), "INTEGRATE.HKL")

    def _integrate_finish(self):
        """Finish off the integration by running correct."""

        # first run the postrefinement etc with spacegroup P1
        # and the current unit cell - this will be used to
        # obtain a benchmark rmsd in pixels / phi and also
        # cell deviations (this is working towards spotting bad
        # indexing solutions) - only do this if we have no
        # reindex matrix... and no postrefined cell...

        p1_deviations = None

        # fix for bug # 3264 -
        # if we have not run integration with refined parameters, make it so...
        # erm? shouldn't this therefore return if this is the principle, or
        # set the flag after we have tested the lattice?

        if (
            "GXPARM.XDS" not in self._xds_data_files
            and PhilIndex.params.xds.integrate.reintegrate
        ):
            logger.debug("Resetting integrater, to ensure refined orientation is used")
            self.set_integrater_done(False)

        if (
            not self.get_integrater_reindex_matrix()
            and not self._intgr_cell
            and PhilIndex.params.xia2.settings.lattice_rejection
            and not self.get_integrater_sweep().get_user_lattice()
        ):
            correct = self.Correct()

            correct.set_data_range(
                self._intgr_wedge[0] + self.get_frame_offset(),
                self._intgr_wedge[1] + self.get_frame_offset(),
            )

            if self.get_polarization() > 0.0:
                correct.set_polarization(self.get_polarization())

            # FIXME should this be using the correctly transformed
            # cell or are the results ok without it?!

            correct.set_spacegroup_number(1)
            correct.set_cell(self._intgr_refiner_cell)

            correct.run()

            cell = correct.get_result("cell")
            cell_esd = correct.get_result("cell_esd")

            logger.debug("Postrefinement in P1 results:")
            logger.debug("%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f" % tuple(cell))
            logger.debug("%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f" % tuple(cell_esd))
            logger.debug(
                "Deviations: %.2f pixels %.2f degrees"
                % (correct.get_result("rmsd_pixel"), correct.get_result("rmsd_phi"))
            )

            p1_deviations = (
                correct.get_result("rmsd_pixel"),
                correct.get_result("rmsd_phi"),
            )

        # next run the postrefinement etc with the given
        # cell / lattice - this will be the assumed result...

        integrate_hkl = os.path.join(self.get_working_directory(), "INTEGRATE.HKL")

        if PhilIndex.params.xia2.settings.input.format.dynamic_shadowing:
            from dxtbx.serialize import load
            from dials.algorithms.shadowing.filter import filter_shadowed_reflections

            experiments_json = xparm_xds_to_experiments_json(
                os.path.join(self.get_working_directory(), "XPARM.XDS"),
                self.get_working_directory(),
            )
            experiments = load.experiment_list(experiments_json, check_format=True)
            imageset = experiments[0].imageset
            masker = (
                imageset.get_format_class()
                .get_instance(imageset.paths()[0])
                .get_masker()
            )
            if masker is not None:
                integrate_filename = integrate_hkl_to_reflection_file(
                    integrate_hkl, experiments_json, self.get_working_directory()
                )
                reflections = flex.reflection_table.from_file(integrate_filename)

                t0 = time.time()
                sel = filter_shadowed_reflections(experiments, reflections)
                shadowed = reflections.select(sel)
                t1 = time.time()
                logger.debug(
                    "Filtered %i reflections in %.1f seconds"
                    % (sel.count(True), t1 - t0)
                )

                filter_hkl = os.path.join(self.get_working_directory(), "FILTER.HKL")
                with open(filter_hkl, "wb") as f:
                    detector = experiments[0].detector
                    for ref in shadowed:
                        p = detector[ref["panel"]]
                        ox, oy = p.get_raw_image_offset()
                        h, k, l = ref["miller_index"]
                        x, y, z = ref["xyzcal.px"]
                        dx, dy, dz = (2, 2, 2)
                        print(
                            "%i %i %i %.1f %.1f %.1f %.1f %.1f %.1f"
                            % (h, k, l, x + ox, y + oy, z, dx, dy, dz),
                            file=f,
                        )
                t2 = time.time()
                logger.debug("Written FILTER.HKL in %.1f seconds" % (t2 - t1))

        correct = self.Correct()

        correct.set_data_range(
            self._intgr_wedge[0] + self.get_frame_offset(),
            self._intgr_wedge[1] + self.get_frame_offset(),
        )

        if self.get_polarization() > 0.0:
            correct.set_polarization(self.get_polarization())

        # BUG # 2695 probably comes from here - need to check...
        # if the pointless interface comes back with a different
        # crystal setting then the unit cell stored in self._intgr_cell
        # needs to be set to None...

        if self.get_integrater_spacegroup_number():
            correct.set_spacegroup_number(self.get_integrater_spacegroup_number())
            if not self._intgr_cell:
                raise RuntimeError("no unit cell to recycle")
            correct.set_cell(self._intgr_cell)

        # BUG # 3113 - new version of XDS will try and figure the
        # best spacegroup out from the intensities (and get it wrong!)
        # unless we set the spacegroup and cell explicitly

        if not self.get_integrater_spacegroup_number():
            cell = self._intgr_refiner_cell
            lattice = self._intgr_refiner.get_refiner_lattice()
            spacegroup_number = lattice_to_spacegroup_number(lattice)

            # this should not prevent the postrefinement from
            # working correctly, else what is above would not
            # work correctly (the postrefinement test)

            correct.set_spacegroup_number(spacegroup_number)
            correct.set_cell(cell)

            logger.debug("Setting spacegroup to: %d" % spacegroup_number)
            logger.debug("Setting cell to: %.2f %.2f %.2f %.2f %.2f %.2f" % tuple(cell))

        if self.get_integrater_reindex_matrix():

            # bug! if the lattice is not primitive the values in this
            # reindex matrix need to be multiplied by a constant which
            # depends on the Bravais lattice centering.

            lattice = self._intgr_refiner.get_refiner_lattice()

            matrix = self.get_integrater_reindex_matrix()
            matrix = scitbx.matrix.sqr(matrix).transpose().elems
            matrix = r_to_rt(matrix)

            if lattice[1] == "P":
                mult = 1
            elif lattice[1] == "C" or lattice[1] == "I":
                mult = 2
            elif lattice[1] == "R":
                mult = 3
            elif lattice[1] == "F":
                mult = 4
            else:
                raise RuntimeError("unknown multiplier for lattice %s" % lattice)

            logger.debug("REIDX multiplier for lattice %s: %d" % (lattice, mult))

            mult_matrix = [mult * m for m in matrix]

            logger.debug(
                "REIDX set to %d %d %d %d %d %d %d %d %d %d %d %d" % tuple(mult_matrix)
            )
            correct.set_reindex_matrix(mult_matrix)

        correct.run()

        # record the log file -

        pname, xname, dname = self.get_integrater_project_info()
        sweep = self.get_integrater_sweep_name()
        FileHandler.record_log_file(
            f"{pname} {xname} {dname} {sweep} CORRECT",
            os.path.join(self.get_working_directory(), "CORRECT.LP"),
        )

        FileHandler.record_more_data_file(
            f"{pname} {xname} {dname} {sweep} CORRECT",
            os.path.join(self.get_working_directory(), "XDS_ASCII.HKL"),
        )

        # erm. just to be sure
        if self.get_integrater_reindex_matrix() and correct.get_reindex_used():
            raise RuntimeError("Reindex panic!")

        # get the reindex operation used, which may be useful if none was
        # set but XDS decided to apply one, e.g. #419.

        if not self.get_integrater_reindex_matrix() and correct.get_reindex_used():
            # convert this reindex operation to h, k, l form: n.b. this
            # will involve dividing through by the lattice centring multiplier

            matrix = rt_to_r(correct.get_reindex_used())

            matrix = scitbx.matrix.sqr(matrix).transpose().elems

            lattice = self._intgr_refiner.get_refiner_lattice()

            if lattice[1] == "P":
                mult = 1.0
            elif lattice[1] == "C" or lattice[1] == "I":
                mult = 2.0
            elif lattice[1] == "R":
                mult = 3.0
            elif lattice[1] == "F":
                mult = 4.0

            matrix = [m / mult for m in matrix]

            reindex_op = mat_to_symop(matrix)

            # assign this to self: will this reset?! make for a leaky
            # abstraction and just assign this...

            # self.set_integrater_reindex_operator(reindex)

            self._intgr_reindex_operator = reindex_op

        # record the log file -

        pname, xname, dname = self.get_integrater_project_info()
        sweep = self.get_integrater_sweep_name()
        FileHandler.record_log_file(
            f"{pname} {xname} {dname} {sweep} CORRECT",
            os.path.join(self.get_working_directory(), "CORRECT.LP"),
        )

        # should get some interesting stuff from the XDS correct file
        # here, for instance the resolution range to use in integration
        # (which should be fed back if not fast) and so on...

        self._intgr_corrected_hklout = os.path.join(
            self.get_working_directory(), "XDS_ASCII.HKL"
        )

        # also record the batch range - needed for the analysis of the
        # radiation damage in chef...

        self._intgr_batches_out = (self._intgr_wedge[0], self._intgr_wedge[1])

        # FIXME perhaps I should also feedback the GXPARM file here??
        for file in ["GXPARM.XDS"]:
            self._xds_data_files[file] = correct.get_output_data_file(file)

        # record the postrefined cell parameters
        self._intgr_cell = correct.get_result("cell")
        self._intgr_n_ref = correct.get_result("n_ref")

        logger.debug('Postrefinement in "correct" spacegroup results:')
        logger.debug(
            "%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f" % tuple(correct.get_result("cell"))
        )
        logger.debug(
            "%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f"
            % tuple(correct.get_result("cell_esd"))
        )
        logger.debug(
            "Deviations: %.2f pixels %.2f degrees"
            % (correct.get_result("rmsd_pixel"), correct.get_result("rmsd_phi"))
        )

        logger.debug(
            "Error correction parameters: A=%.3f B=%.3f"
            % correct.get_result("sdcorrection")
        )

        # compute misorientation of axes

        xparm_file = os.path.join(self.get_working_directory(), "GXPARM.XDS")

        handle = xparm.reader()
        handle.read_file(xparm_file)

        rotn = handle.rotation_axis
        beam = handle.beam_vector

        dot = sum(rotn[j] * beam[j] for j in range(3))
        r = math.sqrt(sum(rotn[j] * rotn[j] for j in range(3)))
        b = math.sqrt(sum(beam[j] * beam[j] for j in range(3)))

        rtod = 180.0 / math.pi

        angle = rtod * math.fabs(0.5 * math.pi - math.acos(dot / (r * b)))

        logger.debug("Axis misalignment %.2f degrees" % angle)

        correct_deviations = (
            correct.get_result("rmsd_pixel"),
            correct.get_result("rmsd_phi"),
        )

        if p1_deviations:
            # compare and reject if both > 50% higher - though adding a little
            # flexibility - 0.5 pixel / osc width slack.

            pixel = p1_deviations[0]
            phi = math.sqrt(0.05 * 0.05 + p1_deviations[1] * p1_deviations[1])

            threshold = PhilIndex.params.xia2.settings.lattice_rejection_threshold
            logger.debug("RMSD ratio: %.2f" % (correct_deviations[0] / pixel))
            logger.debug("RMSPhi ratio: %.2f" % (correct_deviations[1] / phi))

            if (
                correct_deviations[0] / pixel > threshold
                and correct_deviations[1] / phi > threshold
            ):

                logger.info("Eliminating this indexing solution as postrefinement")
                logger.info("deviations rather high relative to triclinic")
                raise BadLatticeError("high relative deviations in postrefinement")

        if (
            not PhilIndex.params.dials.fast_mode
            and not PhilIndex.params.xds.keep_outliers
        ):
            # check for alien reflections and perhaps recycle - removing them
            correct_remove = correct.get_remove()
            if correct_remove:
                current_remove = set()
                final_remove = []

                # first ensure that there are no duplicate entries...
                if os.path.exists(
                    os.path.join(self.get_working_directory(), "REMOVE.HKL")
                ):
                    with open(
                        os.path.join(self.get_working_directory(), "REMOVE.HKL")
                    ) as fh:
                        for line in fh.readlines():
                            h, k, l = list(map(int, line.split()[:3]))
                            z = float(line.split()[3])

                            if (h, k, l, z) not in current_remove:
                                current_remove.add((h, k, l, z))

                    for c in correct_remove:
                        if c in current_remove:
                            continue
                        final_remove.append(c)

                    logger.debug(
                        "%d alien reflections are already removed"
                        % (len(correct_remove) - len(final_remove))
                    )
                else:
                    # we want to remove all of the new dodgy reflections
                    final_remove = correct_remove

                z_min = PhilIndex.params.xds.z_min
                rejected = 0

                with open(
                    os.path.join(self.get_working_directory(), "REMOVE.HKL"), "w"
                ) as remove_hkl:

                    # write in the old reflections
                    for remove in current_remove:
                        z = remove[3]
                        if z >= z_min:
                            remove_hkl.write("%d %d %d %f\n" % remove)
                        else:
                            rejected += 1
                    logger.debug(
                        "Wrote %d old reflections to REMOVE.HKL"
                        % (len(current_remove) - rejected)
                    )
                    logger.debug("Rejected %d as z < %f" % (rejected, z_min))

                    # and the new reflections
                    rejected = 0
                    used = 0
                    for remove in final_remove:
                        z = remove[3]
                        if z >= z_min:
                            used += 1
                            remove_hkl.write("%d %d %d %f\n" % remove)
                        else:
                            rejected += 1
                    logger.debug(
                        "Wrote %d new reflections to REMOVE.HKL"
                        % (len(final_remove) - rejected)
                    )
                    logger.debug("Rejected %d as z < %f" % (rejected, z_min))

                # we want to rerun the finishing step so...
                # unless we have added no new reflections... or unless we
                # have not confirmed the point group (see SCI-398)

                if used and self.get_integrater_reindex_matrix():
                    self.set_integrater_finish_done(False)

        else:
            logger.debug(
                "Going quickly so not removing %d outlier reflections..."
                % len(correct.get_remove())
            )

        # Convert INTEGRATE.HKL to MTZ format and reapply any reindexing operations
        # spacegroup changes to allow use with CCP4 / Aimless for scaling

        hklout = os.path.splitext(integrate_hkl)[0] + ".mtz"
        self._factory.set_working_directory(self.get_working_directory())
        pointless = self._factory.Pointless()
        pointless.set_xdsin(integrate_hkl)
        pointless.set_hklout(hklout)
        pointless.xds_to_mtz()

        integrate_mtz = hklout

        if (
            self.get_integrater_reindex_operator()
            or self.get_integrater_spacegroup_number()
        ):

            logger.debug("Reindexing things to MTZ")

            reindex = Reindex()
            reindex.set_working_directory(self.get_working_directory())
            auto_logfiler(reindex)

            if self.get_integrater_reindex_operator():
                reindex.set_operator(self.get_integrater_reindex_operator())

            if self.get_integrater_spacegroup_number():
                reindex.set_spacegroup(self.get_integrater_spacegroup_number())

            hklout = "%s_reindex.mtz" % os.path.splitext(integrate_mtz)[0]

            reindex.set_hklin(integrate_mtz)
            reindex.set_hklout(hklout)
            reindex.reindex()
            integrate_mtz = hklout

        experiments_json = xparm_xds_to_experiments_json(
            self._xds_data_files["GXPARM.XDS"], self.get_working_directory()
        )
        pname, xname, dname = self.get_integrater_project_info()
        sweep = self.get_integrater_sweep_name()
        FileHandler.record_more_data_file(
            f"{pname} {xname} {dname} {sweep}", experiments_json
        )
        FileHandler.record_more_data_file(
            f"{pname} {xname} {dname} {sweep} INTEGRATE", integrate_mtz
        )

        self._intgr_experiments_filename = experiments_json

        return integrate_mtz

    def get_integrated_experiments(self):
        return self._intgr_experiments_filename


def integrate_hkl_to_reflection_file(
    integrate_hkl, experiments_json, working_directory
):
    importer = ImportXDS()
    importer.set_working_directory(working_directory)
    auto_logfiler(importer)
    importer.set_experiments_json(experiments_json)
    importer.set_integrate_hkl(integrate_hkl)
    importer.run()
    return importer.get_reflection_filename()


def xparm_xds_to_experiments_json(xparm_xds, working_directory):
    importer = ImportXDS()
    importer.set_working_directory(working_directory)
    auto_logfiler(importer)
    importer.set_xparm_xds(xparm_xds)
    importer.run()
    return importer.get_experiments_json()
