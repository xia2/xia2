#!/usr/bin/env python
# GainEstimater.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A module to estimate the GAIN for a detector based on a number of images
# from a sweep. Will generate a GAIN value from a number of images in that
# sweep and collect the average.
#
# Will also include some test code to estimate the error on that average.

from __future__ import absolute_import, division, print_function

import math
import os
import sys

from xia2.Wrappers.XIA.Diffdump import Diffdump


def gain(image):
    """Get the gain from an image."""

    dd = Diffdump()
    dd.set_image(image)
    return dd.gain()


def generate_gain(image_list):
    """Get the mean and standard deviation in gain from a list
  of images."""

    gains = []
    for image in image_list:
        gains.append(gain(image))

    sum = 0.0
    for g in gains:
        sum += g
    mean = sum / len(gains)

    sd = 0.0
    for g in gains:
        sd += (g - mean) * (g - mean)
    sd = math.sqrt(sd / len(gains))

    return mean, sd


if __name__ == "__main__":

    directory = os.path.join(os.environ["XIA2_ROOT"], "Data", "Test", "Images")

    if len(sys.argv) == 1:

        print(gain(os.path.join(directory, "12287_1_E1_001.img")))
        print(gain(os.path.join(directory, "12287_1_E1_090.img")))

        print(
            generate_gain(
                [
                    os.path.join(directory, "12287_1_E1_001.img"),
                    os.path.join(directory, "12287_1_E1_090.img"),
                ]
            )
        )

    else:

        print(generate_gain(sys.argv[1:]))
