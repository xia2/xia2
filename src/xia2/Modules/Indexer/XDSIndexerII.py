# An reimplementation of the XDS indexer to work for harder cases, for example
# cases where the whole sweep needs to be read into memory in IDXREF to get
# a decent indexing solution (these do happen) and also cases where the
# crystal is highly mosaic. Perhaps. This will now be directly inherited from
# the original XDSIndexer and only the necessary method overloaded (as I
# should have done this in the first place.)


import logging
import math
import os

import dxtbx
from dials.array_family import flex
from dials.util.ascii_art import spot_counts_per_image_plot
from dxtbx.model import Experiment, ExperimentList
from dxtbx.serialize.xds import to_crystal, to_xds
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import banner
from xia2.lib.bits import auto_logfiler
from xia2.Modules.Indexer.XDSIndexer import XDSIndexer
from xia2.Wrappers.Dials.ImportXDS import ImportXDS
from xia2.Wrappers.XDS.XDS import XDSException

logger = logging.getLogger("xia2.Modules.Indexer.XDSIndexerII")


class XDSIndexerII(XDSIndexer):
    """An extension of XDSIndexer using all available images."""

    def __init__(self):
        super().__init__()

        self._index_select_images = "ii"

        self._i_or_ii = None

    # helper functions

    def _index_select_images_ii(self):
        """Select correct images based on image headers."""

        phi_width = self.get_phi_width()

        if phi_width == 0.0:
            raise RuntimeError("cannot use still images")

        # use five degrees for the background calculation

        five_deg = int(round(5.0 / phi_width)) - 1
        turn = int(round(360.0 / phi_width)) - 1

        if five_deg < 5:
            five_deg = 5

        images = self.get_matching_images()

        # characterise the images - are there just two (e.g. dna-style
        # reference images) or is there a full block? if it is the
        # former then we have a problem, as we want *all* the images in the
        # sweep...

        wedges = []

        min_images = PhilIndex.params.xia2.settings.input.min_images

        if len(images) < 3 and len(images) < min_images:
            raise RuntimeError(
                "This INDEXER cannot be used for only %d images" % len(images)
            )

        # including > 360 degrees in indexing does not add fresh information
        start = min(images)
        end = max(images)
        if (end - start) > turn:
            end = start + turn
        logger.debug("Adding images for indexer: %d -> %d", start, end)

        wedges.append((start, end))

        # FIXME this should have a wrapper function!

        if start + five_deg in images:
            self._background_images = (start, start + five_deg)
        else:
            self._background_images = (start, end)

        return wedges

    def _index_prepare(self):
        logger.notice(banner("Spotfinding %s" % self.get_indexer_sweep_name()))
        super()._index_prepare()

        reflections_file = spot_xds_to_reflection_file(
            self._indxr_payload["SPOT.XDS"],
            working_directory=self.get_working_directory(),
        )
        refl = flex.reflection_table.from_file(reflections_file)
        logger.info(spot_counts_per_image_plot(refl))

    def _index(self):
        """Actually do the autoindexing using the data prepared by the
        previous method."""

        self._index_remove_masked_regions()

        if self._i_or_ii is None:
            self._i_or_ii = self.decide_i_or_ii()
            logger.debug("Selecting I or II, chose %s", self._i_or_ii)

        idxref = self.Idxref()

        for file in ["SPOT.XDS"]:
            idxref.set_input_data_file(file, self._indxr_payload[file])

        # set the phi start etc correctly

        idxref.set_data_range(self._indxr_images[0][0], self._indxr_images[0][1])
        idxref.set_background_range(self._indxr_images[0][0], self._indxr_images[0][1])

        if self._i_or_ii == "i":
            blocks = self._index_select_images_i()
            for block in blocks[:1]:
                starting_frame = block[0]
                starting_angle = self.get_scan().get_angle_from_image_index(
                    starting_frame
                )

                idxref.set_starting_frame(starting_frame)
                idxref.set_starting_angle(starting_angle)

                idxref.add_spot_range(block[0], block[1])

            for block in blocks[1:]:
                idxref.add_spot_range(block[0], block[1])
        else:
            for block in self._indxr_images[:1]:
                starting_frame = block[0]
                starting_angle = self.get_scan().get_angle_from_image_index(
                    starting_frame
                )

                idxref.set_starting_frame(starting_frame)
                idxref.set_starting_angle(starting_angle)

                idxref.add_spot_range(block[0], block[1])

            for block in self._indxr_images[1:]:
                idxref.add_spot_range(block[0], block[1])

        # FIXME need to also be able to pass in the known unit
        # cell and lattice if already available e.g. from
        # the helper... indirectly

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

        # FIXED need to set the beam centre here - this needs to come
        # from the input .xinfo object or header, and be converted
        # to the XDS frame... done.

        from dxtbx.serialize.xds import to_xds

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
                    # compare solutions
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

    def decide_i_or_ii(self):
        logger.debug("Testing II or I indexing")

        try:
            fraction_etc_i = self.test_i()
            fraction_etc_ii = self.test_ii()

            if not fraction_etc_i and fraction_etc_ii:
                return "ii"
            if fraction_etc_i and not fraction_etc_ii:
                return "i"

            logger.debug("I:  %.2f %.2f %.2f" % fraction_etc_i)
            logger.debug("II: %.2f %.2f %.2f" % fraction_etc_ii)

            if (
                fraction_etc_i[0] > fraction_etc_ii[0]
                and fraction_etc_i[1] < fraction_etc_ii[1]
                and fraction_etc_i[2] < fraction_etc_ii[2]
            ):
                return "i"

            return "ii"

        except Exception as e:
            logger.debug(str(e), exc_info=True)
            return "ii"

    def test_i(self):
        idxref = self.Idxref()

        self._index_remove_masked_regions()
        for file in ["SPOT.XDS"]:
            idxref.set_input_data_file(file, self._indxr_payload[file])

        idxref.set_data_range(self._indxr_images[0][0], self._indxr_images[0][1])
        idxref.set_background_range(self._indxr_images[0][0], self._indxr_images[0][1])

        # set the phi start etc correctly

        blocks = self._index_select_images_i()

        for block in blocks[:1]:
            starting_frame = block[0]
            starting_angle = self.get_scan().get_angle_from_image_index(starting_frame)

            idxref.set_starting_frame(starting_frame)
            idxref.set_starting_angle(starting_angle)

            idxref.add_spot_range(block[0], block[1])

        for block in blocks[1:]:
            idxref.add_spot_range(block[0], block[1])

        converter = to_xds(self.get_imageset())
        xds_beam_centre = converter.detector_origin

        idxref.set_beam_centre(xds_beam_centre[0], xds_beam_centre[1])

        idxref.run()

        return idxref.get_fraction_rmsd_rmsphi()

    def test_ii(self):
        idxref = self.Idxref()

        self._index_remove_masked_regions()
        for file in ["SPOT.XDS"]:
            idxref.set_input_data_file(file, self._indxr_payload[file])

        idxref.set_data_range(self._indxr_images[0][0], self._indxr_images[0][1])
        idxref.set_background_range(self._indxr_images[0][0], self._indxr_images[0][1])

        for block in self._indxr_images[:1]:
            starting_frame = block[0]
            starting_angle = self.get_scan().get_angle_from_image_index(starting_frame)

            idxref.set_starting_frame(starting_frame)
            idxref.set_starting_angle(starting_angle)

            idxref.add_spot_range(block[0], block[1])

        converter = to_xds(self.get_imageset())
        xds_beam_centre = converter.detector_origin

        idxref.set_beam_centre(xds_beam_centre[0], xds_beam_centre[1])

        idxref.run()

        return idxref.get_fraction_rmsd_rmsphi()


def spot_xds_to_reflection_file(spot_xds, working_directory):
    importer = ImportXDS()
    importer.set_working_directory(working_directory)
    auto_logfiler(importer)
    importer.set_spot_xds(spot_xds)
    importer.run()
    return importer.get_reflection_filename()
