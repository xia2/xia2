#!/usr/bin/env python
# IceId.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 20th May 2008
#
# A subroutine to identify when ice rings are a problem (that is, when it
# appears that a significant amount of "peaks" are contained within ice
# ring regions. As yet the definition of significant is not certain...
#

import math
import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.XIA.Diffdump import Diffdump

from Modules.Indexer.MosflmCheckIndexerSolution import locate_maxima

# first a couple of jiffy calculation subroutines

def is_ice(dspacing):
    '''Return 1 if this dspacing would place the reflection within a
    known ice ring, 0 otherwise.'''

    if dspacing < 3.93 and dspacing > 3.87:
        return 1
    if dspacing < 3.70 and dspacing > 3.64:
        return 1
    if dspacing < 3.47 and dspacing > 3.41:
        return 1
    if dspacing < 2.70 and dspacing > 2.64:
        return 1
    if dspacing < 2.28 and dspacing > 2.22:
        return 1

    return 0

def compute_resolution(distance, offset, wavelength):
    '''Compute the resolution (d spacing) for the provided sample to
    detector distance, offset on the detector and wavelength. This assumes
    that the detector is orthogonal to the direct beam.'''

    theta = 0.5 * math.atan(offset / distance)
    dspacing = 0.5 * wavelength / math.sin(theta)

    return dspacing

class IceId:
    '''A class to help identify if images contain ice rings, by performing a
    peak search, calculating the resolution of the peaks and seeing how many
    fall in the region expected for ice rings (as taken from example
    XDS input files at:

    http://www.mpimf-heidelberg.mpg.de/~kabsch/xds/html_doc/INPUT_templates/)

    this will simply accumulate the number of peaks in the different regions
    and overall (between 2-4A) and see if a surprising number of the peaks
    occur in those regions.'''

    def __init__(self):

        # these may optionally be set by the user

        self._image = None
        self._beam = None
        self._distance = None
        self._wavelength = None

        # and these must be set from the image header

        self._pixel = None

        # and this is used internally

        self._setup = False

        return

    def set_beam(self, beam):
        self._beam = beam
        return

    def set_distance(self, distance):
        self._distance = distance
        return

    def set_wavelength(self, wavelength):
        self._wavelength = wavelength
        return

    def set_image(self, image):
        self._image = image
        self._setup = False
        return

    def setup(self):
        '''Run diffdump to get the image header values out.'''

        if not self._image:
            raise RuntimeError, 'image not assigned'

        p = Diffdump()
        p.set_image(self._image)
        header = p.readheader()

        # check that the pixels are square; raise exception if not
        if not header['pixel'][0] == header['pixel'][1]:
            raise RuntimeError, 'pixels not square'

        pixel = header['pixel'][0]
        wavelength = header['wavelength']
        beam = header['beam']
        distance = header['distance']

        self._pixel = pixel

        if not self._wavelength:
            self._wavelength = wavelength

        # printpeaks prints out the peaks w.r.t. the header beam centre...

        if not self._beam:
            self._beam = 0.0, 0.0
        else:
            x = self._beam[1] - beam[0]
            y = self._beam[0] - beam[1]
            self._beam = x, y

        if not self._distance:
            self._distance = distance

        # ok, we be ok then...

        self._setup = True

        return

    def search(self):
        '''Actually assess if we are in an ice ring situation.'''

        if not self._setup:
            self.setup()

        # p = Printpeaks()
        # p.set_image(self._image)
        # peaks = p.getpeaks()

        # sometimes at the moment mosflm find spots fails => failover this...

        try:
            peaks = locate_maxima(self._image)
        except IOError, e:
            return 0.0

        # now do some sums...

        ice = 0.0
        notice = 0.0

        for p in peaks:
            dx = p[0]
            dy = p[1]
            i = p[2]

            d = math.sqrt(dx * dx + dy * dy)

            resol = compute_resolution(self._distance, d, self._wavelength)

            if resol < 2.0 or resol > 4.0:
                continue

            if is_ice(resol):
                ice += i
            else:
                notice += i

        if ice == 0 and notice == 0:
            return 0.0

        return ice / (ice + notice)

def test():
    # test 1 - icy images

    print 'icy'

    for n in 1, 90, 180:

        image = os.path.join(os.environ['X2TD_ROOT'],
                             'Images', 'ICE', 'yellow3_1_%03d.img' % n)

        i = IceId()
        i.set_image(image)
        print i.search()

    # test2 - a not icy image

    print 'not icy'

    for n in range(1, 46):

        image = os.path.join(os.environ['X2TD_ROOT'],
                             'DL', 'insulin', 'images',
                             'insulin_1_%03d.img' % n)

        i = IceId()
        i.set_image(image)
        print i.search()


    return

def test_input():

    for image in sys.argv[1:]:
        i = IceId()
        i.set_image(image)
        print i.search()


if __name__ == '__main__':

    if len(sys.argv) == 1:
        test()

    else:
        test_input()
