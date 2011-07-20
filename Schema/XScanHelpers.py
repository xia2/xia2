#!/usr/bin/env python
# XScanHelpers.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#  
# Helpers for the XScan class, which are things for handling e.g. filenames,
# templates and so on. In first instance this will being in code from
# $XIA2_ROOT/Experts/FindImages.py as I will need it here too.

import os
import sys

assert('XIA2_ROOT' in os.environ)

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Experts.FindImages import image2template
from Experts.FindImages import image2image
from Experts.FindImages import image2template_directory
from Experts.FindImages import find_matching_images
from Experts.FindImages import template_directory_number2image
from Experts.FindImages import template_number2image

class XScanHelperImageFiles:
    '''A helper class which handles things like image names, making templates,
    finding matching images and so on. Currently this just provides aliases
    to existing functions elsewhere, but ultimately it would be good if they
    were all encapsulated herein.'''

    @staticmethod
    def image_to_template(filename):
        '''From an image name, return a file template which should match.'''
        return image2template(filename)

    @staticmethod
    def image_to_index(filename):
        '''From an image name, determine the index within the scan for this
        image, complementary to the image_to_template method above.'''
        return image2image(filename)

    @staticmethod
    def image_to_template_directory(filename):
        '''From a full path to an image, return the filename template and
        directory.'''
        return image2template_directory(filename)

    @staticmethod
    def template_directory_to_indices(template, directory):
        '''For a given template and directory, return a list of image indices
        which match. Also complementary with image_to_template_directory.'''
        return find_matching_images(template, directory)

    @staticmethod
    def template_directory_index_to_image(template, directory, index):
        '''Construct the full image name from the template, directory and
        file index.'''
        return template_directory_number2image(template, directory, index)

    @staticmethod
    def template_index_to_image(template, index):
        '''Construct the image file name from the template and file index.'''
        return template_number2image(template, index)

class XScanHelperImageFormats:
    '''A helper class which enxapsulates the allowed and supported image
    formats namely CBF, TIFF, SMV, RAXIS, MAR. N.B. there will be some
    crosstalk between this class and the ImageFormat classes.'''

    FORMAT_CBF = 'FORMAT_CBF'
    FORMAT_TIFF = 'FORMAT_TIFF'
    FORMAT_SMV = 'FORMAT_SMV'
    FORMAT_RAXIS = 'FORMAT_RAXIS'
    FORMAT_MAR = 'FORMAT_MAR'

    @staticmethod
    def check_format(format):
        if format in [XScanHelperImageFormats.FORMAT_CBF,
                      XScanHelperImageFormats.FORMAT_TIFF,
                      XScanHelperImageFormats.FORMAT_SMV,
                      XScanHelperImageFormats.FORMAT_RAXIS,
                      XScanHelperImageFormats.FORMAT_MAR]:
            return True

        return False

    
            

    
