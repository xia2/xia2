#!/usr/bin/env python
# Printheader.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 14th June 2006
# 
# A wrapper for the program "printheader" derived from the DiffractionImage
# code in XIA1 by Francois Remacle.
#
# The output looks like...
# 
# > printheader 12287_1_E1_001.img 
# Image type : adsc
# Exposure epoch : Sun Sep 26 14:01:35 2004
# Exposure time : 5.000000
# Detector S/N : 445
# Wavelength : 0.979660
# Beam center : (105.099998,101.050003)
# Distance to detector : 170.000000 mm
# Image Size : (2048 px, 2048 px)
# Pixel Size : (0.102400 mm, 0.102400 mm)
# Angle range : 290.000000 -> 291.000000
# Two Theta value: N/A

import os
import sys
import copy
import time
import datetime

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

from Driver.DriverFactory import DriverFactory

class _HeaderCache:
    '''A cache for image headers.'''

    def __init__(self):
        self._headers = { }

    def put(self, image, header):
        self._headers[image] = copy.deepcopy(header)

    def get(self, image):
        return self._headers[image]

    def check(self, image):
        return self._headers.has_key(image)

HeaderCache = _HeaderCache()

def Printheader(DriverType = None):
    '''A factory for wrappers for the printheader.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class PrintheaderWrapper(DriverInstance.__class__):
        '''Provide access to the functionality in printheader.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.setExecutable('printheader')
            
            self._image = None
            self._header = { }

            return

        def setImage(self, image):
            '''Set an image to read the header of.'''
            self._image = image
            self._header = { }
            return

        def _get_time(self, datestring):
            '''Unpack a date string to a structure.'''

            if len(datestring) == 0:
                raise RuntimeError, 'empty date'

            try:
                struct_time = time.strptime(datestring)
            except:
                # this may be a mar format date...
                # MMDDhhmmYYYY.ss - go figure
                month = int(datestring[:2])
                day = int(datestring[2:4])
                hour = int(datestring[4:6])
                minute = int(datestring[6:8])
                year = int(datestring[8:12])
                second = int(datestring[-2:])
                d = datetime.datetime(year, month, day, hour, minute, second)
                struct_time = d.timetuple()

            return struct_time
        
        def _epoch(self, datestring):
            '''Compute an epoch from a date string.'''

            return time.mktime(self._get_time(datestring))

        def _date(self, datestring):
            '''Compute a human readable date from a date string.'''

            return time.asctime(self._get_time(datestring))

        def readheader(self):
            '''Read the image header.'''
            
            # if we have the results already then don't bother
            # with the program
            if self._header:
                return copy.deepcopy(self._header)

            if HeaderCache.check(self._image):
                self._header = HeaderCache.get(self._image)
                return copy.deepcopy(self._header)

            self.addCommand_line(self._image)
            self.start()
            self.close_wait()

            self.check_for_errors()            

            # results were ok, so get all of the output out
            output = self.get_all_output()

            # note that some of the records in the image header
            # will depend on the detector class - this should
            # really be fixed in the program printheader...

            detector = None
            
            fudge = {'adsc':{'wavelength':1.0,
                             'pixel':1.0},
                     'marccd':{'wavelength':10.0,
                               'pixel':0.001}}            

            for o in output:
                l = o.split(':')
                if 'Image type' in o:
                    self._header['detector'] = l[1].strip()
                    detector = self._header['detector']

                if 'Exposure epoch' in o:
                    d = o[o.index(':') + 1:]
                    self._header['epoch'] = self._epoch(d.strip())
                    self._header['date'] = self._date(d.strip())

                if 'Exposure time' in o:
                    self._header['exposure_time'] = float(l[1])

                if 'Wavelength' in o:
                    self._header['wavelength'] = float(l[1]) * \
                                                 fudge[detector]['wavelength']

                if 'Distance' in o:
                    self._header['distance'] = float(
                        l[1].replace('mm', '').strip())

                if 'Beam cent' in o:
                    beam = l[1].replace('(', '').replace(')', '').split(',')
                    self._header['beam'] = map(float, beam)

                if 'Image Size' in o:
                    image = l[1].replace('px', '')
                    image = image.replace('(', '').replace(')', '').split(',')
                    self._header['size'] = map(float, image)
                
                if 'Pixel Size' in o:
                    image = l[1].replace('mm', '')
                    x, y = image.replace('(', '').replace(')', '').split(',')
                    self._header['pixel'] = \
                                          (float(x) * fudge[detector]['pixel'],
                                           float(y) * fudge[detector]['pixel'])
                
                if 'Angle range' in o:
                    phi = map(float, l[1].split('->'))
                    self._header['phi_start'] = phi[0]
                    self._header['phi_end'] = phi[1]
                    self._header['phi_width'] = phi[1] - phi[0]

            HeaderCache.put(self._image, self._header)

            return copy.deepcopy(self._header)

    return PrintheaderWrapper()

if __name__ == '__main__':
    
    p = Printheader()

    directory = os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images')

    if len(sys.argv) == 1:
        p.setImage(os.path.join(directory, '12287_1_E1_001.img'))
        print p.readheader()

    else:
        for image in sys.argv[1:]:
            p.setImage(image)

            header = p.readheader()
            
            print 'Frame %s collected at: %s' % \
                  (os.path.split(image)[-1], header['date'])
            print 'Phi:  %6.2f %6.2f' % \
                  (header['phi_start'], header['phi_end'])
            print 'Wavelength: %6.4f    Distance:   %6.2f' % \
                  (header['wavelength'], header['distance'])
