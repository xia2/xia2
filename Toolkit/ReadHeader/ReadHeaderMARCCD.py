#!/usr/bin/env cctbx.python
# ReadHeaderMARCCD.py
# 
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Code to read an MARCCD image header and populate the contents of the standard
# image header ReadHeader class.

import os
import sys
import copy
import time
import datetime
import math
import exceptions
import binascii
import struct

from ReadHeader import ReadHeader

class ReadHeaderMARCCD(ReadHeader):
    '''A class to read MARCCD image headers.'''

    def __init__(self, image = None):
        ReadHeader.__init__(self)

        if image:
            self._read_marccd_header(image)

        return

    def _read_marccd_header(self, image):
        '''Read the contents of the header of this image.'''

        marccd_header_bytes = open(image, 'rb').read(4096)[1024:]

        # first determine if the header byte order is little endian or
        # big endian
        
        byte_order = struct.unpack('I', marccd_header_bytes[28:32])[0]

        little_endian = 1234
        big_endian = 4321

        # if this is the native byte order it will have been correctly read
        # as one or the other of these values 

        if byte_order == little_endian or byte_order == big_endian:
            header_unsigned_ints = struct.unpack('768I', marccd_header_bytes)
        else:
            header_unsigned_ints = struct.unpack('768I', marccd_header_bytes)
            header_array = array.array('I', header_unsigned_ints)
            header_array.byteswap()
            header_unsigned_ints = tuple(header_array)

        nfast, nslow = header_unsigned_ints[20], header_unsigned_ints[21]

        print nfast, nslow



    def __str__(self):
        return ''


if __name__ == '__main__':

    import sys

    for arg in sys.argv[1:]:
        print ReadHeaderMARCCD(arg)
        
        
