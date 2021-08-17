# An implementation of the Integrater interface using Dials. This depends on the
# Dials wrappers to actually implement the functionality.


import logging
import math
import os

import xia2.Wrappers.Dials.Integrate
from dxtbx.serialize import load
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import auto_logfiler
from xia2.lib.SymmetryLib import lattice_to_spacegroup
from xia2.Schema.Interfaces.Integrater import Integrater
from xia2.Wrappers.Dials.anvil_correction import anvil_correction as _anvil_correction
from xia2.Wrappers.Dials.ExportMtz import ExportMtz as _ExportMtz
from xia2.Wrappers.Dials.ExportXDSASCII import ExportXDSASCII
from xia2.Wrappers.Dials.Report import Report as _Report

logger = logging.getLogger("xia2.Modules.Integrater.DialsIntegrater")


class DialsIntegrater(Integrater):
    """A class to implement the Integrater interface using *only* DIALS
    programs."""

    def __init__(self):
        super().__init__()

        # check that the programs exist - this will raise an exception if
        # they do not...

        xia2.Wrappers.Dials.Integrate.Integrate()

        # place to store working data
        self._data_files = {}

        # internal parameters to pass around
        self._integrate_parameters = {}
        self._intgr_integrated_filename = None

        self._intgr_integrated_reflections = None
        self._intgr_experiments_filename = None

        # Check whether to do diamond anvil cell attenuation correction.
        self.high_pressure = PhilIndex.params.dials.high_pressure.correction

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

    # admin functions

    def get_integrated_experiments(self):
        self.integrate()
        return self._intgr_experiments_filename

    def get_integrated_filename(self):
        self.integrate()
        return self._intgr_integrated_filename

    def get_integrated_reflections(self):
        self.integrate()
        return self._intgr_integrated_reflections

    def set_integrated_experiments(self, filename):
        Integrater.set_integrated_experiments = filename

    def set_integrated_reflections(self, filename):
        Integrater.set_integrated_reflections = filename

    # factory functions

    def Integrate(self):
        params = PhilIndex.params.dials.integrate
        integrate = xia2.Wrappers.Dials.Integrate.Integrate()
        integrate.set_phil_file(params.phil_file)

        if params.mosaic == "new":
            integrate.set_new_mosaic()

        if PhilIndex.params.dials.fast_mode:
            integrate.set_profile_fitting(False)
        else:
            profile_fitting = PhilIndex.params.xia2.settings.integration.profile_fitting
            integrate.set_profile_fitting(profile_fitting)

        # Options for profile modelling.
        integrate.set_scan_varying_profile(params.scan_varying_profile)

        high_pressure = PhilIndex.params.dials.high_pressure.correction
        integrate.set_profile_params(
            params.min_spots.per_degree, params.min_spots.overall, high_pressure
        )

        integrate.set_background_outlier_algorithm(params.background_outlier_algorithm)
        integrate.set_background_algorithm(params.background_algorithm)
        integrate.set_working_directory(self.get_working_directory())

        integrate.set_experiments_filename(self._intgr_experiments_filename)

        integrate.set_reflections_filename(self._intgr_indexed_filename)

        auto_logfiler(integrate, "INTEGRATE")

        return integrate

    def Report(self):
        report = _Report()
        report.set_working_directory(self.get_working_directory())
        report.set_experiments_filename(self._intgr_experiments_filename)
        report.set_reflections_filename(self._intgr_integrated_reflections)
        auto_logfiler(report, "REPORT")
        return report

    def ExportMtz(self):
        params = PhilIndex.params.dials.integrate
        export = _ExportMtz()
        pname, xname, _ = self.get_integrater_project_info()
        export.crystal_name = xname
        export.project_name = pname
        export.set_working_directory(self.get_working_directory())

        export.set_experiments_filename(self._intgr_experiments_filename)
        export.set_combine_partials(params.combine_partials)
        export.set_partiality_threshold(params.partiality_threshold)
        if len(self.get_matching_images()) == 1:
            export.set_partiality_threshold(0.1)
        if (
            len(self.get_matching_images()) == 1
            or PhilIndex.params.dials.fast_mode
            or not PhilIndex.params.xia2.settings.integration.profile_fitting
        ):
            # With no profiles available have to rely on summation alone
            export.set_intensity_choice("sum")

        auto_logfiler(export, "EXPORTMTZ")

        return export

    # now some real functions, which do useful things

    def _integrater_reset_callback(self):
        """Delete all results on a reset."""
        logger.debug("Deleting all stored results.")
        self._data_files = {}
        self._integrate_parameters = {}

    def _integrate_prepare(self):
        """Prepare for integration - in XDS terms this may mean rerunning
        IDXREF to get the XPARM etc. DEFPIX is considered part of the full
        integration as it is resolution dependent."""

        Citations.cite("dials")

        # decide what images we are going to process, if not already
        # specified
        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images), max(images))

        logger.debug("DIALS INTEGRATE PREPARE:")
        logger.debug("Wavelength: %.6f" % self.get_wavelength())
        logger.debug("Distance: %.2f" % self.get_distance())

        if not self.get_integrater_low_resolution():

            dmax = self._intgr_refiner.get_indexer_low_resolution(
                self.get_integrater_epoch()
            )
            self.set_integrater_low_resolution(dmax)

            logger.debug(
                "Low resolution set to: %s" % self.get_integrater_low_resolution()
            )

        ## copy the data across
        refiner = self.get_integrater_refiner()
        # For multi-sweep refinement, get the split experiments from after refinement.
        if PhilIndex.params.xia2.settings.multi_sweep_refinement:
            self._intgr_experiments_filename = refiner.get_refiner_payload(
                f"{self._intgr_sweep._name}_models.expt"
            )
            self._intgr_indexed_filename = refiner.get_refiner_payload(
                f"{self._intgr_sweep._name}_observations.refl"
            )
        # Otherwise, there should only be a single experiment list and reflection table.
        else:
            self._intgr_experiments_filename = refiner.get_refiner_payload(
                "models.expt"
            )
            self._intgr_indexed_filename = refiner.get_refiner_payload(
                "observations.refl"
            )
        experiments = load.experiment_list(self._intgr_experiments_filename)
        experiment = experiments[0]

        # this is the result of the cell refinement
        self._intgr_cell = experiment.crystal.get_unit_cell().parameters()

        logger.debug("Files available at the end of DIALS integrate prepare:")
        for f in self._data_files:
            logger.debug("%s" % f)

        self.set_detector(experiment.detector)
        self.set_beam_obj(experiment.beam)
        self.set_goniometer(experiment.goniometer)

    def _integrate(self):
        """Actually do the integration - in XDS terms this will mean running
        DEFPIX and INTEGRATE to measure all the reflections."""

        integrate = self.Integrate()

        # decide what images we are going to process, if not already
        # specified

        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images), max(images))

        imageset = self.get_imageset()
        beam = imageset.get_beam()
        detector = imageset.get_detector()

        d_min_limit = detector.get_max_resolution(beam.get_s0())
        if (
            d_min_limit > self._intgr_reso_high
            or PhilIndex.params.xia2.settings.resolution.keep_all_reflections
        ):
            logger.debug(
                "Overriding high resolution limit: %f => %f"
                % (self._intgr_reso_high, d_min_limit)
            )
            self._intgr_reso_high = d_min_limit

        integrate.set_experiments_filename(self._intgr_experiments_filename)
        integrate.set_reflections_filename(self._intgr_indexed_filename)
        if PhilIndex.params.dials.integrate.d_max:
            integrate.set_d_max(PhilIndex.params.dials.integrate.d_max)
        else:
            integrate.set_d_max(self._intgr_reso_low)
        if PhilIndex.params.dials.integrate.d_min:
            integrate.set_d_min(PhilIndex.params.dials.integrate.d_min)
        else:
            integrate.set_d_min(self._intgr_reso_high)

        pname, xname, dname = self.get_integrater_project_info()
        sweep = self.get_integrater_sweep_name()
        FileHandler.record_log_file(
            f"{pname} {xname} {dname} {sweep} INTEGRATE",
            integrate.get_log_file(),
        )

        integrate.run()

        self._intgr_experiments_filename = integrate.get_integrated_experiments()

        # also record the batch range - needed for the analysis of the
        # radiation damage in chef...

        self._intgr_batches_out = (self._intgr_wedge[0], self._intgr_wedge[1])

        # FIXME (i) record the log file, (ii) get more information out from the
        # integration log on the quality of the data and (iii) the mosaic spread
        # range observed and R.M.S. deviations.

        self._intgr_integrated_reflections = integrate.get_integrated_reflections()
        if not os.path.isfile(self._intgr_integrated_reflections):
            raise RuntimeError(
                "Integration failed: %s does not exist."
                % self._intgr_integrated_reflections
            )

        self._intgr_per_image_statistics = integrate.get_per_image_statistics()
        logger.info(self.show_per_image_statistics())

        report = self.Report()
        html_filename = os.path.join(
            self.get_working_directory(),
            "%i_dials.integrate.report.html" % report.get_xpid(),
        )
        report.set_html_filename(html_filename)
        report.run(wait_for_completion=True)
        FileHandler.record_html_file(
            f"{pname} {xname} {dname} {sweep} INTEGRATE", html_filename
        )

        experiments = load.experiment_list(self._intgr_experiments_filename)
        profile = experiments.profiles()[0]
        mosaic = profile.sigma_m()
        try:
            m_min, m_max, m_mean = mosaic.min_max_mean().as_tuple()
            self.set_integrater_mosaic_min_mean_max(m_min, m_mean, m_max)
        except AttributeError:
            self.set_integrater_mosaic_min_mean_max(mosaic, mosaic, mosaic)

        logger.info(
            "Mosaic spread: %.3f < %.3f < %.3f"
            % self.get_integrater_mosaic_min_mean_max()
        )

        # If running in high-pressure mode, run dials.anvil_correction to
        # correct for the attenuation of the incident and diffracted beams by the
        # diamond anvils.
        if self.high_pressure:
            self._anvil_correction()

        return self._intgr_integrated_reflections

    def _integrate_finish(self):
        """
        Finish off the integration.

        If in high-pressure mode run dials.anvil_correction.

        Run dials.export.
        """

        # FIXME - do we want to export every time we call this method
        # (the file will not have changed) and also (more important) do
        # we want a different exported MTZ file every time (I do not think
        # that we do; these can be very large) - was exporter.get_xpid() ->
        # now dials

        if self._output_format == "hkl":
            exporter = self.ExportMtz()
            exporter.set_reflections_filename(self._intgr_integrated_reflections)
            mtz_filename = os.path.join(
                self.get_working_directory(), "%s_integrated.mtz" % "dials"
            )
            exporter.set_mtz_filename(mtz_filename)
            exporter.run()
            self._intgr_integrated_filename = mtz_filename

            # record integrated MTZ file
            pname, xname, dname = self.get_integrater_project_info()
            sweep = self.get_integrater_sweep_name()
            FileHandler.record_more_data_file(
                f"{pname} {xname} {dname} {sweep} INTEGRATE", mtz_filename
            )

            from iotbx.reflection_file_reader import any_reflection_file

            miller_arrays = any_reflection_file(
                self._intgr_integrated_filename
            ).as_miller_arrays()
            # look for profile-fitted intensities
            intensities = [
                ma for ma in miller_arrays if ma.info().labels == ["IPR", "SIGIPR"]
            ]
            if len(intensities) == 0:
                # look instead for summation-integrated intensities
                intensities = [
                    ma for ma in miller_arrays if ma.info().labels == ["I", "SIGI"]
                ]
                assert len(intensities)
            self._intgr_n_ref = intensities[0].size()

            if not os.path.isfile(self._intgr_integrated_filename):
                raise RuntimeError(
                    "dials.export failed: %s does not exist."
                    % self._intgr_integrated_filename
                )

            if (
                self._intgr_reindex_operator is None
                and self._intgr_spacegroup_number
                == lattice_to_spacegroup(
                    self.get_integrater_refiner().get_refiner_lattice()
                )
            ):
                logger.debug(
                    "Not reindexing to spacegroup %d (%s)"
                    % (self._intgr_spacegroup_number, self._intgr_reindex_operator)
                )
                return mtz_filename

            if (
                self._intgr_reindex_operator is None
                and self._intgr_spacegroup_number == 0
            ):
                logger.debug(
                    "Not reindexing to spacegroup %d (%s)"
                    % (self._intgr_spacegroup_number, self._intgr_reindex_operator)
                )
                return mtz_filename

            logger.debug(
                "Reindexing to spacegroup %d (%s)"
                % (self._intgr_spacegroup_number, self._intgr_reindex_operator)
            )

            hklin = mtz_filename
            from xia2.Wrappers.CCP4.Reindex import Reindex

            reindex = Reindex()
            reindex.set_working_directory(self.get_working_directory())
            auto_logfiler(reindex)

            reindex.set_operator(self._intgr_reindex_operator)

            if self._intgr_spacegroup_number:
                reindex.set_spacegroup(self._intgr_spacegroup_number)
            else:
                reindex.set_spacegroup(
                    lattice_to_spacegroup(
                        self.get_integrater_refiner().get_refiner_lattice()
                    )
                )

            hklout = "%s_reindex.mtz" % hklin[:-4]
            reindex.set_hklin(hklin)
            reindex.set_hklout(hklout)
            reindex.reindex()
            self._intgr_integrated_filename = hklout
            self._intgr_cell = reindex.get_cell()

            pname, xname, dname = self.get_integrater_project_info()
            sweep = self.get_integrater_sweep_name()
            FileHandler.record_more_data_file(
                f"{pname} {xname} {dname} {sweep}",
                self.get_integrated_experiments(),
            )
            FileHandler.record_more_data_file(
                f"{pname} {xname} {dname} {sweep}",
                self.get_integrated_reflections(),
            )

            return hklout

        elif self._output_format == "pickle":

            if (
                self._intgr_reindex_operator is None
                and self._intgr_spacegroup_number
                == lattice_to_spacegroup(
                    self.get_integrater_refiner().get_refiner_lattice()
                )
            ):
                logger.debug(
                    "Not reindexing to spacegroup %d (%s)"
                    % (self._intgr_spacegroup_number, self._intgr_reindex_operator)
                )
                return self._intgr_integrated_reflections

            if (
                self._intgr_reindex_operator is None
                and self._intgr_spacegroup_number == 0
            ):
                logger.debug(
                    "Not reindexing to spacegroup %d (%s)"
                    % (self._intgr_spacegroup_number, self._intgr_reindex_operator)
                )
                return self._intgr_integrated_reflections

            logger.debug(
                "Reindexing to spacegroup %d (%s)"
                % (self._intgr_spacegroup_number, self._intgr_reindex_operator)
            )
            from xia2.Wrappers.Dials.Reindex import Reindex

            reindex = Reindex()
            reindex.set_working_directory(self.get_working_directory())
            auto_logfiler(reindex)

            reindex.set_cb_op(self._intgr_reindex_operator)

            if self._intgr_spacegroup_number:
                reindex.set_space_group(self._intgr_spacegroup_number)
            else:
                reindex.set_space_group(
                    lattice_to_spacegroup(
                        self.get_integrater_refiner().get_refiner_lattice()
                    )
                )

            reindex.set_experiments_filename(self.get_integrated_experiments())
            reindex.set_indexed_filename(self.get_integrated_reflections())

            reindex.run()
            self._intgr_integrated_reflections = (
                reindex.get_reindexed_reflections_filename()
            )
            self._intgr_integrated_filename = (
                reindex.get_reindexed_reflections_filename()
            )
            self._intgr_experiments_filename = (
                reindex.get_reindexed_experiments_filename()
            )

            pname, xname, dname = self.get_integrater_project_info()
            sweep = self.get_integrater_sweep_name()
            FileHandler.record_more_data_file(
                f"{pname} {xname} {dname} {sweep}",
                self.get_integrated_experiments(),
            )
            FileHandler.record_more_data_file(
                f"{pname} {xname} {dname} {sweep}",
                self.get_integrated_reflections(),
            )
            return None  # this will be set to intgr_hklout - better to cause failure
            # due to it being none than it be set wrong and not knowing?

    def _integrate_select_images_wedges(self):
        """Select correct images based on image headers."""

        phi_width = self.get_phi_width()

        images = self.get_matching_images()

        # characterise the images - are there just two (e.g. dna-style
        # reference images) or is there a full block?

        wedges = []

        if len(images) < 3:
            # work on the assumption that this is a reference pair

            wedges.append(images[0])

            if len(images) > 1:
                wedges.append(images[1])

        else:
            block_size = min(len(images), int(math.ceil(5 / phi_width)))

            logger.debug(
                "Adding images for indexer: %d -> %d"
                % (images[0], images[block_size - 1])
            )

            wedges.append((images[0], images[block_size - 1]))

            if int(90.0 / phi_width) + block_size in images:
                # assume we can add a wedge around 45 degrees as well...
                logger.debug(
                    "Adding images for indexer: %d -> %d"
                    % (
                        int(45.0 / phi_width) + images[0],
                        int(45.0 / phi_width) + images[0] + block_size - 1,
                    )
                )
                logger.debug(
                    "Adding images for indexer: %d -> %d"
                    % (
                        int(90.0 / phi_width) + images[0],
                        int(90.0 / phi_width) + images[0] + block_size - 1,
                    )
                )
                wedges.append(
                    (
                        int(45.0 / phi_width) + images[0],
                        int(45.0 / phi_width) + images[0] + block_size - 1,
                    )
                )
                wedges.append(
                    (
                        int(90.0 / phi_width) + images[0],
                        int(90.0 / phi_width) + images[0] + block_size - 1,
                    )
                )

            else:

                # add some half-way anyway
                first = (len(images) // 2) - (block_size // 2) + images[0] - 1
                if first > wedges[0][1]:
                    last = first + block_size - 1
                    logger.debug("Adding images for indexer: %d -> %d" % (first, last))
                    wedges.append((first, last))
                if len(images) > block_size:
                    logger.debug(
                        "Adding images for indexer: %d -> %d"
                        % (images[-block_size], images[-1])
                    )
                    wedges.append((images[-block_size], images[-1]))

        return wedges

    def get_integrater_corrected_intensities(self):
        self.integrate()

        exporter = ExportXDSASCII()
        exporter.set_experiments_filename(self.get_integrated_experiments())
        exporter.set_reflections_filename(self.get_integrated_reflections())
        exporter.set_working_directory(self.get_working_directory())
        auto_logfiler(exporter)
        self._intgr_corrected_hklout = os.path.join(
            self.get_working_directory(), "%i_DIALS.HKL" % exporter.get_xpid()
        )
        exporter.set_hkl_filename(self._intgr_corrected_hklout)
        exporter.run()
        assert os.path.exists(self._intgr_corrected_hklout)
        return self._intgr_corrected_hklout

    def _anvil_correction(self):
        """Correct for attenuation in a diamond anvil pressure cell."""

        logger.info(
            "Rescaling integrated reflections for attenuation in the diamond anvil "
            "cell."
        )

        params = PhilIndex.params.dials.high_pressure
        anvil_correct = _anvil_correction()

        # Take the filenames of the last integration step as input.
        anvil_correct.experiments_filenames.append(self._intgr_experiments_filename)
        anvil_correct.reflections_filenames.append(self._intgr_integrated_reflections)

        # The output reflections have a filename appended with '_corrected'.
        output_reflections = "_corrected".join(
            os.path.splitext(self._intgr_integrated_reflections)
        )
        anvil_correct.output_reflections_filename = output_reflections

        # Set the user-specified parameters from the PHIL scope.
        anvil_correct.density = params.anvil.density
        anvil_correct.thickness = params.anvil.thickness
        anvil_correct.normal = params.anvil.normal

        # Run dials.anvil_correction with the parameters as set above.
        anvil_correct.set_working_directory(self.get_working_directory())
        auto_logfiler(anvil_correct)
        anvil_correct.run()
        self._intgr_integrated_reflections = output_reflections
