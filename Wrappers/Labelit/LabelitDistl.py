#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import os

from xia2.Driver.DriverFactory import DriverFactory


def LabelitDistl(DriverType=None):
    """Factory for LabelitDistl wrapper classes, with the specified
    Driver type."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class LabelitDistlWrapper(DriverInstance.__class__):
        """A wrapper for the program labelit.distl - which will provide
        functionality for looking for ice rings and screening diffraction
        images."""

        def __init__(self):

            DriverInstance.__class__.__init__(self)

            self.set_executable("labelit.distl")

            self._images = []

            self._statistics = {}

        def add_image(self, image):
            """Add an image for indexing."""

            if not image in self._images:
                self._images.append(image)

            return

        def distl(self):
            """Actually analyse the images."""

            self._images.sort()

            for i in self._images:
                self.add_command_line(i)

            task = "Screen images:"

            for i in self._images:
                task += " %s" % i

            self.set_task(task)

            self.start()
            self.close_wait()

            # check for errors
            self.check_for_errors()

            # ok now we're done, let's look through for some useful stuff

            output = self.get_all_output()

            current_image = None

            for o in output:
                if "None" in o and "Resolution" in o:
                    l = o.replace("None", "0.0").split()
                else:
                    l = o.split()

                if l[:1] == ["File"]:
                    current_image = l[2]
                    self._statistics[current_image] = {}

                if l[:2] == ["Spot", "Total"]:
                    self._statistics[current_image]["spots_total"] = int(l[-1])
                if l[:2] == ["In-Resolution", "Total"]:
                    self._statistics[current_image]["spots"] = int(l[-1])
                if l[:3] == ["Good", "Bragg", "Candidates"]:
                    self._statistics[current_image]["spots_good"] = int(l[-1])
                if l[:2] == ["Ice", "Rings"]:
                    self._statistics[current_image]["ice_rings"] = int(l[-1])
                if l[:3] == ["Method", "1", "Resolution"]:
                    self._statistics[current_image]["resol_one"] = float(l[-1])
                if l[:3] == ["Method", "2", "Resolution"]:
                    self._statistics[current_image]["resol_two"] = float(l[-1])
                if l[:3] == ["%Saturation,", "Top", "50"]:
                    self._statistics[current_image]["saturation"] = float(l[-1])

            return "ok"

        # things to get results from the indexing

        def get_statistics(self, image):
            """Get the screening statistics from image as dictionary.
            The keys are spots_total, spots, spots_good, ice_rings,
            resol_one, resol_two."""

            return self._statistics[os.path.split(image)[-1]]

    return LabelitDistlWrapper()
