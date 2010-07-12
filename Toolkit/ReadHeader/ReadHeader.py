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

class ReadHeader:
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
        
        self._beam_position_pixels_fast = None
        self._beam_position_pixels_slow = None

        # matters relating to the detector

        self._image_size_pixels_fast = None
        self._image_size_pixels_slow = None
        self._pixel_size_mm_fast = None
        self._pixel_size_mm_slow = None

        self._detector_gain = None

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
        # experimental frame
        
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

    

