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
import time
import datetime

from XScanHelpers import XScanHelperImageFiles
from XScanHelpers import XScanHelperImageFormats

class XScan:
    '''A class to represent the scan used to perform a rotation method X-ray
    diffraction experiment. In essence this is the information provided to the
    camera on where the images should go, how long the exposures should be
    and how the frames are formatted.'''
    
    def __init__(self, template, directory, format, image_range,
                 exposure_time, oscillation, epochs):
        '''Construct a new scan class, which represents the information given
        to the camera to perform the diffraction experiment. N.B. though some
        of this information could be derived from image headers within the
        class it was felt to be more flexible to expose that kind of cleverness
        in factory functions. (i) format must be one of the types enumerated
        in XScanHelper.FORMAT_NAME (ii) Require that the exposure times and
        epochs are passed in as dictionaries incexed by image numbers in
        range image_range[0] to image_range[1] inclusive however (iii) do not
        presume in here that the images must exist when the XScan object is
        constructed. N.B. also now include the oscillation as a (start, width)
        tuple corresponding to the first image in the scan. It is implied that
        subsequent images will be continuous with this, sharing the same
        oscillation width.'''

        assert('#' in template)
        assert(os.path.exists(directory))
        assert(XScanHelperImageFormats.check_format(format))
        assert(len(image_range) == 2)
        assert(len(oscillation) == 2)
        assert(len(epochs) == (image_range[1] - image_range[0] + 1))
        
        self._template = template
        self._directory = directory
        self._format = format
        self._image_range = image_range
        self._exposure_time = exposure_time
        self._oscillation = oscillation
        self._epochs = epochs
        
        return

    def __repr__(self):

        return '%s\n' % os.path.join(self._directory, self._template) + \
               '%d -> %d\n' % (self._image_range) + \
               '%.3f -> %.3f\n' % (self.get_oscillation_range()) + \
               '%s' % self.get_image_time(self._image_range[0])

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
        assert(math.fabs(self.get_oscillation_range()[1] -
                         other.get_oscillation_range()[0]) < 0.001)
        assert(math.fabs(self.get_oscillation()[1] -
                         other.get_oscillation()[1]) < 0.001)

        new_image_range = (self._image_range[0], other.get_image_range()[1])
        new_epochs = copy.deepcopy(self._epochs)
        new_epochs.update(other.get_epochs())

        return XScan(self._template, self._directory, self._format,
                     new_image_range, self._exposure_time,
                     self._oscillation, new_epochs)

    def __getitem__(self, index):
        '''Implement ability to get an XScan object corresponding to a single
        image in the scan. N.B. this is slightly complex as we need to support
        single indices and slice objects. If index has attribute start is
        assumed to be a slice. N.B. these all operate on the IMAGE INDEX
        rather than behaving like a list.'''

        if type(index) == type(1):

            assert(not index < self._image_range[0])
            assert(not index > self._image_range[1])
            
            return XScan(self._template, self._directory, self._format,
                         (index, index), self._exposure_time,
                         self.get_oscillation(index),
                         {index:self._epochs[index]})

        if hasattr(index, 'start'):
            assert(index.step is None)

            start = index.start
            stop = index.stop

            # work around unspecified image ranges i.e. [:10]

            if start == 0:
                start = self._image_range[0]
                
            if stop == sys.maxint:
                stop = self._image_range[1]

            assert(not start < self._image_range[0])
            assert(not stop > self._image_range[1])

            new_epochs = { }

            for i in range(start, stop + 1):
                new_epochs[i] = self._epochs[i]

            return XScan(self._template, self._directory, self._format,
                         (start, stop), self._exposure_time,
                         self.get_oscillation(start), new_epochs)

        raise TypeError, 'useless index: %s' % type(index)
                     
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

    def get_oscillation(self, index = None):
        '''Get the oscillation start and width for a given frame in the
        scan.'''

        if index is None:
            return self._oscillation

        assert(not index < self._image_range[0])
        assert(not index > self._image_range[1])

        offset = (index - self._image_range[0]) * self._oscillation[1]
        
        return (self._oscillation[0] + offset, self._oscillation[1])

    def get_oscillation_range(self):
        '''Return the overall range of this scan.'''

        range = (self._image_range[1] - self._image_range[0] + 1) * \
                self._oscillation[1]
        
        return (self._oscillation[0], self._oscillation[0] + range)
        
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

    def get_image_time(self, index):
        '''Get the time for this which is the epoch translated into a human
        readable form.'''

        return time.asctime(time.gmtime(self._epochs[index]))

class XScanFactory:
    '''A factory for XScan instances, to help with constructing the classes
    in a set of common circumstances.'''

    @staticmethod
    def Single(filename, format, exposure_time, osc_start, osc_width, epoch):
        '''Construct an XScan instance for a single image.'''

        template, directory = \
                  XScanHelperImageFiles.image_to_template_directory(filename)
        index = XScanHelperImageFiles.image_to_index(filename)

        assert(XScanHelperImageFiles.template_directory_index_to_image(
            template, directory, index) == filename)
        
        return XScan(template, directory, format, (index, index),
                     exposure_time, (osc_start, osc_width), {index:epoch})

    @staticmethod
    def Sum(xscans):
        '''Sum a list of scans wrapping the sligtly clumsy idiomatic method:
        sum(xscans[1:], xscans[0]).'''

        for xscan in xscans:
            assert(xscan.__class__ == XScan)

        return sum(xscans[1:], xscans[0])

    @staticmethod
    def Search(filename):
        '''Get a list of files which appear to match the template and
        directory implied by the input filename. This could well be used
        to get a list of image headers to read and hence construct XScans
        from.'''

        template, directory = \
                  XScanHelperImageFiles.image_to_template_directory(filename)

        indices = XScanHelperImageFiles.template_directory_to_indices(
            template, directory)

        return [XScanHelperImageFiles.template_directory_index_to_image(
            template, directory, index) for index in indices]

    @staticmethod
    def Format(name):
        '''Return the correct format token for a given name, for example:

        cbf, CBF
        smv, SMV
        tiff, tif, TIFF
        raxis, RAXIS
        mar, MAR

        to the appropriate static token which will be used as a handle
        everywhere else in this.'''
        
        if name.upper() == 'CBF':
            return XScanHelperImageFormats.FORMAT_CBF
        elif name.upper() == 'SMV':
            return XScanHelperImageFormats.FORMAT_SMV
        elif name.upper() == 'TIF' or name.upper() == 'TIFF':
            return XScanHelperImageFormats.FORMAT_TIFF
        elif name.upper() == 'RAXIS':
            return XScanHelperImageFormats.FORMAT_RAXIS
        elif name.upper() == 'MAR':
            return XScanHelperImageFormats.FORMAT_MAR

        raise RuntimeError, 'name %s not known' % name

    @staticmethod
    def Epoch(date_string):
        '''Interpret a standard time string and get the corresponding epoch.'''

        return time.mktime(time.strptime(date_string))

            
