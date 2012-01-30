#!/usr/bin/env cctbx.python
# ReadHeader.py
#
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A starting point for Python code to read image headers from a variety
# of normal image header types. Will be a replacement for the diffdump
# program and wrapper.

import os
import sys
import copy
import time
import datetime
import math
import exceptions
import binascii
import struct

detector_class = {('adsc', 2304, 81):'adsc q4',
                  ('adsc', 1152, 163):'adsc q4 2x2 binned',
                  ('adsc', 1502, 163):'adsc q4 2x2 binned',
                  ('adsc', 4096, 51):'adsc q210',
                  ('adsc', 2048, 102):'adsc q210 2x2 binned',
                  ('adsc', 6144, 51):'adsc q315',
                  ('adsc', 3072, 102):'adsc q315 2x2 binned',
                  ('adsc', 4168, 64):'adsc q270',
                  ('cbf', 2463, 172):'pilatus 6M',
                  ('mini-cbf', 2463, 172):'pilatus 6M',
                  ('dectris', 2527, 172):'pilatus 6M',
                  ('dectris', 1679, 172):'pilatus 2M',
                  ('marccd', 4096, 73):'mar 300 ccd',
                  ('marccd', 4096, 79):'mar 325 ccd',
                  ('marccd', 3072, 73):'mar 225 ccd',
                  ('marccd', 2048, 78):'mar 165 ccd',
                  ('marccd', 2048, 79):'mar 165 ccd',
                  ('marccd', 2048, 64):'mar 135 ccd',
                  ('mar', 4096, 73):'mar 300 ccd',
                  ('mar', 4096, 79):'mar 325 ccd',
                  ('mar', 3072, 73):'mar 225 ccd',
                  ('mar', 2048, 78):'mar 165 ccd',
                  ('mar', 2048, 79):'mar 165 ccd',
                  ('mar', 2048, 64):'mar 135 ccd',
                  ('mar', 1200, 150):'mar 180',
                  ('mar', 1600, 150):'mar 240',
                  ('mar', 2000, 150):'mar 300',
                  ('mar', 2300, 150):'mar 345',
                  ('mar', 3450, 100):'mar 345',
                  ('raxis', 3000, 100):'raxis IV',
                  ('rigaku', 3000, 100):'raxis IV',
                  ('saturn', 2048, 45):'rigaku saturn 92',
                  ('saturn', 1024, 90):'rigaku saturn 92 2x2 binned',
                  ('saturn', 2084, 45):'rigaku saturn 944',
                  ('saturn', 1042, 90):'rigaku saturn 944 2x2 binned',
                  ('rigaku', 2048, 45):'rigaku saturn 92',
                  ('rigaku', 1024, 90):'rigaku saturn 92 2x2 binned',
                  ('rigaku', 2084, 45):'rigaku saturn 944',
                  ('rigaku', 1042, 90):'rigaku saturn 944 2x2 binned'}

class ReadHeader(object):
    '''A generic class to handle the reading and handling of image
    headers. N.B. this can handle transformation to a standard reference
    frame, which will be defined in terms of the fast and slow direction of
    the image, in mm, with the origin being the outermost corner of the
    first pixel in the array:

    This corner:
      .
       [][][][][]
       [][][][][]
       [][][][][]
       [][][][][]
       [][][][][]

    Which will hopefully be transformable in and out of the usual image
    coordinate frames. N.B. could also specialise for a given instrument.'''

    def __init__(self):

        # matters relating to time

        self._epoch_unix = None
        self._epoch_ms = None
        self._date_gregorian = None
        self._date_struct = None

        self._exposure_time_s = None

        # matters relating to the experiment

        self._wavelength_angstroms = None
        self._distance_mm = None

        # matters relating to the beam centre

        self._beam_centre_pixels_fast = None
        self._beam_centre_pixels_slow = None

        # matters relating to the detector

        self._image_size_pixels_fast = None
        self._image_size_pixels_slow = None
        self._pixel_size_mm_fast = None
        self._pixel_size_mm_slow = None
        self._header_length = None
        self._image_length = None
        self._pixel_depth_bytes = None

        self._detector_gain = None
        self._image_offset = None
        self._maximum_value = None

        # matters relating to this oscillation

        self._osc_start_deg = None
        self._osc_width_deg = None

        # things which define the orientation of the sample

        self._angle_twotheta_deg = None
        self._angle_kappa_deg = None
        self._angle_chi_deg = None

        # and the rotation axis

        self._axis_name = None

        # the orientation of the beam, rotation axis and detector in the
        # experimental frame. N.B. many of these will be hard coded with
        # standard assumptions for that detector.

        self._axis_direction = None
        self._beam_direction = None
        self._fast_direction = None
        self._slow_direction = None

        # matters relating to this instrument - things which may be useful
        # for telling data processing programs what to do

        self._detector_name = None
        self._detector_format = None
        self._detector_serial_number = None

        return

    # begin very boring getter and setter code - using properties to make
    # the resulting code a little tidier.

    def set_epoch_unix(self, epoch_unix):
        self._epoch_unix = epoch_unix
        return

    def get_epoch_unix(self):
        return self._epoch_unix

    epoch_unix = property(get_epoch_unix, set_epoch_unix)

    def set_epoch_ms(self, epoch_ms):
        self._epoch_ms = epoch_ms
        return

    def get_epoch_ms(self):
        return self._epoch_ms

    epoch_ms = property(get_epoch_ms, set_epoch_ms)

    def set_date_gregorian(self, date_gregorian):
        self._date_gregorian = date_gregorian
        return

    def get_date_gregorian(self):
        return self._date_gregorian

    date_gregorian = property(get_date_gregorian, set_date_gregorian)

    def set_date_struct(self, date_struct):
        self._date_struct = date_struct
        self._date_gregorian = self._struct_to_date()
        self._epoch_unix = self._struct_to_epoch()
        return

    def get_date_struct(self):
        return self._date_struct

    date_struct = property(get_date_struct, set_date_struct)

    def set_exposure_time_s(self, exposure_time_s):
        self._exposure_time_s = exposure_time_s
        return

    def get_exposure_time_s(self):
        return self._exposure_time_s

    exposure_time_s = property(get_exposure_time_s, set_exposure_time_s)

    def set_wavelength_angstroms(self, wavelength_angstroms):
        self._wavelength_angstroms = wavelength_angstroms
        return

    def get_wavelength_angstroms(self):
        return self._wavelength_angstroms

    wavelength_angstroms = property(get_wavelength_angstroms,
                                    set_wavelength_angstroms)

    def set_distance_mm(self, distance_mm):
        self._distance_mm = distance_mm
        return

    def get_distance_mm(self):
        return self._distance_mm

    distance_mm = property(get_distance_mm, set_distance_mm)

    def set_beam_centre_pixels_fast(self, beam_centre_pixels_fast):
        self._beam_centre_pixels_fast = beam_centre_pixels_fast
        return

    def get_beam_centre_pixels_fast(self):
        return self._beam_centre_pixels_fast

    beam_centre_pixels_fast = property(get_beam_centre_pixels_fast,
                                       set_beam_centre_pixels_fast)

    def set_beam_centre_pixels_slow(self, beam_centre_pixels_slow):
        self._beam_centre_pixels_slow = beam_centre_pixels_slow
        return

    def get_beam_centre_pixels_slow(self):
        return self._beam_centre_pixels_slow

    beam_centre_pixels_slow = property(get_beam_centre_pixels_slow,
                                       set_beam_centre_pixels_slow)

    def set_image_size_pixels_fast(self, image_size_pixels_fast):
        self._image_size_pixels_fast = image_size_pixels_fast
        return

    def get_image_size_pixels_fast(self):
        return self._image_size_pixels_fast

    image_size_pixels_fast = property(get_image_size_pixels_fast,
                                      set_image_size_pixels_fast)

    def set_image_size_pixels_slow(self, image_size_pixels_slow):
        self._image_size_pixels_slow = image_size_pixels_slow
        return

    def get_image_size_pixels_slow(self):
        return self._image_size_pixels_slow

    image_size_pixels_slow = property(get_image_size_pixels_slow,
                                      set_image_size_pixels_slow)

    def set_pixel_size_mm_fast(self, pixel_size_mm_fast):
        self._pixel_size_mm_fast = pixel_size_mm_fast
        return

    def get_pixel_size_mm_fast(self):
        return self._pixel_size_mm_fast

    pixel_size_mm_fast = property(get_pixel_size_mm_fast,
                                  set_pixel_size_mm_fast)

    def set_pixel_size_mm_slow(self, pixel_size_mm_slow):
        self._pixel_size_mm_slow = pixel_size_mm_slow
        return

    def get_pixel_size_mm_slow(self):
        return self._pixel_size_mm_slow

    pixel_size_mm_slow = property(get_pixel_size_mm_slow,
                                  set_pixel_size_mm_slow)

    def set_header_length(self, header_length):
        self._header_length = header_length
        return

    def get_header_length(self):
        return self._header_length

    header_length = property(get_header_length, set_header_length)

    def set_image_length(self, image_length):
        self._image_length = image_length
        return

    def get_image_length(self):
        return self._image_length

    image_length = property(get_image_length, set_image_length)

    def set_pixel_depth_bytes(self, pixel_depth_bytes):
        self._pixel_depth_bytes = pixel_depth_bytes
        return

    def get_pixel_depth_bytes(self):
        return self._pixel_depth_bytes

    pixel_depth_bytes = property(get_pixel_depth_bytes,
                                 set_pixel_depth_bytes)

    def set_detector_gain(self, detector_gain):
        self._detector_gain = detector_gain
        return

    def get_detector_gain(self):
        return self._detector_gain

    detector_gain = property(get_detector_gain, set_detector_gain)

    def set_image_offset(self, image_offset):
        self._image_offset = image_offset
        return

    def get_image_offset(self):
        return self._image_offset

    image_offset = property(get_image_offset, set_image_offset)

    def set_maximum_value(self, maximum_value):
        self._maximum_value = maximum_value
        return

    def get_maximum_value(self):
        return self._maximum_value

    maximum_value = property(get_maximum_value, set_maximum_value)

    def set_osc_start_deg(self, osc_start_deg):
        self._osc_start_deg = osc_start_deg
        return

    def get_osc_start_deg(self):
        return self._osc_start_deg

    osc_start_deg = property(get_osc_start_deg, set_osc_start_deg)

    def set_osc_width_deg(self, osc_width_deg):
        self._osc_width_deg = osc_width_deg
        return

    def get_osc_width_deg(self):
        return self._osc_width_deg

    osc_width_deg = property(get_osc_width_deg, set_osc_width_deg)

    def set_angle_twotheta_deg(self, angle_twotheta_deg):
        self._angle_twotheta_deg = angle_twotheta_deg
        return

    def get_angle_twotheta_deg(self):
        return self._angle_twotheta_deg

    angle_twotheta_deg = property(get_angle_twotheta_deg,
                                  set_angle_twotheta_deg)

    def set_angle_kappa_deg(self, angle_kappa_deg):
        self._angle_kappa_deg = angle_kappa_deg
        return

    def get_angle_kappa_deg(self):
        return self._angle_kappa_deg

    angle_kappa_deg = property(get_angle_kappa_deg, set_angle_kappa_deg)

    def set_angle_chi_deg(self, angle_chi_deg):
        self._angle_chi_deg = angle_chi_deg
        return

    def get_angle_chi_deg(self):
        return self._angle_chi_deg

    angle_chi_deg = property(get_angle_chi_deg, set_angle_chi_deg)

    def set_axis_name(self, axis_name):
        self._axis_name = axis_name
        return

    def get_axis_name(self):
        return self._axis_name

    axis_name = property(get_axis_name, set_axis_name)

    def set_axis_direction(self, axis_direction):
        self._axis_direction = axis_direction
        return

    def get_axis_direction(self):
        return self._axis_direction

    axis_direction = property(get_axis_direction, set_axis_direction)

    def set_beam_direction(self, beam_direction):
        self._beam_direction = beam_direction
        return

    def get_beam_direction(self):
        return self._beam_direction

    beam_direction = property(get_beam_direction, set_beam_direction)

    def set_fast_direction(self, fast_direction):
        self._fast_direction = fast_direction
        return

    def get_fast_direction(self):
        return self._fast_direction

    fast_direction = property(get_fast_direction, set_fast_direction)

    def set_slow_direction(self, slow_direction):
        self._slow_direction = slow_direction
        return

    def get_slow_direction(self):
        return self._slow_direction

    slow_direction = property(get_slow_direction, set_slow_direction)

    def set_detector_name(self, detector_name):
        self._detector_name = detector_name
        return

    def get_detector_name(self):
        return self._detector_name

    detector_name = property(get_detector_name, set_detector_name)

    def set_detector_format(self, detector_format):
        self._detector_format = detector_format
        return

    def get_detector_format(self):
        return self._detector_format

    detector_format = property(get_detector_format, set_detector_format)

    def set_detector_serial_number(self, detector_serial_number):
        self._detector_serial_number = detector_serial_number
        return

    def get_detector_serial_number(self):
        return self._detector_serial_number

    detector_serial_number = property(get_detector_serial_number,
                                      set_detector_serial_number)

    # end of boring getter and setter code

    def _struct_to_epoch(self, struct = None, ms = None):
        '''Get the epoch from a date structure.'''

        if not struct:
            struct = self._date_struct

        if not ms:
            ms = self._epoch_ms

        if ms is None:
            ms = 0.0

        return time.mktime(struct) + ms

    def _struct_to_date(self, struct = None, ms = None):
        '''Get the date from a time structure.'''

        if not struct:
            struct = self._date_struct

        if not ms:
            ms = self._epoch_ms

        if ms is None:
            ms = 0.0

        return time.asctime(struct)

    def __str__(self):
        '''Print a summary of what we know about this image.'''

        result = 'Image size:  %6d x %6d\n' % \
                 (self.image_size_pixels_fast, self.image_size_pixels_slow)
        result += 'Pixel size:  %.4f x %.4f\n' % \
                  (self.pixel_size_mm_fast, self.pixel_size_mm_slow)
        result += 'Distance:    %.1f\n' % self.distance_mm
        result += 'Wavelength:  %.5f\n' % self.wavelength_angstroms
        result += 'Exposure:    %.3f\n' % self.exposure_time_s
        result += 'Oscillation: %.3f -> %.3f\n' % (
            self.osc_start_deg, self.osc_start_deg + self.osc_width_deg)
        result += 'Two Theta:   %.3f\n' % self.angle_twotheta_deg
        result += 'Trusted:     %d -> %d\n' % (self.image_offset,
                                               self.maximum_value)
        result += 'Beam:        %.1f %.1f\n' % (self.beam_centre_pixels_fast,
                                                self.beam_centre_pixels_slow)
        result += 'Date:        %s\n' % self.date_gregorian
        result += 'Serial No:   %s\n' % self.detector_serial_number

        return result
