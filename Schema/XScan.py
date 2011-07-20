#!/usr/bin/env python
# XScan.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# A model for the scan for the "updated experimental model" project documented
# in internal ticket #1555. This is not designed to be used outside of the 
# XSweep classes.

import os
import sys
import pycbf
import math
import copy

from XScanHelpers import XScanHelperImageFiles
from XScanHelpers import XScanHelperImageFormats

class XScan:
    '''A class to represent the scan used to perform a rotation method X-ray
    diffraction experiment. In essence this is the information provided to the
    camera on where the images should go, how long the exposures should be
    and how the frames are formatted.'''
    
    def __init__(self, template, directory, format, image_range,
                 exposure_time, epochs):
        '''Construct a new scan class, which represents the information given
        to the camera to perform the diffraction experiment. N.B. though some
        of this information could be derived from image headers within the
        class it was felt to be more flexible to expose that kind of cleverness
        in factory functions. (i) format must be one of the types enumerated
        in XScanHelper.FORMAT_NAME (ii) Require that the exposure times and
        epochs are passed in as dictionaries incexed by image numbers in
        range image_range[0] to image_range[1] inclusive however (iii) do not
        presume in here that the images must exist when the XScan object is
        constructed.'''

        assert('#' in template)
        assert(os.path.exists(directory))
        assert(XScanHelperImageFormats.check_format(format))
        assert(len(image_range) == 2)
        assert(len(epochs) == (image_range[1] - image_range[0] + 1))
        
        self._template = template
        self._directory = directory
        self._format = format
        self._image_range = image_range
        self._exposure_time = exposure_time
        self._epochs = epochs
        
        return

    def __repr__(self):
        return '%s\n' % os.path.join(self._directory, self._template) + \
               '%d -> %d' % (self._image_range)

    def __cmp__(self, other):
        '''Comparison of this scan with another - which should be generally
        comparable, to allow for sorting.'''

        assert(self._template == other.get_template())
        assert(self._directory == other.get_directory())
        assert(self._format == other.get_format())
        assert(self._exposure_time == other.get_exposure_time())

        return self._image_range[0] - other.get_image_range()[0]

    def __add__(self, other):
        '''Return a new sweep which cosists of the contents of this sweep and
        the contents of the other sweep, provided that they are consistent -
        if they are not consistent (i.e. do not share the template, directory,
        format, exposure time and follow from one another) then an
        AssertionError will result.'''

        assert(self._template == other.get_template())
        assert(self._directory == other.get_directory())
        assert(self._format == other.get_format())
        assert(self._exposure_time == other.get_exposure_time())
        assert(self._image_range[1] + 1 == other.get_image_range()[0])

        new_image_range = (self._image_range[0], other.get_image_range()[1])
        new_epochs = copy.deepcopy(self._epochs)
        new_epochs.update(other.get_epochs())

        return XScan(self._template, self._directory, self._format,
                     new_image_range, self._exposure_time, new_epochs)
                     
    def get_template(self):
        '''Get the scan template.'''
        return self._template

    def get_directory(self):
        '''Get the scan directory.'''
        return self._directory

    def get_format(self):
        '''Get the image format for the images.'''
        return self._format

    def get_image_range(self):
        '''Get the image range (i.e. start, end inclusive) for this scan.'''
        return self._image_range

    def get_exposure_time(self):
        '''Get the exposure time used for these images.'''
        return self._exposure_time

    def get_epochs(self):
        '''Return the dictionary containing the image epochs.'''
        return self._epochs

    def get_image_name(self, index):
        '''Get the full image name for this image index.'''
        return XScanHelperImageFiles.template_directory_index_to_image(
            self._template, self._directory, self._image)

    def get_image_epoch(self, index):
        '''Get the epoch for this image.'''
        return self._epochs[index]

class XScanFactory:
    '''A factory for XScan instances, to help with constructing the classes
    in a set of common circumstances.'''

    @staticmethod
    def Single(filename, format, exposure_time, epoch):
        '''Construct an XScan instance for a single image.'''

        template, directory = \
                  XScanHelperImageFiles.image_to_template_directory(filename)
        index = XScanHelperImageFiles.image_to_index(filename)

        assert(XScanHelperImageFiles.template_directory_index_to_image(
            template, directory, index) == filename)
        
        return XScan(template, directory, format, (index, index),
                     exposure_time, {index:exposure_time})

