#!/usr/bin/env python
# XDSIntegrate.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=INTEGRATE module in XDS.
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
from XDS import header_to_xds, xds_check_version_supported

# specific helper stuff
from XDSIntegrateHelpers import _parse_integrate_lp

from Handlers.Streams import Chatter

def XDSIntegrate(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSIntegrateWrapper(DriverInstance.__class__,
                              FrameProcessor):
        '''A wrapper for wrapping XDS in integrate mode.'''

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # now set myself up...
            
            self.set_executable('xds')

            # generic bits

            self._data_range = (0, 0)
            self._resolution_range = (0, 0)

            self._input_data_files = { }
            self._output_data_files = { }

            self._input_data_files_list = ['X-CORRECTIONS.pck',
                                           'Y-CORRECTIONS.pck',
                                           'BLANK.pck',
                                           'BKGPIX.pck',
                                           'GAIN.pck',
                                           'XPARM.XDS']

            self._output_data_files_list = ['FRAME.pck']

            # note well - INTEGRATE.HKL is not included in this list
            # because it is likely to be very large - this is treated
            # separately...

            self._integrate_hkl = None

            return

        # getter and setter for input / output data

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data
            return

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def get_integrate_hkl(self):
            return self._integrate_hkl

        # this needs setting up from setup_from_image in FrameProcessor

        def set_data_range(self, start, end):
            self._data_range = (start, end)

        def run(self):
            '''Run integrate.'''

            header = header_to_xds(self.get_header())

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'XDS.INP'), 'w')

            # what are we doing?
            xds_inp.write('JOB=INTEGRATE\n')
            
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

            xds_inp.close()
            
            # write the input data files...

            for file in self._input_data_files_list:
                open(os.path.join(
                    self.get_working_directory(), file), 'wb').write(
                    self._input_data_files[file])

            self.start()
            self.close_wait()

            xds_check_version_supported(self.get_all_output())

            # tidy up...
            try:
                os.remove('xds-image-directory')
            except OSError, e:
                pass
            
            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = open(os.path.join(
                    self.get_working_directory(), file), 'rb').read()

            self._integrate_hkl = os.path.join(self.get_working_directory(),
                                               'INTEGRATE.HKL')

            stats = _parse_integrate_lp(os.path.join(
                self.get_working_directory(),
                'INTEGRATE.LP'))

            # analyse stats here, perhaps raising an exception if we
            # are unhappy with something, so that the indexing solution
            # can be eliminated in the integrater.

            images = stats.keys()
            images.sort()

            standard_deviations_spot_positions = [stats[i]['rmsd_pixel'] \
                                                  for i in images]

            low, high = min(standard_deviations_spot_positions), \
                        max(standard_deviations_spot_positions)          

            Chatter.write('Standard Deviation in pixel range: %f %f' % \
                          (low, high))

            if (high - low) / (0.5 * (high + low)) > 0.25:
                # there was a very large variation in deviation
                raise RuntimeError, 'very large variation in pixel deviation'

            return

    return XDSIntegrateWrapper()

if __name__ == '__main__':

    integrate = XDSIntegrate()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    
    integrate.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    for file in ['X-CORRECTIONS.pck',
                 'Y-CORRECTIONS.pck',
                 'BLANK.pck',
                 'BKGPIX.pck',
                 'GAIN.pck',
                 'XPARM.XDS']:
        integrate.set_input_data_file(file, open(file, 'rb').read())
    
    integrate.set_data_range(1, 1)

    integrate.run()


