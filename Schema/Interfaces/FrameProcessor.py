#!/usr/bin/env python
# FrameProcessor.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# An interface for programs which process X-Ray diffraction images.
# This adds the code for handling the templates, directories etc.
# but not the use of them e.g. the keyworded input.
# 
# This is a virtual class - and should be inherited from only for the
# purposes of using the methods.
# 
# The following are considered critical to this class:
# 
# Template, directory. Template in the form ### not ???
# Distance (mm), wavelength (ang), beam centre (mm, mm),
# image header information [general c/f printheader output]
# 
# FIXME 06/SEP/06 Need to be able to interface to the XSweep
#                 object in here, to allow all of this information
#                 to be pulled automatically...
#                 No, don't do this, it will overcomplicate things.

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Experts.FindImages import image2template_directory, \
     template_directory_number2image, image2image, find_matching_images
from Wrappers.XIA.Printheader import Printheader

class FrameProcessor:
    '''A class to handle the information needed to process X-Ray
    diffraction frames.'''

    def __init__(self, image = None):

        self._fp_template = None
        self._fp_directory = None

        self._fp_matching_images = []

        self._fp_wavelength = None
        self._fp_distance = None
        self._fp_beam = None

        self._fp_wavelength_prov = None
        self._fp_distance_prov = None
        self._fp_beam_prov = None

        self._fp_gain = 0.0

        self._fp_header = { }

        # see FIXME for 06/SEP/06
        self._fp_xsweep = None

        # if image has been specified, construct much of this information
        # from the image

        if image:
            self._setup_from_image(image)

        return

    def set_template(self, template):
        self._fp_template = template
        return

    def get_template(self):
        return self._fp_template

    def set_directory(self, directory):
        self._fp_directory = directory
        return

    def get_directory(self):
        return self._fp_directory

    def get_matching_images(self):
        return self._fp_matching_images

    def set_wavelength(self, wavelength):
        self._fp_wavelength = wavelength
        self._fp_wavelength_prov = 'user'
        return

    def get_wavelength(self):
        return self._fp_wavelength

    def get_wavelength_prov(self):
        return self._fp_wavelength_prov

    def set_distance(self, distance):
        self._fp_distance = distance
        self._fp_distance_prov = 'user'
        return

    def get_distance(self):
        return self._fp_distance

    def set_gain(self, gain):
        self._fp_gain = gain
        return

    def get_gain(self):
        return self._fp_gain

    def get_distance_prov(self):
        return self._fp_distance_prov

    def set_beam(self, beam):
        self._fp_beam = beam
        self._fp_beam_prov = 'user'
        return

    def get_beam(self):
        return tuple(self._fp_beam)

    def get_beam_prov(self):
        return self._fp_beam_prov

    def set_header(self, header):
        self._fp_header = header
        return

    def get_header(self):
        return self._fp_header

    def get_header_item(self, item):
        return self._fp_header[item]

    # utility functions
    def get_image_name(self, number):
        '''Convert an image number into a name.'''

        return template_directory_number2image(self.get_template(),
                                               self.get_directory(),
                                               number)

    def get_image_number(self, image):
        '''Convert an image name to a number.'''

        if type(image) == type(1):
            return image

        # FIXME HACK - if this is the first run, presume that this
        # can be used to configure the template &c.
        # FIXME DOC this means that a FrameProcessor must deal only ever
        # with one sweep.

        # FIXED - now removed, because setup_from_image is public and
        # the preferred way of accessing this functionality.
        # if not self._fp_template and not self._fp_directory:
        # self._setup_from_image(image)

        return image2image(image)
                                               
    # FIXME should this be public??
    def setup_from_image(self, image):
        if self._fp_template and self._fp_directory:
            raise RuntimeError, 'FrameProcessor implementation already set up'
        
        self._setup_from_image(image)

    # private methods

    def _setup_from_image(self, image):
        '''Configure myself from an image name.'''
        template, directory = image2template_directory(image)
        self._fp_template = template
        self._fp_directory = directory

        self._fp_matching_images = find_matching_images(template, directory)

        # read the image header
        ph = Printheader()
        ph.set_image(image)
        self._fp_header = ph.readheader()

        # populate wavelength, beam etc from this
        if self._fp_wavelength_prov is None:
            self._fp_wavelength = self._fp_header['wavelength']
            self._fp_wavelength_prov = 'header'
        if self._fp_distance_prov is None:
            self._fp_distance = self._fp_header['distance']
            self._fp_distance_prov = 'header'
        if self._fp_beam_prov is None:
            self._fp_beam = tuple(map(float, self._fp_header['beam']))
            self._fp_beam_prov = 'header'

        return

    # end of class

if __name__ == '__main__':
    # run a quick test


    fp = FrameProcessor(os.path.join(os.environ['XIA2_ROOT'],
                                     'Data', 'Test', 'Images',
                                     '12287_1_E1_001.img'))

    print fp.get_beam()
    print fp.get_wavelength()
    print fp.get_header()
    print fp.get_matching_images()
    
    

    
