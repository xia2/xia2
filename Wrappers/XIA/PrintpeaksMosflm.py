#!/usr/bin/env python
# PrintpeaksMosflm.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A replacement for the printpeaks tool and wrapper, using Mosflm.
#
from __future__ import absolute_import, division, print_function

import copy
import math
import os
import sys

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Experts.FindImages import (
    image2image,
    image2template_directory,
    template_number2image,
)
from xia2.Wrappers.XIA.Diffdump import Diffdump


def PrintpeaksMosflm(DriverType=None):
    """A factory for wrappers for the printpeaks/mosflm."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class PrintpeaksMosflmWrapper(DriverInstance.__class__):
        """Provide access to the spot finding functionality in Mosflm."""

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("ipmosflm")

            if "CCP4_SCR" in os.environ:
                self.set_working_directory(os.environ["CCP4_SCR"])

            self._image = None
            self._peaks = {}

        def set_image(self, image):
            """Set an image to read the header of."""
            self._image = image
            self._peaks = {}

        def get_maxima(self, threshold=5.0):
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

            template, directory = image2template_directory(self._image)
            image_number = image2image(os.path.split(self._image)[-1])

            spot_file = "%s.spt" % template_number2image(template, image_number)

            self.start()

            self.input('template "%s"' % template)
            self.input('directory "%s"' % directory)
            self.input("findspots local find %d file %s" % (image_number, spot_file))
            self.input("go")

            self.close_wait()

            self.check_for_errors()

            output = open(
                os.path.join(self.get_working_directory(), spot_file)
            ).readlines()

            os.remove(os.path.join(self.get_working_directory(), spot_file))

            peaks = []

            for record in output[3:-2]:
                lst = record.split()
                x = float(lst[0])
                y = float(lst[1])
                i = float(lst[4]) / float(lst[5])
                x /= pixel[0]
                y /= pixel[1]

                if i < threshold:
                    continue

                # this is Mosflm right? Swap X & Y!!

                peaks.append((y, x, i))

            return peaks

        def printpeaks(self):
            """Run printpeaks and get the list of peaks out, then decompose
      this to a histogram."""

            if not self._image:
                raise RuntimeError("image not set")

            if not os.path.exists(self._image):
                raise RuntimeError("image %s does not exist" % self._image)

            _peaks = self.get_maxima()
            peaks = []

            for peak in _peaks:
                intensity = peak[2]
                peaks.append(intensity)

            # now construct the histogram

            log_max = int(math.log10(peaks[0])) + 1
            max_limit = int(math.pow(10.0, log_max))

            if False:

                limit = math.pow(10.0, log_max)

                while limit > 2.0:
                    self._peaks[limit] = len([j for j in peaks if j > limit])
                    limit *= 0.5

            else:

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

            _peaks = self.get_maxima()

            peaks = []

            for peak in _peaks:
                if peak[2] > 10:
                    peaks.append(peak)

            if len(peaks) < 10:
                return "blank"

            return "ok"

    return PrintpeaksMosflmWrapper()


if __name__ == "__main__":
    # run a test of some of the new code...

    p = Printpeaks()
    p.set_image(sys.argv[1])
    peaks = p.get_maxima()

    for m in peaks:
        print("%6.1f %6.1f %6.1f" % m)
