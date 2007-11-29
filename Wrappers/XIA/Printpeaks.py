#!/usr/bin/env python
# Printpeaks.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 29th November 2007
# 
# A wrapper for the program "printpeaks" derived from the DiffractionImage
# code in XIA1 by Francois Remacle.
#

import os
import sys
import copy
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Printpeaks(DriverType = None):
    '''A factory for wrappers for the printpeaks.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class PrintpeaksWrapper(DriverInstance.__class__):
        '''Provide access to the functionality in printpeaks.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('printpeaks')
            
            self._image = None
            self._peaks = { }

            return

        def set_image(self, image):
            '''Set an image to read the header of.'''
            self._image = image
            self._peaks = { }
            return

        def printpeaks(self):
            '''Run printpeaks and get the list of peaks out, then decompose
            this to a histogram.'''

            if not self._image:
                raise RuntimeError, 'image not set'

            if not os.path.exists(self._image):
                raise RuntimeError, 'image %s does not exist' % \
                      self._image

            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            self.check_for_errors()            

            # results were ok, so get all of the output out
            output = self.get_all_output()

            peaks = []

            for record in output:

                if not 'Peak' in record[:4]:
                    continue

                intensity = float(record.split(':')[-1])
                peaks.append(intensity)

            # now construct the histogram

            log_max = int(math.log10(peaks[0])) + 1
            max_limit = int(math.pow(10.0, log_max))

            if False:

                limit = math.pow(10.0, log_max)

                while limit > 2.0:
                    self._peaks[limit] = len([j for j in peaks if j > limit])
                    limit *= 0.5

            else:
                
                for limit in [5, 10, 20, 50, 100, 200, 500, 1000]:
                    if limit > max_limit:
                        continue
                    self._peaks[float(limit)] = len(
                        [j for j in peaks if j > limit])
                    

            return self._peaks

    return PrintpeaksWrapper()

if __name__ == '__main__':
    
    p = Printpeaks()

    def printer(peaks):
        keys = peaks.keys()
        keys.sort()
        for k in keys:
            print '%.5f %d' % (k, peaks[k])

    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    if len(sys.argv) == 1:
        image = os.path.join(directory, '12287_1_E1_001.img')
        p.set_image(image)
        peaks = p.printpeaks()
        printer(peaks)
            
    else:
        for image in sys.argv[1:]:
            p.set_image(image)

            peaks = p.printpeaks()
            printer(peaks)
