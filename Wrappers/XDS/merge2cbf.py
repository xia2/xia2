#!/usr/bin/env python
# merge2cbf.py
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper to handle the merge2cbf program that is distributed as part of
# the XDS package.
#

import os
import sys
import shutil

# We should really put these variable checks, etc in one centralised place
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
from Handlers.Streams import Debug

# global flags
from Handlers.Flags import Flags

def merge2cbf(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class merge2cbfWrapper(DriverInstance.__class__,
                           FrameProcessor):
        '''A wrapper for wrapping merge2cbf.'''

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # now set myself up...

            # I don't think there is a parallel version
            self.set_executable('merge2cbf')

            self._moving_average = False
            self._data_range = (0, 0)
            self._merge_n_images = 1
            self._input_data_files = { }
            self._output_data_files = { }

            self._input_data_files_list = []
            self._output_data_files_list = []

            return

        ## getter and setter for input / output data

        #def set_input_data_file(self, name, data):
            #self._input_data_files[name] = data
            #return

        #def get_output_data_file(self, name):
            #return self._output_data_files[name]

        # this needs setting up from setup_from_image in FrameProcessor

        def set_data_range(self, start, end):
            self._data_range = (start, end)

        def set_merge_n_images(self, n):
            self._merge_n_images = n

        def get_merge_n_images(self):
            return self._merge_n_images

        def set_moving_average(self, moving_average):
            assert moving_average in (True, False)
            self._moving_average = moving_average

        def get_moving_average(self):
            return self._moving_average

        def run(self):
            '''Run merge2cbf.'''

            # merge2cbf only requires mimimal information in the input file
            image_header = self.get_header()

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'MERGE2CBF.INP'), 'w')

            name_template = os.path.join(self.get_directory(),
                                         self.get_template().replace('#', '?'))

            output_template = os.path.join(self.get_working_directory(),
                                           'merge2cbf_averaged_????.cbf')

            xds_inp.write(
                'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' %name_template)

            xds_inp.write(
                'NAME_TEMPLATE_OF_OUTPUT_FRAMES=%s\n' %output_template)

            xds_inp.write(
                'NUMBER_OF_DATA_FRAMES_COVERED_BY_EACH_OUTPUT_FRAME=%s\n' %
                self.get_merge_n_images())

            xds_inp.write('DATA_RANGE=%d %d\n' % self._data_range)

            xds_inp.close()

            self.start()
            self.close_wait()

            xds_check_version_supported(self.get_all_output())

        def run_moving_average(self):
            '''Like the run method, but to create a sequence of moving average
               images.'''
            i_first, i_last = self._data_range
            n_output_images = (i_last - i_first) - self._merge_n_images + 1
            for i in range(i_first, i_first+n_output_images):
                self._data_range = (i, i+self._merge_n_images)
                self.run()
            # restore the original data range
            self._data_range = (i_first, i_last)

    return merge2cbfWrapper()

if __name__ == '__main__':

    m2c = merge2cbf()

    directory = '/Users/rjgildea/data/2013_05_23/insitu/thermolysin/F9/'

    m2c.setup_from_image(os.path.join(directory, 'app30_weak_F9d1_10_0001.cbf'))

    m2c.set_data_range(1, 50)
    m2c.set_merge_n_images(5)

    # Either do straight averaging:
    m2c.run()
    # or a moving average
    #m2c.run_moving_average()
