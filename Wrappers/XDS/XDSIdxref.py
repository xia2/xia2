#!/usr/bin/env python
# XDSIdxref.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper to handle the JOB=IDXREF module in XDS.
#

import os
import sys
import math
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

# specific helper stuff
from XDSIdxrefHelpers import _parse_idxref_lp, _parse_idxref_lp_distance_etc
from Experts.LatticeExpert import SortLattices

# global flags
from Handlers.Flags import Flags

def XDSIdxref(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XDSIdxrefWrapper(DriverInstance.__class__,
                           FrameProcessor):
        '''A wrapper for wrapping XDS in idxref mode.'''

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)
            FrameProcessor.__init__(self)

            # now set myself up...
            
            
            self._parallel = Flags.get_parallel()

            if self._parallel < 1:
                self.set_executable('xds')
            else:
                self.set_executable('xds_par')

            # generic bits

            self._data_range = (0, 0)
            self._spot_range = []
            self._background_range = (0, 0)
            self._resolution_range = (0, 0)

            self._org = [0.0, 0.0]

            self._cell = None
            self._symm = 0

            # results

            self._refined_beam = (0, 0)
            self._refined_distance = 0

            self._indexing_solutions = { }

            self._indxr_input_lattice = None
            self._indxr_input_cell = None
            
            self._indxr_lattice = None
            self._indxr_cell = None
            self._indxr_mosaic = None

            self._input_data_files = { }
            self._output_data_files = { }

            self._input_data_files_list = ['SPOT.XDS']

            self._output_data_files_list = ['SPOT.XDS',
                                            'XPARM.XDS']

            return

        # getter and setter for input / output data

        def set_indexer_input_lattice(self, lattice):
            self._indxr_input_lattice = lattice
            return

        def set_indexer_input_cell(self, cell):
            if not type(cell) == type(()):
                raise RuntimeError, 'cell must be a 6-tuple de floats'

            if len(cell) != 6:
                raise RuntimeError, 'cell must be a 6-tuple de floats'

            self._indxr_input_cell = tuple(map(float, cell))
            return

        def set_input_data_file(self, name, data):
            self._input_data_files[name] = data
            return

        def get_output_data_file(self, name):
            return self._output_data_files[name]

        def get_refined_beam(self):
            return self._refined_beam

        def get_refined_distance(self):
            return self._refined_distance

        def get_indexing_solutions(self):
            return self._indexing_solutions

        def get_indexing_solution(self):
            return self._indxr_lattice, self._indxr_cell, self._indxr_mosaic

        # this needs setting up from setup_from_image in FrameProcessor

        def set_beam_centre(self, x, y):
            self._org = float(x), float(y)

        def set_data_range(self, start, end):
            self._data_range = (start, end)

        def add_spot_range(self, start, end):
            self._spot_range.append((start, end))

        def set_background_range(self, start, end):
            self._background_range = (start, end)

        def run(self):
            '''Run idxref.'''

            header = header_to_xds(self.get_header())

            xds_inp = open(os.path.join(self.get_working_directory(),
                                        'XDS.INP'), 'w')

            # what are we doing?
            xds_inp.write('JOB=IDXREF\n')
            xds_inp.write('MAXIMUM_NUMBER_OF_PROCESSORS=%d\n' % \
                          self._parallel) 
            
            # FIXME this needs to be calculated from the beam centre...
            
            xds_inp.write('ORGX=%f ORGY=%f\n' % \
                          tuple(self._org))

            lattice_to_spacegroup = {'aP':1,
                                     'mP':3,
                                     'mC':5,
                                     'oP':16,
                                     'oC':20,
                                     'oF':22,
                                     'oI':23,
                                     'tP':75,
                                     'tI':79,
                                     'hP':143,
                                     'hR':146,
                                     'cP':195,
                                     'cF':196,
                                     'cI':197}

            if self._indxr_input_cell:
                self._cell = self._indxr_input_cell
            if self._indxr_input_lattice:
                self._symm = lattice_to_spacegroup[self._indxr_input_lattice]

            xds_inp.write('SPACE_GROUP_NUMBER=%d\n' % self._symm)
            if self._cell:
                cell_format = '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f'
                xds_inp.write('UNIT_CELL_CONSTANTS=%s\n' % \
                              cell_format % self._cell)

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

            # copy the input file...
            shutil.copyfile(os.path.join(self.get_working_directory(),
                                         'XDS.INP'),
                            os.path.join(self.get_working_directory(),
                                         'IDXREF.INP'))

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

            # parse the output

            lp = open(os.path.join(
                self.get_working_directory(), 'IDXREF.LP'), 'r').readlines()

            self._idxref_data = _parse_idxref_lp(lp)

            for j in range(1, 45):
                if not self._idxref_data.has_key(j):
                    continue
                data = self._idxref_data[j]
                lattice = data['lattice']
                fit = data['fit']
                cell = data['cell']
                mosaic = data['mosaic']
                reidx = data['reidx']

                # only consider indexing solutions with goodness of fit < 30

                if fit < 30.0:
                    if self._indexing_solutions.has_key(lattice):
                        if self._indexing_solutions[lattice][
                            'goodness'] < fit:
                            continue
                        
                    self._indexing_solutions[lattice] = {
                        'goodness':fit,
                        'cell':cell}

            # get the highest symmetry "acceptable" solution
            
            list = [(k, self._indexing_solutions[k]['cell']) for k in \
                    self._indexing_solutions.keys()]

            # if there was a preassigned cell and symmetry return now
            # with everything done, else select the "top" solution and
            # reindex, resetting the input cell and symmetry.

            lattice_to_spacegroup = {'aP':1,
                                     'mP':3,
                                     'mC':5,
                                     'oP':16,
                                     'oC':20,
                                     'oF':22,
                                     'oI':23,
                                     'tP':75,
                                     'tI':79,
                                     'hP':143,
                                     'hR':146,
                                     'cP':195,
                                     'cF':196,
                                     'cI':197}
            
            if self._cell:

                # select the solution which matches the input unit cell

                for l in list:
                    if lattice_to_spacegroup[l[0]] == self._symm:
                        # this should be the correct solution...
                        # check the unit cell...
                        cell = l[1]

                        for j in range(6):
                            if math.fabs(cell[j] - self._cell[j]) > 5:
                                raise RuntimeError, 'bad unit cell in idxref'

                        self._indxr_lattice = l[0]
                        self._indxr_cell = l[1]
                        self._indxr_mosaic = mosaic

                        # return True
            
            else:

                # select the top solution as the input cell and reset the
                # "indexing done" flag
                    
                sorted_list = SortLattices(list)

                self._symm = lattice_to_spacegroup[sorted_list[0][0]]
                self._cell = sorted_list[0][1]

                return False

            
            # get the refined distance &c.

            beam, distance = _parse_idxref_lp_distance_etc(lp)

            self._refined_beam = beam
            self._refined_distance = distance
            
            # gather the output files

            for file in self._output_data_files_list:
                self._output_data_files[file] = open(os.path.join(
                    self.get_working_directory(), file), 'rb').read()

            return True

    return XDSIdxrefWrapper()

if __name__ == '__main__':

    idxref = XDSIdxref()
    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    
    idxref.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    # FIXED 12/DEC/06 need to work out how this is related to the beam centre
    # from labelit...
    
    for file in ['SPOT.XDS']:
        idxref.set_input_data_file(file, open(file, 'rb').read())

    idxref.set_beam_centre(1030, 1066)

    idxref.set_data_range(1, 1)
    idxref.set_background_range(1, 1)
    idxref.add_spot_range(1, 1)
    idxref.add_spot_range(90, 90)

    idxref.run()


