#!/usr/bin/env python
# Format.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A top-level class to represent image formats which does little else but
# (i) establish an abstract class for what needs to be implemented and
# (ii) include the format registration code for any image formats which
# inherit from this. This will also contain links to the static methods
# from the X(component)Factories which will allow construction of e.g.
# goniometers etc. from the headers and hence a format specific factory.

import os
import sys

try:
    import bz2
except:
    bz2 = None

try:
    import gzip
except:
    gzip = None
    
import exceptions
import traceback

assert('XIA2_ROOT' in os.environ)

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# first - import access to all of the factories that we will be needing

from dxtbx.model.XGoniometer import XGoniometer, XGoniometerFactory
from dxtbx.model.XDetector import XDetector, XDetectorFactory
from dxtbx.model.XBeam import XBeam, XBeamFactory
from dxtbx.model.XScan import XScan, XScanFactory

class _MetaFormat(type):
    '''A metaclass for the Format base class (and hence all format classes)
    to allow autoregistration of the class implementations.'''

    def __init__(self, name, bases, attributes):
        super(_MetaFormat, self).__init__(name, bases, attributes)

        from dxtbx.format.Registry import Registry
        Registry.add(self)

        return

class Format:
    '''A base class for the representation and interrogation of diffraction
    image formats, from which all classes for reading the header should be
    inherited. This includes: autoregistration of implementation classes,
    stubs which need to be overridden and links to static factory methods
    which will prove to be useful in other implementations.'''

    __metaclass__ = _MetaFormat

    @staticmethod
    def understand(image_file):
        '''Overload this to publish whether this class instance understands
        a given file. N.B. to say that we really understand it, return a
        positive number. To say in a subclass that you understand it better
        then return a larger number, for example checking the detector serial
        number. Finally, if you are writing this subclass for a given
        instrument and you are given a different example return 0.'''
        
        return 0

    def __init__(self, image_file):
        '''Initialize a class instance from an image file.'''

        self._image_file = image_file
        
        self._xgoniometer_instance = None
        self._xdetector_instance = None
        self._xbeam_instance = None
        self._xscan_instance = None

        self._xgoniometer_factory = XGoniometerFactory
        self._xdetector_factory = XDetectorFactory
        self._xbeam_factory = XBeamFactory
        self._xscan_factory = XScanFactory

        self.setup()

        return

    def setup(self):
        '''Read the image file, construct the information which we will be
        wanting about the experiment from this. N.B. in your implementation
        of this you will probably want to make use of the static methods
        below and probably add some format parsing code too. Please also keep
        in mind that your implementation may be further subclassed by
        someone else.'''

        try:
            self._start()
            
            xgoniometer_instance = self._xgoniometer()
            assert(isinstance(xgoniometer_instance, XGoniometer))
            self._xgoniometer_instance = xgoniometer_instance
            
            xdetector_instance = self._xdetector()
            assert(isinstance(xdetector_instance, XDetector))
            self._xdetector_instance = xdetector_instance
            
            xbeam_instance = self._xbeam()
            assert(isinstance(xbeam_instance, XBeam))
            self._xbeam_instance = xbeam_instance

            xscan_instance = self._xscan()
            assert(isinstance(xscan_instance, XScan))
            self._xscan_instance = xscan_instance

        except exceptions.Exception, e:
            traceback.print_exc(sys.stderr)
        finally:
            self._end()

        return

    def get_xgoniometer(self):
        '''Get the standard XGoniometer instance which was derived from the
        image headers.'''

        return self._xgoniometer_instance

    def get_xdetector(self):
        '''Get the standard XDetector instance which was derived from the
        image headers.'''

        return self._xdetector_instance

    def get_xbeam(self):
        '''Get the standard XBeam instance which was derived from the image
        headers.'''

        return self._xbeam_instance

    def get_xscan(self):
        '''Get the standard XScan instance which was derived from the image
        headers.'''

        return self._xscan_instance

    def get_image_file(self):
        '''Get the image file provided to the constructor.'''

        return self._image_file

    # methods which must be overloaded in order to produce a useful Format
    # class implementation

    def _start(self):
        '''Start code for handling this image file, which may open a link
        to it once, say, and pass this around within the implementation.
        How you use this is up to you, though you probably want to overload
        it...'''

        return 

    def _end(self):
        '''Clean up things - keeping in mind that this should run even in the
        case of an exception being raised.'''

        return

    def _xgoniometer(self):
        '''Overload this method to read the image file however you like so
        long as the result is an XGoniometer.'''

        raise RuntimeError, 'overload me'

    def _xdetector(self):
        '''Overload this method to read the image file however you like so
        long as the result is an XDetector.'''

        raise RuntimeError, 'overload me'

    def _xbeam(self):
        '''Overload this method to read the image file however you like so
        long as the result is an XBeam.'''

        raise RuntimeError, 'overload me'

    def _xscan(self):
        '''Overload this method to read the image file however you like so
        long as the result is an XScan.'''

        raise RuntimeError, 'overload me'

    ####################################################################
    #                                                                  #
    # Helper functions for dealing with compressed images.             #
    #                                                                  #
    ####################################################################

    @staticmethod
    def is_bz2(filename):
        '''Check if a file pointed at by filename is bzip2 format.'''

        return 'BZh' in open(filename, 'rb').read(3)

    @staticmethod
    def is_gzip(filename):
        '''Check if a file pointed at by filename is gzip compressed.'''

        magic = open(filename, 'rb').read(2)

        return ord(magic[0]) == 0x1f and ord(magic[1]) == 0x8b

    @staticmethod
    def open_file(filename, mode = 'rb'):
        '''Open file for reading, decompressing silently if necessary.'''

        if Format.is_bz2(filename):

            if bz2 is None:
                raise RuntimeError, 'bz2 file provided without bz2 module'
            
            return bz2.BZ2File(filename, mode)

        if Format.is_gzip(filename):

            if gzip is None:
                raise RuntimeError, 'gz file provided without gzip module'

            return gzip.GzipFile(filename, mode)

        return open(filename, mode)

    

                
        
