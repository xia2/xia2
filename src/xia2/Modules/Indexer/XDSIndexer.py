# An implementation of the Indexer interface using XDS. This depends on the
# XDS wrappers to actually implement the functionality.


import logging
import os
import math
import shutil

from cctbx.array_family import flex
from scitbx import matrix

# wrappers for programs that this needs

from xia2.Wrappers.XDS.XDSXycorr import XDSXycorr as _Xycorr
from xia2.Wrappers.XDS.XDSInit import XDSInit as _Init
from xia2.Wrappers.XDS.XDSColspot import XDSColspot as _Colspot
from xia2.Wrappers.XDS.XDSIdxref import XDSIdxref as _Idxref

# helper functions

from xia2.Wrappers.XDS.XDS import XDSException
from xia2.Modules.Indexer.XDSCheckIndexerSolution import xds_check_indexer_solution

# interfaces that this must implement to be an indexer

from xia2.Schema.Interfaces.Indexer import IndexerSingleSweep

# odds and sods that are needed

from xia2.lib.bits import auto_logfiler
from xia2.Handlers.Flags import Flags
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Files import FileHandler
from xia2.Wrappers.Dials.Spotfinder import Spotfinder
from xia2.Wrappers.Dials.ExportSpotXDS import ExportSpotXDS
from dxtbx.serialize.xds import to_xds
import dxtbx
from dxtbx.model import Experiment, ExperimentList
from iotbx.xds import spot_xds
from dxtbx.serialize.xds import to_crystal

logger = logging.getLogger("xia2.Modules.Indexer.XDSIndexer")


class XDSIndexer(IndexerSingleSweep):
    """An implementation of the Indexer interface using XDS."""

    def __init__(self):
        super().__init__()

        # check that the programs exist - this will raise an exception if
        # they do not...

        _Idxref()

        self._background_images = None
        self._index_select_images = "i"

        # place to store working data
        self._data_files = {}

    # factory functions

    def Xycorr(self):
        xycorr = _Xycorr()
        xycorr.set_working_directory(self.get_working_directory())

        xycorr.setup_from_imageset(self.get_imageset())

        if self.get_distance():
            xycorr.set_distance(self.get_distance())

        if self.get_wavelength():
            xycorr.set_wavelength(self.get_wavelength())

        auto_logfiler(xycorr, "XYCORR")

        return xycorr

    def Init(self):
        init = _Init(params=PhilIndex.params.xds.init)
        init.set_working_directory(self.get_working_directory())

        init.setup_from_imageset(self.get_imageset())

        if self.get_distance():
            init.set_distance(self.get_distance())

        if self.get_wavelength():
            init.set_wavelength(self.get_wavelength())

        auto_logfiler(init, "INIT")

        return init

    def Colspot(self):
        colspot = _Colspot(params=PhilIndex.params.xds.colspot)
        colspot.set_working_directory(self.get_working_directory())

        colspot.setup_from_imageset(self.get_imageset())

        if self.get_distance():
            colspot.set_distance(self.get_distance())

        if self.get_wavelength():
            colspot.set_wavelength(self.get_wavelength())

        auto_logfiler(colspot, "COLSPOT")

        return colspot

    def DialsSpotfinder(self):
        spotfinder = Spotfinder(params=PhilIndex.params.dials.find_spots)
        spotfinder.set_working_directory(self.get_working_directory())
        spotfinder.setup_from_imageset(self.get_imageset())

        auto_logfiler(spotfinder, "SPOTFINDER")

        return spotfinder

    def DialsExportSpotXDS(self):
        export = ExportSpotXDS()
        export.set_working_directory(self.get_working_directory())
        return export

    def Idxref(self):
        idxref = _Idxref(params=PhilIndex.params.xds.index)
        idxref.set_working_directory(self.get_working_directory())

        idxref.setup_from_imageset(self.get_imageset())

        if self.get_distance():
            idxref.set_distance(self.get_distance())

        if self.get_wavelength():
            idxref.set_wavelength(self.get_wavelength())

        # if we have a refined set of parameters to apply, apply these
        if Flags.get_xparm():
            idxref.set_refined_origin(Flags.get_xparm_origin())
            idxref.set_refined_beam_vector(Flags.get_xparm_beam_vector())
            idxref.set_refined_rotation_axis(Flags.get_xparm_rotation_axis())
            idxref.set_refined_distance(Flags.get_xparm_distance())

        # hacks for Jira 493

        if Flags.get_xparm_a():
            idxref.set_a_axis(Flags.get_xparm_a())
        if Flags.get_xparm_b():
            idxref.set_b_axis(Flags.get_xparm_b())
        if Flags.get_xparm_c():
            idxref.set_c_axis(Flags.get_xparm_c())

        auto_logfiler(idxref, "IDXREF")

        return idxref

    # helper functions

    def _index_remove_masked_regions(self):
        if not PhilIndex.params.xia2.settings.untrusted_rectangle_indexing:
            return

        untrusted_rectangle_indexing = (
            PhilIndex.params.xia2.settings.untrusted_rectangle_indexing
        )
        spot_xds = []
        removed = 0
        lines = open(self._indxr_payload["SPOT.XDS"], "rb").readlines()
        for record in lines:
            if not record.strip():
                continue
            remove = False
            x, y, phi, i = list(map(float, record.split()[:4]))
            for limits in untrusted_rectangle_indexing:
                if x > limits[0] and x < limits[1] and y > limits[2] and y < limits[3]:
                    removed += 1
                    remove = True
                    break

            if not remove:
                spot_xds.append("%s" % record)

        logger.debug("Removed %d peaks from SPOT.XDS", removed)
        masked_spot_xds = (
            os.path.splitext(self._indxr_payload["SPOT.XDS"])[0] + "_masked.XDS"
        )
        with open(masked_spot_xds, "w") as f:
            f.writelines(spot_xds)
        self._indxr_payload["SPOT.XDS"] = masked_spot_xds

    def _index_select_images_i(self):
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
            max_wedge_size_degrees = PhilIndex.params.xds.index.max_wedge_size_degrees
            max_wedge_size = PhilIndex.params.xds.index.max_wedge_size
            if max_wedge_size_degrees is not None:
                n = int(math.floor(max_wedge_size_degrees / self.get_phi_width()))
                if max_wedge_size is not None:
                    max_wedge_size = min(max_wedge_size, max(n, 1))
                else:
                    max_wedge_size = n

            logger.debug("Using max_wedge_size: %d", max_wedge_size)

            block_size = min(len(images), max_wedge_size)

            logger.debug(
                "Adding images for indexer: %d -> %d", images[0], images[block_size - 1]
            )

            wedges.append((images[0], images[block_size - 1]))

            if int(90.0 / phi_width) + block_size in images:
                # assume we can add a wedge around 45 degrees as well...
                logger.debug(
                    "Adding images for indexer: %d -> %d",
                    int(45.0 / phi_width) + images[0],
                    int(45.0 / phi_width) + images[0] + block_size - 1,
                )
                logger.debug(
                    "Adding images for indexer: %d -> %d",
                    int(90.0 / phi_width) + images[0],
                    int(90.0 / phi_width) + images[0] + block_size - 1,
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
                    logger.debug("Adding images for indexer: %d -> %d", first, last)
                    wedges.append((first, last))
                if len(images) > block_size:
                    logger.debug(
                        "Adding images for indexer: %d -> %d",
                        images[-block_size],
                        images[-1],
                    )
                    wedges.append((images[-block_size], images[-1]))

        return wedges

    # do-er functions

    def _index_prepare(self):
        """Prepare to do autoindexing - in XDS terms this will mean
        calling xycorr, init and colspot on the input images."""

        # decide on images to work with

        logger.debug("XDS INDEX PREPARE:")
        logger.debug("Wavelength: %.6f", self.get_wavelength())
        logger.debug("Distance: %.2f", self.get_distance())

        if self._indxr_images == []:
            _select_images_function = getattr(
                self, "_index_select_images_%s" % self._index_select_images
            )
            wedges = _select_images_function()
            for wedge in wedges:
                self.add_indexer_image_wedge(wedge)
            self.set_indexer_prepare_done(True)

        all_images = self.get_matching_images()

        first = min(all_images)
        last = max(all_images)

        # next start to process these - first xycorr

        xycorr = self.Xycorr()

        xycorr.set_data_range(first, last)
        xycorr.set_background_range(self._indxr_images[0][0], self._indxr_images[0][1])

        converter = to_xds(self.get_imageset())
        xds_beam_centre = converter.detector_origin
        xycorr.set_beam_centre(xds_beam_centre[0], xds_beam_centre[1])
        for block in self._indxr_images:
            xycorr.add_spot_range(block[0], block[1])

        # FIXME need to set the origin here

        xycorr.run()

        for file in ["X-CORRECTIONS.cbf", "Y-CORRECTIONS.cbf"]:
            self._indxr_payload[file] = xycorr.get_output_data_file(file)

        # next start to process these - then init

        if PhilIndex.params.xia2.settings.input.format.dynamic_shadowing:
            imageset = self._indxr_imagesets[0]
            masker = (
                imageset.get_format_class()
                .get_instance(imageset.paths()[0])
                .get_masker()
            )
            if masker is None:
                # disable dynamic_shadowing
                PhilIndex.params.xia2.settings.input.format.dynamic_shadowing = False

        if PhilIndex.params.xia2.settings.input.format.dynamic_shadowing:
            # find the region of the scan with the least predicted shadow
            # to use for background determination in XDS INIT step
            from dxtbx.model.experiment_list import ExperimentListFactory

            imageset = self._indxr_imagesets[0]
            xsweep = self._indxr_sweeps[0]
            sweep_filename = os.path.join(
                self.get_working_directory(), "%s_indexed.expt" % xsweep.get_name()
            )
            ExperimentListFactory.from_imageset_and_crystal(imageset, None).as_file(
                sweep_filename
            )

            from xia2.Wrappers.Dials.ShadowPlot import ShadowPlot

            shadow_plot = ShadowPlot()
            shadow_plot.set_working_directory(self.get_working_directory())
            auto_logfiler(shadow_plot)
            shadow_plot.set_sweep_filename(sweep_filename)
            shadow_plot.set_json_filename(
                os.path.join(
                    self.get_working_directory(),
                    "%s_shadow_plot.json" % shadow_plot.get_xpid(),
                )
            )
            shadow_plot.run()
            results = shadow_plot.get_results()

            fraction_shadowed = flex.double(results["fraction_shadowed"])
            if flex.max(fraction_shadowed) == 0:
                PhilIndex.params.xia2.settings.input.format.dynamic_shadowing = False
            else:
                scan_points = flex.double(results["scan_points"])

                scan = imageset.get_scan()
                oscillation = scan.get_oscillation()

                if self._background_images is not None:
                    bg_images = self._background_images
                    bg_range_deg = (
                        scan.get_angle_from_image_index(bg_images[0]),
                        scan.get_angle_from_image_index(bg_images[1]),
                    )
                    bg_range_width = bg_range_deg[1] - bg_range_deg[0]

                    min_shadow = 100
                    best_bg_range = bg_range_deg
                    from libtbx.utils import frange

                    for bg_range_start in frange(
                        flex.min(scan_points),
                        flex.max(scan_points) - bg_range_width,
                        step=oscillation[1],
                    ):
                        bg_range_deg = (bg_range_start, bg_range_start + bg_range_width)
                        sel = (scan_points >= bg_range_deg[0]) & (
                            scan_points <= bg_range_deg[1]
                        )
                        mean_shadow = flex.mean(fraction_shadowed.select(sel))
                        if mean_shadow < min_shadow:
                            min_shadow = mean_shadow
                            best_bg_range = bg_range_deg

                    self._background_images = (
                        scan.get_image_index_from_angle(best_bg_range[0]),
                        scan.get_image_index_from_angle(best_bg_range[1]),
                    )
                    logger.debug(
                        "Setting background images: %s -> %s" % self._background_images
                    )

        init = self.Init()

        for file in ["X-CORRECTIONS.cbf", "Y-CORRECTIONS.cbf"]:
            init.set_input_data_file(file, self._indxr_payload[file])

        init.set_data_range(first, last)

        if self._background_images:
            init.set_background_range(
                self._background_images[0], self._background_images[1]
            )
        else:
            init.set_background_range(
                self._indxr_images[0][0], self._indxr_images[0][1]
            )

        for block in self._indxr_images:
            init.add_spot_range(block[0], block[1])

        init.run()

        # at this stage, need to (perhaps) modify the BKGINIT.cbf image
        # to mark out the back stop

        if PhilIndex.params.xds.backstop_mask:
            logger.debug("Applying mask to BKGINIT.pck")

            # copy the original file
            cbf_old = os.path.join(init.get_working_directory(), "BKGINIT.cbf")
            cbf_save = os.path.join(init.get_working_directory(), "BKGINIT.sav")
            shutil.copyfile(cbf_old, cbf_save)

            # modify the file to give the new mask
            from xia2.Toolkit.BackstopMask import BackstopMask

            mask = BackstopMask(PhilIndex.params.xds.backstop_mask)
            mask.apply_mask_xds(self.get_header(), cbf_save, cbf_old)

            init.reload()

        for file in ["BLANK.cbf", "BKGINIT.cbf", "GAIN.cbf"]:
            self._indxr_payload[file] = init.get_output_data_file(file)

        if PhilIndex.params.xia2.settings.developmental.use_dials_spotfinder:

            spotfinder = self.DialsSpotfinder()

            for block in self._indxr_images:
                spotfinder.add_spot_range(block[0], block[1])

            spotfinder.run()
            export = self.DialsExportSpotXDS()
            export.set_input_data_file(
                "observations.refl",
                spotfinder.get_output_data_file("observations.refl"),
            )
            export.run()

            for file in ["SPOT.XDS"]:
                self._indxr_payload[file] = export.get_output_data_file(file)

        else:

            # next start to process these - then colspot

            colspot = self.Colspot()

            for file in (
                "X-CORRECTIONS.cbf",
                "Y-CORRECTIONS.cbf",
                "BLANK.cbf",
                "BKGINIT.cbf",
                "GAIN.cbf",
            ):
                colspot.set_input_data_file(file, self._indxr_payload[file])

            colspot.set_data_range(first, last)
            colspot.set_background_range(
                self._indxr_images[0][0], self._indxr_images[0][1]
            )
            for block in self._indxr_images:
                colspot.add_spot_range(block[0], block[1])

            colspot.run()

            for file in ["SPOT.XDS"]:
                self._indxr_payload[file] = colspot.get_output_data_file(file)

        # that should be everything prepared... all of the important
        # files should be loaded into memory to be able to cope with
        # integration happening somewhere else

    def _index(self):
        """Actually do the autoindexing using the data prepared by the
        previous method."""

        idxref = self.Idxref()

        self._index_remove_masked_regions()
        for file in ["SPOT.XDS"]:
            idxref.set_input_data_file(file, self._indxr_payload[file])

        # edit SPOT.XDS to remove reflections in untrusted regions of the detector

        idxref.set_data_range(self._indxr_images[0][0], self._indxr_images[0][1])
        idxref.set_background_range(self._indxr_images[0][0], self._indxr_images[0][1])

        # set the phi start etc correctly

        for block in self._indxr_images[:1]:
            starting_frame = block[0]
            starting_angle = self.get_scan().get_angle_from_image_index(starting_frame)

            idxref.set_starting_frame(starting_frame)
            idxref.set_starting_angle(starting_angle)

            idxref.add_spot_range(block[0], block[1])

        for block in self._indxr_images[1:]:
            idxref.add_spot_range(block[0], block[1])

        if self._indxr_user_input_lattice:
            idxref.set_indexer_user_input_lattice(True)

        if self._indxr_input_lattice and self._indxr_input_cell:
            idxref.set_indexer_input_lattice(self._indxr_input_lattice)
            idxref.set_indexer_input_cell(self._indxr_input_cell)

            logger.debug("Set lattice: %s", self._indxr_input_lattice)
            logger.debug("Set cell: %f %f %f %f %f %f" % self._indxr_input_cell)

            original_cell = self._indxr_input_cell
        elif self._indxr_input_lattice:
            idxref.set_indexer_input_lattice(self._indxr_input_lattice)
            original_cell = None
        else:
            original_cell = None

        converter = to_xds(self.get_imageset())
        xds_beam_centre = converter.detector_origin

        idxref.set_beam_centre(xds_beam_centre[0], xds_beam_centre[1])

        # fixme need to check if the lattice, cell have been set already,
        # and if they have, pass these in as input to the indexing job.

        done = False

        while not done:
            try:
                done = idxref.run()

                # N.B. in here if the IDXREF step was being run in the first
                # pass done is FALSE however there should be a refined
                # P1 orientation matrix etc. available - so keep it!

            except XDSException as e:
                # inspect this - if we have complaints about not
                # enough reflections indexed, and we have a target
                # unit cell, and they are the same, well ignore it

                if "solution is inaccurate" in str(e):
                    logger.debug("XDS complains solution inaccurate - ignoring")
                    done = idxref.continue_from_error()
                elif (
                    "insufficient percentage (< 70%)" in str(e)
                    or "insufficient percentage (< 50%)" in str(e)
                ) and original_cell:
                    done = idxref.continue_from_error()
                    lattice, cell, mosaic = idxref.get_indexing_solution()
                    # compare solutions FIXME should use xds_cell_deviation
                    check = PhilIndex.params.xia2.settings.xds_check_cell_deviation
                    for j in range(3):
                        # allow two percent variation in unit cell length
                        if (
                            math.fabs((cell[j] - original_cell[j]) / original_cell[j])
                            > 0.02
                            and check
                        ):
                            logger.debug("XDS unhappy and solution wrong")
                            raise e
                        # and two degree difference in angle
                        if (
                            math.fabs(cell[j + 3] - original_cell[j + 3]) > 2.0
                            and check
                        ):
                            logger.debug("XDS unhappy and solution wrong")
                            raise e
                    logger.debug("XDS unhappy but solution ok")
                elif "insufficient percentage (< 70%)" in str(
                    e
                ) or "insufficient percentage (< 50%)" in str(e):
                    logger.debug("XDS unhappy but solution probably ok")
                    done = idxref.continue_from_error()
                else:
                    raise e

        FileHandler.record_log_file(
            "%s INDEX" % self.get_indexer_full_name(),
            os.path.join(self.get_working_directory(), "IDXREF.LP"),
        )

        for file in ["SPOT.XDS", "XPARM.XDS"]:
            self._indxr_payload[file] = idxref.get_output_data_file(file)

        # need to get the indexing solutions out somehow...

        self._indxr_other_lattice_cell = idxref.get_indexing_solutions()

        (
            self._indxr_lattice,
            self._indxr_cell,
            self._indxr_mosaic,
        ) = idxref.get_indexing_solution()

        xparm_file = os.path.join(self.get_working_directory(), "XPARM.XDS")
        models = dxtbx.load(xparm_file)
        crystal_model = to_crystal(xparm_file)

        # this information gets lost when re-creating the models from the
        # XDS results - however is not refined so can simply copy from the
        # input - https://github.com/xia2/xia2/issues/372
        models.get_detector()[0].set_thickness(
            converter.get_detector()[0].get_thickness()
        )

        experiment = Experiment(
            beam=models.get_beam(),
            detector=models.get_detector(),
            goniometer=models.get_goniometer(),
            scan=models.get_scan(),
            crystal=crystal_model,
            # imageset=self.get_imageset(),
        )

        experiment_list = ExperimentList([experiment])
        self.set_indexer_experiment_list(experiment_list)

        # I will want this later on to check that the lattice was ok
        self._idxref_subtree_problem = idxref.get_index_tree_problem()

    def _index_finish(self):
        """Perform the indexer post-processing as required."""

        # ok, in here now ask if this solution was sensible!

        if not self.get_indexer_user_input_lattice():

            lattice = self._indxr_lattice
            cell = self._indxr_cell

            lattice2, cell2 = xds_check_indexer_solution(
                os.path.join(self.get_working_directory(), "XPARM.XDS"),
                os.path.join(self.get_working_directory(), "SPOT.XDS"),
            )

            logger.debug("Centring analysis: %s => %s", lattice, lattice2)

            doubled_lattice = False
            for j in range(3):
                if int(round(cell2[j] / cell[j])) == 2:
                    doubled_lattice = True
                    axes = "A", "B", "C"
                    logger.debug("Lattice axis doubled: %s", axes[j])

            if (
                self._idxref_subtree_problem and (lattice2 != lattice)
            ) or doubled_lattice:

                # hmm.... looks like we don't agree on the correct result...
                # update the putative correct result as input

                logger.debug("Detected pseudocentred lattice")
                logger.debug(
                    "Inserting solution: %s " % lattice2
                    + "%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f" % cell2
                )

                self._indxr_replace(lattice2, cell2)

                logger.debug("Set lattice: %s", lattice2)
                logger.debug("Set cell: %f %f %f %f %f %f" % cell2)

                # then rerun

                self.set_indexer_done(False)
                return

        # finally read through SPOT.XDS and XPARM.XDS to get an estimate
        # of the low resolution limit - this should be pretty straightforward
        # since what I want is the resolution of the lowest resolution indexed
        # spot..

        spot_file = os.path.join(self.get_working_directory(), "SPOT.XDS")

        experiment = self.get_indexer_experiment_list()[0]
        crystal_model = experiment.crystal

        spot_xds_handle = spot_xds.reader()
        spot_xds_handle.read_file(spot_file)

        miller_indices = flex.miller_index(spot_xds_handle.miller_index)

        # only those reflections that were actually indexed
        miller_indices = miller_indices.select(miller_indices != (0, 0, 0))

        ub = matrix.sqr(crystal_model.get_A())
        dmax = 1.05 * flex.max(1 / (ub.elems * miller_indices.as_vec3_double()).norms())

        logger.debug("Low resolution limit assigned as: %.2f", dmax)
        self._indxr_low_resolution = dmax
