#!/usr/bin/env python
# FrameProcessor.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
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

class FrameProcessor:
    '''A class to handle the information needed to process X-Ray
    diffraction frames.'''

    def __init__(self):

        self._fp_template = None
        self._fp_directory = None

        self._fp_wavelength = None
        self._fp_distance = None
        self._fp_beam = None

        self._fp_header = { }

    def setTemplate(self, template):
        self._fp_template = template
        return

    def getTemplate(self):
        return self._fp_template

    def setDirectory(self, directory):
        self._fp_directory = directory
        return

    def getDirectory(self):
        return self._fp_directory

    def setWavelength(self, wavelength):
        self._fp_wavelength = wavelength
        return

    def getWavelength(self):
        return self._fp_wavelength

    def setDistance(self, distance):
        self._fp_distance = distance
        return

    def getDistance(self):
        return self._fp_distance

    def setBeam(self, beam):
        self._fp_beam = beam
        return

    def getBeam(self):
        return self._fp_beam

    def setHeader(self, header):
        self._fp_header = header
        return

    def getHeader(self):
        return self._fp_header

    def getHeader_item(self, item):
        return self._fp_header[item]

    # end of class



    
