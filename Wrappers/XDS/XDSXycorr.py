#!/usr/bin/env python
# XDSXycorr.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=XYCORR module in XDS.
#

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

def XDSXycorr(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSXycorr(DriverInstance.__class__,
                    FrameProcessor):
        '''A wrapper for wrapping XDS in xycorr mode.'''

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # now set myself up...
            
            self.set_executable('xds')

            # generic bits

            self._data_range = (0, 0)
            self._spot_range = [(0, 0)]
            self._background_range = (0, 0)
            self._resolution_range = (0, 0)

            return

        # this needs setting up from setup_from_image in FrameProcessor

        def run(self):
            '''Run xycorr.'''

            header = header_to_xds(self.get_header())

            name_template = os.path.join(self.get_directory(),
                                         self.get_template().replace('#', '?'))

            self.start()

            for record in header:
                self.input(header)

            self.input('NAME_TEMPLATE_OF_DATA_FRAMES=%s' % \
                       name_template)
            
            self.close_wait()

            for line in self.get_all_output():
                # do something

                pass

            return

    return XDSXycorrWrapper()


