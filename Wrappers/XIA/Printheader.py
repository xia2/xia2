#!/usr/bin/env python
# Printheader.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
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

# FIXME this should probably be replaced with a module which uses the
# swig-python bindings of the DiffractionImage library directly.
# 
# FIXED 24/NOV/06 before running should check that the file actually 
#                 exists!
# 
# FIXME 24/NOV/06 if beam centre is 0.0, 0.0 then perhaps reset it to
#                 the centre of the image.
# 

import os
import sys
import copy
import time
import datetime
import math
import exceptions

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

# FIXME this does not include all MAR, RAXIS detectors

detector_class = {('adsc', 2304, 81):'adsc q4',
                  ('adsc', 1502, 163):'adsc q4 2x2 binned',
                  ('adsc', 4096, 51):'adsc q210',
                  ('adsc', 2048, 102):'adsc q210 2x2 binned',
                  ('adsc', 6144, 51):'adsc q315',
                  ('adsc', 3072, 102):'adsc q315 2x2 binned',
                  ('marccd', 4096, 73):'mar 300',
                  ('marccd', 3072, 73):'mar 225',
                  ('marccd', 2048, 79):'mar 165',
                  ('mar', 2300, 150):'mar 345',
                  ('raxis', 3000, 100):'raxis IV'}

def Printheader(DriverType = None):
    '''A factory for wrappers for the printheader.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class PrintheaderWrapper(DriverInstance.__class__):
        '''Provide access to the functionality in printheader.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('printheader')
            
            self._image = None
            self._header = { }

            return

        def set_image(self, image):
            '''Set an image to read the header of.'''
            self._image = image
            self._header = { }
            return

        def _get_time(self, datestring):
            '''Unpack a date string to a structure.'''

            if len(datestring) == 0:
                raise RuntimeError, 'empty date'

            if datestring == 'N/A':
                # we don't have the date!
                # set default to 0-epoch
                return datetime.datetime(1970, 1, 1, 1, 0, 0).timetuple()

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

            global detector_class
            
            # if we have the results already then don't bother
            # with the program
            if self._header:
                return copy.deepcopy(self._header)

            if HeaderCache.check(self._image):
                self._header = HeaderCache.get(self._image)
                return copy.deepcopy(self._header)

            # check that the input file exists..

            if not os.path.exists(self._image):
                raise RuntimeError, 'image %s does not exist' % \
                      self._image

            self.add_command_line(self._image)
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
                     'raxis':{'wavelength':1.0,
                             'pixel':1.0},
                     'marccd':{'wavelength':10.0,
                               'pixel':0.001},
                     'mar':{'wavelength':1.0,
                            'pixel':1.0}}

            for o in output:
                l = o.split(':')
                if 'Image type' in o:
                    self._header['detector'] = l[1].strip()
                    detector = self._header['detector']

                if 'Exposure epoch' in o:
                    try:
                        d = o[o.index(':') + 1:]
                        if d.strip():
                            self._header['epoch'] = self._epoch(d.strip())
                            self._header['date'] = self._date(d.strip())
                        else:
                            self._header['epoch'] = 0.0
                            self._header['date'] = ''
                    except exceptions.Exception, e:
                        # this is badly formed....
                        self._header['epoch'] = 0.0
                        self._header['date'] = ''

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

            # check to see if the beam centre needs to be converted
            # from pixels to mm - e.g. MAR 300 images from APS ID 23

            if self._header.has_key('beam') and \
               self._header.has_key('pixel') and \
               self._header.has_key('size'):
		# look to see if the current beam is somewhere in the middle
 		# pixel count wise...
		beam = self._header['beam']
		size = self._header['size']
                pixel = self._header['pixel']
                if math.fabs((beam[0] - 0.5 * size[0]) / size[0]) < 0.25:
                    new_beam = (beam[0] * pixel[0], beam[1] * pixel[1])
                    self._header['beam'] = new_beam

            # FIXME here - if the beam centre is exactly 0.0, 0.0,
            # then perhaps reset it to the centre of the image?
            
            if self._header.has_key('detector') and \
               self._header.has_key('pixel') and \
               self._header.has_key('size'):
                # compute the detector class
                detector = self._header['detector']
                width = int(self._header['size'][0])
                pixel = int(1000 * self._header['pixel'][0])

                key = (detector, width, pixel)

                try:
                    self._header['detector_class'] = detector_class[key]
                except:
                    print 'unknown key: ', key

            else:
                self._header['detector_class'] = 'unknown'

            HeaderCache.put(self._image, self._header)

            return copy.deepcopy(self._header)

    return PrintheaderWrapper()

if __name__ == '__main__':
    
    p = Printheader()

    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    if len(sys.argv) == 1:
        p.set_image(os.path.join(directory, '12287_1_E1_001.img'))
        print p.readheader()

    else:
        for image in sys.argv[1:]:
            p.set_image(image)

            header = p.readheader()
            
            print 'Frame %s collected at: %s' % \
                  (os.path.split(image)[-1], header['date'])
            print 'Phi:  %6.2f %6.2f' % \
                  (header['phi_start'], header['phi_end'])
            print 'Wavelength: %6.4f    Distance:   %6.2f' % \
                  (header['wavelength'], header['distance'])
