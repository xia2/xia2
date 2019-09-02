#!/usr/bin/env python


from __future__ import absolute_import, division, print_function

import libtbx.phil
from spotfinder.command_line import sweep_strength
from xia2.Driver.DriverFactory import DriverFactory

master_params = sweep_strength.master_params
custom_params = libtbx.phil.parse(
    """
distl.verbosity = 0
"""
)
# override distl.sweep_strength_defaults
master_params = master_params.fetch(source=custom_params)


def DistlSweepStrength(DriverType=None, params=None):
    """Factory for DistlSweepStrength wrapper classes, with the specified
    Driver type."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DistlSweepStrengthWrapper(DriverInstance.__class__):
        """A wrapper for the program distl.sweep_strength - which will provide
        functionality for looking for finding spots &c."""

        def __init__(self, params=None):

            DriverInstance.__class__.__init__(self)

            # phil parameters

            if not params:
                params = master_params.extract()
            self._params = params

            self.set_executable("distl.sweep_strength")

            self._images = []

            self._statistics = {}
            self._peaks = []

        def set_image(self, image):
            """Set an image for analysis."""

            self._images.append(image)

        def distl(self):
            """Actually analyse the images."""

            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            # check for errors
            self.check_for_errors()

            # ok now we're done, let's look through for some useful stuff

            output = self.get_all_output()

            for o in output:
                l = o.split()

                if l[:2] == ["Spot", "Total"]:
                    self._statistics["spots_total"] = int(l[-1])
                if l[:2] == ["In-Resolution", "Total"]:
                    self._statistics["spots"] = int(l[-1])
                if l[:3] == ["Good", "Bragg", "Candidates"]:
                    self._statistics["spots_good"] = int(l[-1])
                if l[:2] == ["Ice", "Rings"]:
                    self._statistics["ice_rings"] = int(l[-1])
                if l[:3] == ["Method", "1", "Resolution"]:
                    self._statistics["resol_one"] = float(l[-1])
                if l[:3] == ["Method", "2", "Resolution"]:
                    self._statistics["resol_two"] = float(l[-1])
                if l[:3] == ["%Saturation,", "Top", "50"]:
                    self._statistics["saturation"] = float(l[-1])

        def run(self):
            """Actually analyse the images."""

            for image in self._images:
                self.add_command_line(image)
            self.start()
            self.close_wait()

            # check for errors
            self.check_for_errors()

            output = self.get_all_output()
            print("".join(output))

    return DistlSweepStrengthWrapper()
