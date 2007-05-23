#!/usr/bin/env python
# XDSCorrect.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=CORRECT module in XDS.
#
# 04/JAN/07 FIXME - need to know if we want anomalous pairs separating
#                   in this module...

import os
import sys
import shutil

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

def XDSCorrect(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSCorrectWrapper(DriverInstance.__class__,
                            FrameProcessor):
        '''A wrapper for wrapping XDS in correct mode.'''

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

            # specific information

            self._cell = None
            self._spacegroup_number = None

            self._reindex_matrix = None

            self._input_data_files = { }
            self._output_data_files = { }

            self._input_data_files_list = []

            self._output_data_files_list = ['GXPARM.XDS']

            # the following input files are also required:
            # 
            # INTEGRATE.HKL
            # REMOVE.HKL
            #
            # and XDS_ASCII.HKL is produced.

            # in
            self._integrate_hkl = None
            self._remove_hkl = None

            # out
            self._xds_ascii_hkl = None

            return

        # getter and setter for input / output data

        def set_spacegroup_number(self, spacegroup_number):
            self._spacegroup_number = spacegroup_number
            return

        def set_cell(self, cell):
            self._cell = cell
            return

        def set_reindex_matrix(self, reindex_matrix):
            if not len(reindex_matrix) == 12:
                raise RuntimeError, 'reindex matrix must be 12 numbers'
            self._reindex_matrix = reindex_matrix
            return

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data
            return

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def set_integrate_hkl(self, integrate_hkl):
            self._integrate_hkl = integrate_hkl
            return

        def set_remove_hkl(self, remove_hkl):
            self._remove_hkl = remove_hkl
            return

        def get_xds_ascii_hkl(self):
            return self._xds_ascii_hkl

        # this needs setting up from setup_from_image in FrameProcessor

        def set_data_range(self, start, end):
            self._data_range = (start, end)

        def add_spot_range(self, start, end):
            self._spot_range.append((start, end))

        def set_background_range(self, start, end):
            self._background_range = (start, end)

        def run(self):
            '''Run correct.'''

            # this is ok...
            # if not self._cell:
            # raise RuntimeError, 'cell not set'
            # if not self._spacegroup_number:
            # raise RuntimeError, 'spacegroup not set'

            header = header_to_xds(self.get_header())

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'XDS.INP'), 'w')

            # what are we doing?
            xds_inp.write('JOB=CORRECT\n')
            
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
            # for spot_range in self._spot_range:
            # xds_inp.write('SPOT_RANGE=%d %d\n' % spot_range)
            # xds_inp.write('BACKGROUND_RANGE=%d %d\n' % \
            # self._background_range)

            # assume for the moment anomalous data

            xds_inp.write('FRIEDEL\'S_LAW=FALSE\n')

            if self._spacegroup_number:
                xds_inp.write('SPACE_GROUP_NUMBER=%d\n' % \
                              self._spacegroup_number)
            if self._cell:
                xds_inp.write('UNIT_CELL_CONSTANTS=')
                xds_inp.write('%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f\n' % \
                              self._cell)
            if self._reindex_matrix:
                xds_inp.write('REIDX=%d %d %d %d %d %d %d %d %d %d %d %d' % \
                              map(int, self._reindex_matrix))
                

            xds_inp.close()
            
            # copy the input file...
            shutil.copyfile(os.path.join(self.get_working_directory(),
                                         'XDS.INP'),
                            os.path.join(self.get_working_directory(),
                                         'CORRECT.INP'))

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

            self._xds_ascii_hkl = os.path.join(
                self.get_working_directory(), 'XDS_ASCII.HKL')

            return

    return XDSCorrectWrapper()

if __name__ == '__main__':

    correct = XDSCorrect()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    correct.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    correct.set_data_range(1, 1)
    correct.set_background_range(1, 1)
    correct.add_spot_range(1, 1)

    correct.run()


