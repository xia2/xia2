#!/usr/bin/env python
# FormatRAXIS.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Implementation of an ImageFormat class to read RAXIS format image which,
# since it is only really used for one brand of detector, will be the only
# class in the pile.
# 
# Following taken from:
# 
# http://www.rigaku.com/downloads/software/readimage.html
# 
# Header Structure:
#
# First 256 bytes
# 
# 52 characters: name (10) version (10) xname (20) system (12)
# 6 floats: a, b, c, alpha, beta, gamma
# 12 characters: spacegroup
# float: mosaic
# 80 characters: notes
# 84 characters: padding
# 
# Next 256 bytes:
#
# 36 characters: date (12) username (20) target (4)
# float wavelength
# 20 character: typo of mono
# float: mono 2theta (degrees)
# 24 characters: collimator settings (20) filter type (4)
# 3 floats: distance, voltage, current
# 92 characters: focus stuff (12) xray chunder (80)
# long int: ipshape - 0 flat (good) 1 cylinder (bad)
# float weiss (1?)
# 56 characters: padding
#
# Next 256 bytes:
# 
# 8 bytes (xtal axes)
# 3 float - phi0, phistart, phiend
# long int frame no
# float exposure time (minutes!)
# 6 floats - beam x, beam z omega chi two theta mu
# 204 characters - padding
# 
# Next 256 bytes:
# 
# 2 long ints - nx, nz
# 2 float - pixel size
# 4 long, 3 float (not really useful)
# 20 char host (10) ip type (10)
# 3 long - scan order horizontal, vertical, back / front:
#
#  long  dr_x;    /* horizontal scanning code: 0=left->right, 1=>right->left */
#  long  dr_z;    /* vertical scanning code: 0=down->up, 1=up->down */
#  long  drxz;    /* front/back scanning code: 0=front, 1=back */
# 
# 2 useless floats
# 2 long - a magic number (useless) and number of gonio axies
# 15 floats - up to 5 goniometer axis vectors
# 5 floats - up to 5 start angles
# 5 floats - up to 5 end angles
# 5 floats - up to 5 offset values
# long - which axis is scan axis
# 40 characters - gonio axis names, space or comma separated
# 
# Then some more chunder follows - however I don't think it contains anything
# useful. So need to read first 1K of the image header.

from Toolkit.ImageFormat.Format import Format

class FormatRAXIS(Format):
    '''A class to support the RAXIS detector format from Rigaku.'''

    @staticmethod
    def understand(image_file):
        '''See if this looks like an RAXIS format image - clue is first
        5 letters of file should be RAXIS.'''

        if open(image_file).read(5) == 'RAXIS':
            return 2

        return 0

    def __init__(self, image_file):
        assert(FormatRAXIS.understand(image_file) > 0)

        Format.__init__(self, image_file)

        return

    def _setup(self):
        self._header_bytes = open(self._image_file).read(1024)

        if self._header_bytes[812:822].strip() == 'SGI':
            self._f = '>f'
            self._i = '>i'
        else:
            self._f = '<f'
            self._i = '<i'

        return

    def _xgoniometer(self):
        '''Return a model for the goniometer from the values stored in the
        header. Assumes same reference frame as is used for the Saturn
        instrument.'''

        
