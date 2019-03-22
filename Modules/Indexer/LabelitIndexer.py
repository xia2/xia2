#!/usr/bin/env python
# LabelitIndex.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 2nd June 2006
#
# A wrapper for labelit.index - this will provide functionality to:
#
# Decide the beam centre.
# Index the lattce.
#

from __future__ import absolute_import, division, print_function

import copy
import math
import os

from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.lib.bits import auto_logfiler
from xia2.lib.SymmetryLib import lattice_to_spacegroup
from xia2.Modules.Indexer.IndexerSelectImages import (
    index_select_images_lone,
    index_select_images_user,
)
from xia2.Modules.Indexer.MosflmCheckIndexerSolution import (
    mosflm_check_indexer_solution,
)

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.Indexer import IndexerSingleSweep

# other labelit things that this uses
from xia2.Wrappers.Labelit.LabelitMosflmScript import LabelitMosflmScript
from xia2.Wrappers.Labelit.LabelitStats_distl import LabelitStats_distl


class LabelitIndexer(IndexerSingleSweep):
    """A wrapper for the program labelit.index - which will provide
  functionality for deciding the beam centre and indexing the
  diffraction pattern."""

    def __init__(self, indxr_print=True):
        super(LabelitIndexer, self).__init__()

        # this will check that Labelit is available in the PATH

        from xia2.Wrappers.Labelit.LabelitIndex import LabelitIndex

        index = LabelitIndex()

        # control over the behaviour

        self._refine_beam = True

        # this is linked to the above!

        self._beam_search_scope = 0.0

        # self._solutions = { }

        self._solution = None

        self._indxr_print = indxr_print

    def set_refine_beam(self, refine_beam):
        self._refine_beam = refine_beam

    def _index_prepare(self):
        # prepare to do some autoindexing

        if self._indxr_images == []:
            self._index_select_images()

    def _index_select_images(self):
        """Select correct images based on image headers."""

        phi_width = self.get_phi_width()
        images = self.get_matching_images()

        if PhilIndex.params.xia2.settings.interactive == True:
            selected_images = index_select_images_user(phi_width, images, Chatter)
        else:
            selected_images = index_select_images_lone(phi_width, images)

        for image in selected_images:
            Debug.write("Selected image %s" % image)
            self.add_indexer_image_wedge(image)

    def _compare_cell(self, c_ref, c_test):
        """Compare two sets of unit cell constants: if they differ by
    less than 5% / 5 degrees return True, else False."""

        for j in range(3):
            if math.fabs((c_test[j] - c_ref[j]) / c_ref[j]) > 0.05:
                return False

        for j in range(3, 6):
            if math.fabs(c_test[j] - c_ref[j]) > 5:
                return False

        return True

    def _index(self):
        """Actually index the diffraction pattern. Note well that
    this is not going to compute the matrix..."""

        # acknowledge this program

        Citations.cite("labelit")
        Citations.cite("distl")

        # self.reset()

        _images = []
        for i in self._indxr_images:
            for j in i:
                if not j in _images:
                    _images.append(j)

        _images.sort()

        images_str = "%d" % _images[0]
        for i in _images[1:]:
            images_str += ", %d" % i

        cell_str = None
        if self._indxr_input_cell:
            cell_str = "%.2f %.2f %.2f %.2f %.2f %.2f" % self._indxr_input_cell

        if self._indxr_sweep_name:

            # then this is a proper autoindexing run - describe this
            # to the journal entry

            # if len(self._fp_directory) <= 50:
            # dirname = self._fp_directory
            # else:
            # dirname = '...%s' % self._fp_directory[-46:]
            dirname = os.path.dirname(self.get_imageset().get_template())

            Journal.block(
                "autoindexing",
                self._indxr_sweep_name,
                "labelit",
                {
                    "images": images_str,
                    "target cell": cell_str,
                    "target lattice": self._indxr_input_lattice,
                    "template": self.get_imageset().get_template(),
                    "directory": dirname,
                },
            )

        if len(_images) > 4:
            raise RuntimeError("cannot use more than 4 images")

        from xia2.Wrappers.Labelit.LabelitIndex import LabelitIndex

        index = LabelitIndex()
        index.set_working_directory(self.get_working_directory())
        auto_logfiler(index)

        # task = 'Autoindex from images:'

        # for i in _images:
        # task += ' %s' % self.get_image_name(i)

        # self.set_task(task)

        Debug.write("Indexing from images:")
        for i in _images:
            index.add_image(self.get_image_name(i))
            Debug.write("%s" % self.get_image_name(i))

        xsweep = self.get_indexer_sweep()
        if xsweep is not None:
            if xsweep.get_distance() is not None:
                index.set_distance(xsweep.get_distance())
            # if self.get_wavelength_prov() == 'user':
            # index.set_wavelength(self.get_wavelength())
            if xsweep.get_beam_centre() is not None:
                index.set_beam_centre(xsweep.get_beam_centre())

        if self._refine_beam is False:
            index.set_refine_beam(False)
        else:
            index.set_refine_beam(True)
            index.set_beam_search_scope(self._beam_search_scope)

        if (math.fabs(self.get_wavelength() - 1.54) < 0.01) or (
            math.fabs(self.get_wavelength() - 2.29) < 0.01
        ):
            index.set_Cu_KA_or_Cr_KA(True)

        # sweep = self.get_indexer_sweep_name()
        # FileHandler.record_log_file(
        #'%s INDEX' % (sweep), self.get_log_file())

        try:
            index.run()
        except RuntimeError as e:

            if self._refine_beam is False:
                raise e

            # can we improve the situation?

            if self._beam_search_scope < 4.0:
                self._beam_search_scope += 4.0

                # try repeating the indexing!

                self.set_indexer_done(False)
                return "failed"

            # otherwise this is beyond redemption

            raise e

        self._solutions = index.get_solutions()

        # FIXME this needs to check the smilie status e.g.
        # ":)" or ";(" or "  ".

        # FIXME need to check the value of the RMSD and raise an
        # exception if the P1 solution has an RMSD > 1.0...

        # Change 27/FEB/08 to support user assigned spacegroups
        # (euugh!) have to "ignore" solutions with higher symmetry
        # otherwise the rest of xia will override us. Bummer.

        for i, solution in self._solutions.iteritems():
            if self._indxr_user_input_lattice:
                if lattice_to_spacegroup(solution["lattice"]) > lattice_to_spacegroup(
                    self._indxr_input_lattice
                ):
                    Debug.write("Ignoring solution: %s" % solution["lattice"])
                    del self._solutions[i]

        # check the RMSD from the triclinic unit cell
        if self._solutions[1]["rmsd"] > 1.0 and False:
            # don't know when this is useful - but I know when it is not!
            raise RuntimeError("high RMSD for triclinic solution")

        # configure the "right" solution
        self._solution = self.get_solution()

        # now store also all of the other solutions... keyed by the
        # lattice - however these should only be added if they
        # have a smiley in the appropriate record, perhaps?

        for solution in self._solutions.keys():
            lattice = self._solutions[solution]["lattice"]
            if lattice in self._indxr_other_lattice_cell:
                if (
                    self._indxr_other_lattice_cell[lattice]["goodness"]
                    < self._solutions[solution]["metric"]
                ):
                    continue

            self._indxr_other_lattice_cell[lattice] = {
                "goodness": self._solutions[solution]["metric"],
                "cell": self._solutions[solution]["cell"],
            }

        self._indxr_lattice = self._solution["lattice"]
        self._indxr_cell = tuple(self._solution["cell"])
        self._indxr_mosaic = self._solution["mosaic"]

        lms = LabelitMosflmScript()
        lms.set_working_directory(self.get_working_directory())
        lms.set_solution(self._solution["number"])
        self._indxr_payload["mosflm_orientation_matrix"] = lms.calculate()

        # get the beam centre from the mosflm script - mosflm
        # may have inverted the beam centre and labelit will know
        # this!

        mosflm_beam_centre = lms.get_mosflm_beam()

        if mosflm_beam_centre:
            self._indxr_payload["mosflm_beam_centre"] = tuple(mosflm_beam_centre)

        import copy

        detector = copy.deepcopy(self.get_detector())
        beam = copy.deepcopy(self.get_beam())
        from dxtbx.model.detector_helpers import set_mosflm_beam_centre

        set_mosflm_beam_centre(detector, beam, mosflm_beam_centre)

        from xia2.Experts.SymmetryExpert import lattice_to_spacegroup_number
        from scitbx import matrix
        from cctbx import sgtbx, uctbx
        from dxtbx.model import CrystalFactory

        mosflm_matrix = matrix.sqr(
            [
                float(i)
                for line in lms.calculate()
                for i in line.replace("-", " -").split()
            ][:9]
        )

        space_group = sgtbx.space_group_info(
            lattice_to_spacegroup_number(self._solution["lattice"])
        ).group()
        crystal_model = CrystalFactory.from_mosflm_matrix(
            mosflm_matrix,
            unit_cell=uctbx.unit_cell(tuple(self._solution["cell"])),
            space_group=space_group,
        )

        from dxtbx.model import Experiment, ExperimentList

        experiment = Experiment(
            beam=beam,
            detector=detector,
            goniometer=self.get_goniometer(),
            scan=self.get_scan(),
            crystal=crystal_model,
        )

        experiment_list = ExperimentList([experiment])
        self.set_indexer_experiment_list(experiment_list)

        # also get an estimate of the resolution limit from the
        # labelit.stats_distl output... FIXME the name is wrong!

        lsd = LabelitStats_distl()
        lsd.set_working_directory(self.get_working_directory())
        lsd.stats_distl()

        resolution = 1.0e6
        for i in _images:
            stats = lsd.get_statistics(self.get_image_name(i))

            resol = 0.5 * (stats["resol_one"] + stats["resol_two"])

            if resol < resolution:
                resolution = resol

        self._indxr_resolution_estimate = resolution

        return "ok"

    def _index_finish(self):
        """Check that the autoindexing gave a convincing result, and
    if not (i.e. it gave a centred lattice where a primitive one
    would be correct) pick up the correct solution."""

        # strictly speaking, given the right input there should be
        # no need to test...

        if self._indxr_input_lattice:
            return

        if self.get_indexer_sweep():
            if self.get_indexer_sweep().get_user_lattice():
                return

        if False:
            status, lattice, matrix, cell = mosflm_check_indexer_solution(self)
        else:
            status = None

        if status is None:

            # basis is primitive

            return

        if status is False:

            # basis is centred, and passes test

            return

        # ok need to update internals...

        self._indxr_lattice = lattice
        self._indxr_cell = cell

        Debug.write(
            "Inserting solution: %s " % lattice
            + "%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f" % cell
        )

        self._indxr_replace(lattice, cell, indxr_print=self._indxr_print)

        self._indxr_payload["mosflm_orientation_matrix"] = matrix

    # things to get results from the indexing

    def get_solutions(self):
        return self._solutions

    def get_solution(self):
        """Get the best solution from autoindexing."""
        if self._indxr_input_lattice is None:
            # FIXME in here I need to check that there is a
            # "good" smiley
            return copy.deepcopy(self._solutions[max(self._solutions.keys())])
        else:
            # look through for a solution for this lattice -
            # FIXME should it delete all other solutions?
            # c/f eliminate.

            # FIXME should also include a check for the indxr_input_cell

            if self._indxr_input_cell:
                for s in self._solutions.keys():
                    if self._solutions[s]["lattice"] == self._indxr_input_lattice:
                        if self._compare_cell(
                            self._indxr_input_cell, self._solutions[s]["cell"]
                        ):
                            return copy.deepcopy(self._solutions[s])
                        else:
                            del self._solutions[s]
                    else:
                        del self._solutions[s]

                raise RuntimeError(
                    "no solution for lattice %s with given cell"
                    % self._indxr_input_lattice
                )

            else:
                for s in self._solutions.keys():
                    if self._solutions[s]["lattice"] == self._indxr_input_lattice:
                        return copy.deepcopy(self._solutions[s])
                    else:
                        del self._solutions[s]

                raise RuntimeError(
                    "no solution for lattice %s" % self._indxr_input_lattice
                )
