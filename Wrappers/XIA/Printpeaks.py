#!/usr/bin/env python
# Printpeaks.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 29th November 2007
#
# A wrapper for the program "printpeaks" derived from the DiffractionImage
# code in XIA1 by Francois Remacle.
#
from __future__ import absolute_import, division, print_function

import math
import os
import sys

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Wrappers.XIA.Diffdump import Diffdump
from xia2.Wrappers.XIA.PrintpeaksMosflm import PrintpeaksMosflm


def Printpeaks(DriverType=None):
    """A factory for wrappers for the printpeaks."""

    if not "XIA2_USE_PRINTPEAKS" in os.environ:
        return PrintpeaksMosflm(DriverType=DriverType)

    DriverInstance = DriverFactory.Driver(DriverType)

    class PrintpeaksWrapper(DriverInstance.__class__):
        """Provide access to the functionality in printpeaks."""

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("printpeaks")

            self._image = None
            self._peaks = {}

        def set_image(self, image):
            """Set an image to read the header of."""
            self._image = image
            self._peaks = {}

        def get_maxima(self):
            """Run diffdump, printpeaks to get a list of diffraction maxima
            at their image positions, to allow for further analysis."""

            if not self._image:
                raise RuntimeError("image not set")

            if not os.path.exists(self._image):
                raise RuntimeError("image %s does not exist" % self._image)

            dd = Diffdump()
            dd.set_image(self._image)
            header = dd.readheader()

            beam = header["raw_beam"]
            pixel = header["pixel"]

            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            self.check_for_errors()

            # results were ok, so get all of the output out
            output = self.get_all_output()

            peaks = []

            for record in output:

                if not "Peak" in record[:4]:
                    continue

                lst = record.replace(":", " ").split()
                x = float(lst[4])
                y = float(lst[6])
                i = float(lst[-1])
                x += beam[0]
                y += beam[1]
                x /= pixel[0]
                y /= pixel[1]

                peaks.append((x, y, i))

            return peaks

        def printpeaks(self):
            """Run printpeaks and get the list of peaks out, then decompose
            this to a histogram."""

            if not self._image:
                raise RuntimeError("image not set")

            if not os.path.exists(self._image):
                raise RuntimeError("image %s does not exist" % self._image)

            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            self.check_for_errors()

            # results were ok, so get all of the output out
            output = self.get_all_output()

            peaks = []

            self._peaks = {}

            for record in output:

                if not "Peak" in record[:4]:
                    continue

                intensity = float(record.split(":")[-1])
                peaks.append(intensity)

            # now construct the histogram

            log_max = int(math.log10(peaks[0])) + 1
            max_limit = int(math.pow(10.0, log_max))

            for limit in [5, 10, 20, 50, 100, 200, 500, 1000]:
                if limit > max_limit:
                    continue
                self._peaks[float(limit)] = len([j for j in peaks if j > limit])

            return self._peaks

        def threshold(self, nspots):
            if not self._peaks:
                peaks = self.printpeaks()
            else:
                peaks = self._peaks
            keys = sorted(peaks.keys())
            keys.reverse()
            for thresh in keys:
                if peaks[thresh] > nspots:
                    return thresh
            return min(keys)

        def screen(self):
            if not self._image:
                raise RuntimeError("image not set")

            if not os.path.exists(self._image):
                raise RuntimeError("image %s does not exist" % self._image)

            self.add_command_line("-th")
            self.add_command_line("10")
            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            self.check_for_errors()

            # results were ok, so get all of the output out
            output = self.get_all_output()

            peaks = []

            self._peaks = {}

            for record in output:

                if not "Peak" in record[:4]:
                    continue

                intensity = float(record.split(":")[-1])
                peaks.append(intensity)

            print(len(peaks), max(peaks))

            if len(peaks) < 10:
                return "blank"

            return "ok"

        def getpeaks(self):
            """Just get the list of peaks out, as (x, y, i)."""

            if not self._image:
                raise RuntimeError("image not set")

            if not os.path.exists(self._image):
                raise RuntimeError("image %s does not exist" % self._image)

            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            self.check_for_errors()

            # results were ok, so get all of the output out
            output = self.get_all_output()

            peaks = []

            for record in output:

                if not "Peak" in record[:4]:
                    continue

                lst = record.split(":")

                x = float(lst[1].split()[0])
                y = float(lst[2].split()[0])
                i = float(lst[4])

                peaks.append((x, y, i))

            return peaks

    return PrintpeaksWrapper()


if __name__ == "__main__":
    # run a test of some of the new code...

    p = Printpeaks()
    p.set_image(sys.argv[1])
    peaks = p.get_maxima()

    for m in peaks:
        print("%6.1f %6.1f %6.1f" % m)
