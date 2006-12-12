#!/usr/bin/env python
# XDSColspot.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=COLSPOT module in XDS.
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

# interfaces that this inherits from ...
from Schema.Interfaces.FrameProcessor import FrameProcessor

# generic helper stuff
from XDS import header_to_xds

def XDSColspot(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSColspotWrapper(DriverInstance.__class__,
                            FrameProcessor):
        '''A wrapper for wrapping XDS in colspot mode.'''

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # now set myself up...
            
            self.set_executable('xds')

            # generic bits

            self._data_range = (0, 0)
            self._spot_range = []
            self._background_range = (0, 0)
            self._resolution_range = (0, 0)

            return

        # this needs setting up from setup_from_image in FrameProcessor

        def set_data_range(self, start, end):
            self._data_range = (start, end)

        def add_spot_range(self, start, end):
            self._spot_range.append((start, end))

        def set_background_range(self, start, end):
            self._background_range = (start, end)

        def run(self):
            '''Run colspot.'''

            header = header_to_xds(self.get_header())

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'XDS.INP'), 'w')

            # what are we doing?
            xds_inp.write('JOB=COLSPOT\n')
            
            for record in header:
                xds_inp.write('%s\n' % record)

            name_template = os.path.join(self.get_directory(),
                                         self.get_template().replace('#', '?'))

            record = 'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
                     name_template

            if len(record) < 80:
                xds_inp.write(record)
                
            else:
                # else we need to make a softlink, then run, then remove 
                # softlink....

                try:
                    os.symlink(self.get_directory(),
                               'xds-image-directory')
                except OSError, e:
                    pass
                
                name_template = os.path.join('xds-image-directory',
                                             self.get_template().replace(
                    '#', '?'))
                record = 'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % \
                         name_template

                xds_inp.write(record)

            xds_inp.write('DATA_RANGE=%d %d\n' % self._data_range)
            for spot_range in self._spot_range:
                xds_inp.write('SPOT_RANGE=%d %d\n' % spot_range)
            xds_inp.write('BACKGROUND_RANGE=%d %d\n' % \
                          self._background_range)

            xds_inp.close()
            
            self.start()
            self.close_wait()

            for line in self.get_all_output():
                # fixme I need to look for errors in here
                print line[:-1]

            # tidy up...
            try:
                os.remove('xds-image-directory')
            except OSError, e:
                pass
            
            return

    return XDSColspotWrapper()

if __name__ == '__main__':

    colspot = XDSColspot()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    
    colspot.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    colspot.set_data_range(1, 1)
    colspot.set_background_range(1, 1)
    colspot.add_spot_range(1, 1)

    colspot.run()


