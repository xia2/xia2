#!/usr/bin/env python
# DistlSignalStrength.py
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 11th May 2010
#
# A wrapper for the replacement for labelit.distl - distl.signal_strength.
# This includes the added ability to get a list of the spot positions on
# the image. This can in turn replace printpeaks.
#
# N.B. this is only included in more recent versions of Labelit.

from __future__ import absolute_import, division, print_function

import sys

from xia2.Driver.DriverFactory import DriverFactory


def DistlSignalStrength(DriverType=None):
    """Factory for DistlSignalStrength wrapper classes, with the specified
    Driver type."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DistlSignalStrengthWrapper(DriverInstance.__class__):
        """A wrapper for the program distl.signal_strength - which will provide
        functionality for looking for finding spots &c."""

        def __init__(self):

            DriverInstance.__class__.__init__(self)

            self.set_executable("distl.signal_strength")

            self._image = None

            self._statistics = {}
            self._peaks = []

        def set_image(self, image):
            """Set an image for analysis."""

            self._image = image

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

        def find_peaks(self):
            """Actually analyse the images."""

            self.add_command_line(self._image)
            self.add_command_line("verbose=True")
            self.start()
            self.close_wait()

            # check for errors
            self.check_for_errors()

            # ok now we're done, let's look through for some useful stuff

            output = self.get_all_output()

            self._peaks = []

            peak_xy = None
            peak_sn = None

            for o in output:

                if not "Peak" in o:
                    continue

                if "signal-to-noise" in o:
                    assert peak_xy is None
                    peak_sn = float(o.split("=")[-1])

                elif "position" in o:
                    assert peak_sn
                    l = o.replace("=", " ").split()
                    peak_xy = float(l[3]), float(l[5])

                    # it appears that the printpeaks coordinate system is
                    # swapped w.r.t. the distl one...

                    self._peaks.append((peak_xy[1], peak_xy[0], peak_sn))

                    peak_xy = None
                    peak_sn = None

            return self._peaks

        def get_statistics(self):
            return self._statistics

        def get_peaks(self):
            return self._peaks

    return DistlSignalStrengthWrapper()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        raise RuntimeError("%s image" % sys.argv[0])

    d = DistlSignalStrength()
    d.set_image(sys.argv[1])
    peaks = d.find_peaks()

    for m in peaks:
        print("%6.1f %6.1f %6.1f" % m)
