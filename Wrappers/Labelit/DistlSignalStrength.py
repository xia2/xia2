#!/usr/bin/env python
# LabelitDistl.py
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 11th May 2010
# 
# A wrapper for the replacement for labelit.distl - distl.signal_strength. 
# This includes the added ability to get a list of the spot positions on
# the image. This can in turn replace printpeaks.
# 
# N.B. this is only included in more recent versions of Labelit.

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory

def DistlSignalStrength(DriverType = None):
    '''Factory for DistlSignalStrength wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class DistlSignalStrengthWrapper(DriverInstance.__class__):
        '''A wrapper for the program distl.signal_strength - which will provide
        functionality for looking for finding spots &c.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)

            self.set_executable('distl.signal_strength')

            self._image = None
            
            self._statistics = { } 
            self._peaks = []

            return

        def set_image(self, image):
            '''Set an image for analysis.'''

            self._image = image

            return

        def distl(self):
            '''Actually analyse the images.'''

            self.add_command_line(self._image)
            self.start()
            self.close_wait()

            # check for errors
            self.check_for_errors()

            # ok now we're done, let's look through for some useful stuff

            output = self.get_all_output()

            for o in output:
                l = o.split()

                if l[:2] == ['Spot', 'Total']:
                    self._statistics['spots_total'] = int(l[-1])
                if l[:2] == ['In-Resolution', 'Total']:
                    self._statistics['spots'] = int(l[-1])
                if l[:3] == ['Good', 'Bragg', 'Candidates']:
                    self._statistics['spots_good'] = int(l[-1])
                if l[:2] == ['Ice', 'Rings']:
                    self._statistics['ice_rings'] = int(l[-1])
                if l[:3] == ['Method', '1', 'Resolution']:
                    self._statistics['resol_one'] = float(l[-1])
                if l[:3] == ['Method', '2', 'Resolution']:
                    self._statistics['resol_two'] = float(l[-1])
                if l[:3] == ['%Saturation,', 'Top', '50']:
                    self._statistics[
                        'saturation'] = float(l[-1])
                
            return 'ok'
        

