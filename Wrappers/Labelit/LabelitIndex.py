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
import shutil
import sys

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Streams import Chatter

# from xia2.Handlers.Files import FileHandler


def LabelitIndex(DriverType=None, indxr_print=True):
    """Factory for LabelitIndex wrapper classes, with the specified
    Driver type."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class LabelitIndexWrapper(DriverInstance.__class__):
        """A wrapper for the program labelit.index - which will provide
        functionality for deciding the beam centre and indexing the
        diffraction pattern."""

        def __init__(self):

            DriverInstance.__class__.__init__(self)

            self.set_executable("labelit.index")

            self._primitive_unit_cell = None
            self._max_cell = None
            self._space_group_number = None
            self._beam_centre = None
            self._wavelength = None
            self._distance = None
            self._mosflm_beam_centre = None
            self._mosflm_detector_distance = None

            # XXX set special distl parameters, rubbish variable name!
            self._Cu_KA_or_Cr_KA = False

            self._images = []

            # control over the behaviour

            self._refine_beam = True

            # this is linked to the above!

            self._beam_search_scope = 0.0

            self._solutions = {}

            return

        def add_image(self, filename):
            self._images.append(filename)

        def set_primitive_unit_cell(self, primitive_unit_cell):
            self._primitive_unit_cell = primitive_unit_cell

        def set_max_cell(self, max_cell):
            self._max_cell = max_cell

        def set_space_group_number(self, space_group_number):
            self._space_group_number = space_group_number

        def set_beam_search_scope(self, beam_search_scope):
            self._beam_search_scope = beam_search_scope

        def set_refine_beam(self, refine_beam):
            self._refine_beam = refine_beam
            return

        def set_wavelength(self, wavelength):
            self._wavelength = wavelength

        def set_distance(self, distance):
            self._distance = distance

        def set_beam_centre(self, beam_centre):
            self._beam_centre = beam_centre

        def set_Cu_KA_or_Cr_KA(self, Cu_KA_or_Cr_KA):
            self._Cu_KA_or_Cr_KA = Cu_KA_or_Cr_KA

        def _write_dataset_preferences(self, n_images):
            """Write the dataset_preferences.py file in the working
            directory - this will include the beam centres etc."""

            out = open(
                os.path.join(self.get_working_directory(), "dataset_preferences.py"),
                "w",
            )

            # only write things out if they have been overridden
            # from what is in the header...

            if self._max_cell:
                out.write("distl_minimum_number_spots_for_indexing = 1\n")

            if self._distance is not None:
                out.write("autoindex_override_distance = %f\n" % self._distance)
            if self._wavelength is not None:
                out.write("autoindex_override_wavelength = %f\n" % self._wavelength)
            if self._beam_centre is not None:
                out.write("autoindex_override_beam = (%f, %f)\n" % self._beam_centre)

            if self._refine_beam is False:
                out.write("beam_search_scope = 0.0\n")
            else:
                out.write("beam_search_scope = %f\n" % self._beam_search_scope)

            # check to see if this is an image plate *or* the
            # wavelength corresponds to Cu KA (1.54A) or Cr KA (2.29 A).
            # numbers from rigaku americas web page.

            if self._Cu_KA_or_Cr_KA:
                out.write("distl_force_binning = True\n")
                out.write("distl_profile_bumpiness = 10\n")
                out.write("distl_binned_image_spot_size = 10\n")

            out.write("wedgelimit = %d\n" % n_images)

            # new feature - index on the spot centre of mass, not the
            # highest pixel (should improve the RMS deviation reports.)

            out.write('distl_spotfinder_algorithm = "maximum_pixel"\n')

            if self._primitive_unit_cell is not None:
                out.write("lepage_max_delta = 5.0")

            out.close()

            return

        def check_labelit_errors(self):
            """Check through the standard output for error reports."""

            output = self.get_all_output()

            for o in output:
                if (
                    "No_Indexing_Solution" in o
                    or "InputFileError" in o
                    or "INDEXING UNRELIABLE" in o
                ):
                    raise RuntimeError("indexing failed: %s" % o.split(":")[-1].strip())

        def run(self):
            """Run labelit.index"""

            assert len(self._images) > 0
            self._images.sort()

            if self._max_cell is None and len(self._images) > 4:
                raise RuntimeError("cannot use more than 4 images")

            # task = 'Autoindex from images:'

            # for i in _images:
            # task += ' %s' % self.get_image_name(i)

            # self.set_task(task)

            self.add_command_line("--index_only")

            for image in self._images:
                self.add_command_line(image)

            if self._space_group_number is not None:
                self.add_command_line("known_symmetry=%d" % self._space_group_number)

            if self._primitive_unit_cell is not None:
                self.add_command_line(
                    "target_cell=%f,%f,%f,%f,%f,%f" % tuple(self._primitive_unit_cell)
                )

            if self._max_cell is not None:
                self.add_command_line("codecamp.maxcell=%f" % self._max_cell)

            self._write_dataset_preferences(len(self._images))

            shutil.copyfile(
                os.path.join(self.get_working_directory(), "dataset_preferences.py"),
                os.path.join(
                    self.get_working_directory(),
                    "%d_dataset_preferences.py" % self.get_xpid(),
                ),
            )

            self.start()
            self.close_wait()

            # sweep = self.get_indexer_sweep_name()
            # FileHandler.record_log_file(
            #'%s INDEX' % (sweep), self.get_log_file())

            # check for errors
            self.check_for_errors()

            # check for labelit errors - if something went wrong, then
            # try to address it by e.g. extending the beam search area...

            self.check_labelit_errors()

            # ok now we're done, let's look through for some useful stuff
            output = self.get_all_output()

            counter = 0

            # FIXME 03/NOV/06 something to do with the new centre search...

            # example output:

            # Beam center is not immediately clear; rigorously retesting \
            #                                             2 solutions
            # Beam x 109.0 y 105.1, initial score 538; refined rmsd: 0.1969
            # Beam x 108.8 y 106.1, initial score 354; refined rmsd: 0.1792

            # in here want to parse the beam centre search if it was done,
            # and check that the highest scoring solution was declared
            # the "best" - though should also have a check on the
            # R.M.S. deviation of that solution...

            # do this first!

            for j in range(len(output)):
                o = output[j]
                if "Beam centre is not immediately clear" in o:
                    # read the solutions that it has found and parse the
                    # information

                    centres = []
                    scores = []
                    rmsds = []

                    num_solutions = int(o.split()[-2])

                    for n in range(num_solutions):
                        record = (
                            output[j + n + 1]
                            .replace(",", " ")
                            .replace(";", " ")
                            .split()
                        )
                        x, y = float(record[2]), float(record[4])

                        centres.append((x, y))
                        scores.append(int(record[7]))
                        rmsds.append(float(record[-1]))

                    # next perform some analysis and perhaps assert the
                    # correct solution - for the moment just raise a warning
                    # if it looks like wrong solution may have been picked

                    best_beam_score = (0.0, 0.0, 0)
                    best_beam_rms = (0.0, 0.0, 1.0e8)

                    for n in range(num_solutions):
                        beam = centres[n]
                        score = scores[n]
                        rmsd = rmsds[n]

                        if score > best_beam_score[2]:
                            best_beam_score = (beam[0], beam[1], score)

                        if rmsd < best_beam_rmsd[2]:
                            best_beam_rmsd = (beam[0], beam[1], rmsd)

                    # allow a difference of 0.1mm in either direction...
                    if (
                        math.fabs(best_beam_score[0] - best_beam_rmsd[0]) > 0.1
                        or math.fabs(best_beam_score[1] - best_beam_rmsd[1]) > 0.1
                    ):
                        Chatter.write("Labelit may have picked the wrong beam centre")

                        # FIXME as soon as I get the indexing loop
                        # structure set up, this should reset the
                        # indexing done flag, set the search range to
                        # 0, correct beam and then return...

                        # should also allow for the possibility that
                        # labelit has selected the best solution - so this
                        # will need to remember the stats for this solution,
                        # then compare them against the stats (one day) from
                        # running with the other solution - eventually the
                        # correct solution will result...

            for o in output:
                l = o.split()

                if l[:3] == ["Beam", "center", "x"]:
                    x = float(l[3].replace("mm,", ""))
                    y = float(l[5].replace("mm,", ""))

                    self._mosflm_beam_centre = (x, y)
                    self._mosflm_detector_distance = float(l[7].replace("mm", ""))
                    # self.set_indexer_beam_centre((x, y))
                    # self.set_indexer_distance(float(l[7].replace('mm', '')))

                    self._mosaic = float(l[10].replace("mosaicity=", ""))

                if l[:3] == ["Solution", "Metric", "fit"]:
                    break

                counter += 1

            # if we've just broken out (counter < len(output)) then
            # we need to gather the output

            if counter >= len(output):
                raise RuntimeError("error in indexing")

            # FIXME this needs to check the smilie status e.g.
            # ":)" or ";(" or "  ".

            for i in range(counter + 1, len(output)):
                o = output[i][3:]
                smiley = output[i][:3]
                l = o.split()
                if l:

                    self._solutions[int(l[0])] = {
                        "number": int(l[0]),
                        "mosaic": self._mosaic,
                        "metric": float(l[1]),
                        "rmsd": float(l[3]),
                        "nspots": int(l[4]),
                        "lattice": l[6],
                        "cell": map(float, l[7:13]),
                        "volume": int(l[-1]),
                        "smiley": smiley,
                    }

            # remove clearly incorrect solutions i.e. rmsd >> rmsd for P1 i.e. factor
            # of 4.0 or more...

            for s in sorted(self._solutions):
                if self._solutions[s]["rmsd"] > 4.0 * self._solutions[1]["rmsd"]:
                    del (self._solutions[s])

            return "ok"

        def get_solutions(self):
            return self._solutions

        def get_mosflm_beam_centre(self):
            return self._mosflm_beam_centre

        def get_mosflm_detector_distance(self):
            return self._mosflm_detector_distance

    return LabelitIndexWrapper()


if __name__ == "__main__":

    indexer = LabelitIndex()
    for filename in sys.argv[1:]:
        indexer.add_image(filename)
    indexer.run()
    print("".join(indexer.get_all_output()))
