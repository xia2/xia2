#!/usr/bin/env python
# Automask.py
#   Copyright (C) 2008 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 17th March 2008
#
# A wrapper for the program "automask" derived from the DiffractionImage
# code in XIA1 by Francois Remacle.
#

import os
import sys
import copy
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Automask(DriverType = None):
    '''A factory for wrappers for the automask.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class AutomaskWrapper(DriverInstance.__class__):
        '''Provide access to the functionality in automask.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('automask')

            self._image_list = []
            self._mask = { }

            # optional user input - to get the start position
            # right

            self._beam_mm = None
            self._beam_pixel = None

            # pieces of information which will be obtained from the
            # image headers (also used to check compatability) - needed
            # to correct information from the optional input above
            # and also to transform the derived mask into "mosflm"
            # coordinates

            self._pixel_size_x = None
            self._pixel_size_y = None
            self._size_x = None
            self._size_y = None
            self._distance = None

            return

        def set_beam(self, x, y):
            '''Set the beam centre - in what units??? dunno. In the mosflm
            units - this will mod them to the diffdump pixel coordinates.'''

            self._beam_mm = x, y

            # then convert to pixel coordinates - if available...

            return

        def add_image(self, image):
            '''Add an image for mask calculation.'''

            # if this is the first image, diffdump it and store the conversion
            # mm to pixel etc

            # if it is a later image, diffdump it and check that this is
            # ok - if not, raise ye exception while ye may

            self._image_list.append(image)

            return

        def automask(self):
            '''Run automask and find the masked areas.'''

            if not self._image_list:
                raise RuntimeError, 'no images assigned for analysis'

            for i in self._image_list:
                self.add_command_line(i)



    return AutomaskWrapper()

if __name__ == '__main__':

    directory = os.path.join(os.environ['X2TD_ROOT'],
                             'DL', 'insulin', 'images')

    a = Automask()
    a.add_image(os.path.join(directory, 'insulin_1_001.img'))
    a.add_image(os.path.join(directory, 'insulin_1_045.img'))
    a.automask()
