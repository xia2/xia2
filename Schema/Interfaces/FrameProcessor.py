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
# image header information [general c/f diffdump output]
#
# FIXME 06/SEP/06 Need to be able to interface to the XSweep
#                 object in here, to allow all of this information
#                 to be pulled automatically...
#                 No, don't do this, it will overcomplicate things.
#
# FIXME 07/OCT/10 Start adding support for a two-theta offset in the analysis.
#       N.B. this will involve a two-theta angle (fine) and axis (less fine).
#

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Experts.FindImages import image2template_directory, \
     template_directory_number2image, image2image, find_matching_images, \
     digest_template

from Wrappers.XIA.Diffdump import Diffdump

from Handlers.Streams import Debug

class FrameProcessor:
    '''A class to handle the information needed to process X-Ray
    diffraction frames.'''

    def __init__(self, image = None):

        self._fp_template = None
        self._fp_directory = None

        self._fp_matching_images = []

        self._fp_offset = 0

        self._fp_wavelength = None
        self._fp_distance = None
        self._fp_beam = None
        self._fp_reversephi = False
        self._fp_two_theta = 0.0
        self._fp_two_theta_prov = None

        self._fp_wavelength_prov = None
        self._fp_distance_prov = None
        self._fp_beam_prov = None

        self._fp_gain = 0.0
        self._fp_polarization = 0.0

        self._fp_header = { }

        # see FIXME for 06/SEP/06
        self._fp_xsweep = None

        # also need to keep track of allowed images in here
        self._fp_wedge = None

        # if image has been specified, construct much of this information
        # from the image

        if image:
            self._setup_from_image(image)

        return

    def set_template(self, template):
        self._fp_template = template
        return

    def set_frame_wedge(self, start, end):
        '''Set the allowed range of images for processing.'''

        start = start - self._fp_offset
        end = end - self._fp_offset

        self._fp_wedge = start, end

        if self._fp_matching_images:
            images = []
            for j in self._fp_matching_images:
                if j < start or j > end:
                    continue
                images.append(j)
            self._fp_matching_images = images

            # reload the header information as well - this will be
            # for the old wedge...

            # read the image header
            dd = Diffdump()
            dd.set_image(self.get_image_name(start))
            self._fp_header = dd.readheader()

            # print this to the debug channel
            Debug.write('Latest header information for image %d:' % start)
            keys = self._fp_header.keys()
            keys.sort()
            for k in keys:
                Debug.write('%s = %s' % (k, str(self._fp_header[k])))

            # populate wavelength, beam etc from this

            if self._fp_wavelength_prov is None or \
                            self._fp_wavelength_prov == 'header':
                self._fp_wavelength = self._fp_header['wavelength']
                self._fp_wavelength_prov = 'header'

            if self._fp_distance_prov is None or \
                            self._fp_distance_prov == 'header':
                self._fp_distance = self._fp_header['distance']
                self._fp_distance_prov = 'header'

            if self._fp_beam_prov is None or \
                            self._fp_beam_prov == 'header':
                self._fp_beam = tuple(map(float, self._fp_header['beam']))
                self._fp_beam_prov = 'header'


        return

    def get_frame_wedge(self):
        return self._fp_wedge

    def get_template(self):
        return self._fp_template

    def get_frame_offset(self):
        return self._fp_offset

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

    def set_polarization(self, polarization):
        self._fp_polarization = polarization
        return

    def get_polarization(self):
        return self._fp_polarization

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

    def set_reversephi(self, reversephi = True):
        self._fp_reversephi = reversephi
        return

    def get_reversephi(self):
        return self._fp_reversephi

    def set_two_theta(self, two_theta):
        self._fp_two_theta = two_theta
        self._fp_two_theta_prov = 'user'
        return

    def get_two_theta(self):
        return self._fp_two_theta

    def get_two_theta_prov(self):
        return self._fp_two_theta_prov

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

        # trim this down to only allowed images...
        if self._fp_wedge:
            start, end = self._fp_wedge
            images = []
            for j in self._fp_matching_images:
                if j < start or j > end:
                    continue
                images.append(j)
            self._fp_matching_images = images

        # read the image header
        dd = Diffdump()
        dd.set_image(image)
        self._fp_header = dd.readheader()

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
        if self._fp_two_theta_prov is None:
            self._fp_two_theta = self._fp_header['two_theta']
            self._fp_two_theta_prov = 'header'

        self.digest_template()

        return

    def digest_template(self):
        '''Strip out common characters from the image list and move them
        to the template.'''

        template, images, offset = digest_template(self._fp_template,
                                                   self._fp_matching_images)

        self._fp_template = template
        self._fp_matching_images = images
        self._fp_offset = offset

        return

    # end of class

if __name__ == '__main__':
    # run a quick test

    import sys

    fp = FrameProcessor(sys.argv[1])

    print fp.get_beam()
    print fp.get_wavelength()
    print fp.get_header()
    print fp.get_matching_images()
    print fp.get_two_theta()
