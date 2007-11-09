#!/usr/bin/env python
# XDSIndexer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 13th December 2006
# 
# An implementation of the Indexer interface using XDS. This depends on the
# XDS wrappers to actually implement the functionality.
#
# 03/JAN/07 FIXME - once the indexing step is complete, all of the files
#                   which are needed for integration should be placed in the 
#                   indexer "payload".

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# wrappers for programs that this needs

from Wrappers.XDS.XDSXycorr import XDSXycorr as _Xycorr
from Wrappers.XDS.XDSInit import XDSInit as _Init
from Wrappers.XDS.XDSColspot import XDSColspot as _Colspot
from Wrappers.XDS.XDSIdxref import XDSIdxref as _Idxref

from Wrappers.XIA.Diffdump import Diffdump

# helper functions

from Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from Wrappers.XDS.XDS import beam_centre_xds_to_mosflm
from Wrappers.XDS.XDS import XDSException

# interfaces that this must implement to be an indexer

from Schema.Interfaces.Indexer import Indexer
from Schema.Interfaces.FrameProcessor import FrameProcessor

# odds and sods that are needed

from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter, Debug
from Handlers.Flags import Flags

class XDSIndexer(FrameProcessor,
                 Indexer):
    '''An implementation of the Indexer interface using XDS.'''

    def __init__(self):

        # set up the inherited objects
        
        FrameProcessor.__init__(self)
        Indexer.__init__(self)

        # check that the programs exist - this will raise an exception if
        # they do not...

        idxref = _Idxref()

        # admin junk
        self._working_directory = os.getcwd()

        # place to store working data
        self._data_files = { }

        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    # factory functions

    def Xycorr(self):
        xycorr = _Xycorr()
        xycorr.set_working_directory(self.get_working_directory())

        xycorr.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            xycorr.set_distance(self.get_distance())

        if self.get_wavelength():
            xycorr.set_wavelength(self.get_wavelength())

        auto_logfiler(xycorr, 'XYCORR')

        return xycorr

    def Init(self):
        init = _Init()
        init.set_working_directory(self.get_working_directory())

        init.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            init.set_distance(self.get_distance())

        if self.get_wavelength():
            init.set_wavelength(self.get_wavelength())

        auto_logfiler(init, 'INIT')

        return init

    def Colspot(self):
        colspot = _Colspot()
        colspot.set_working_directory(self.get_working_directory())

        colspot.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            colspot.set_distance(self.get_distance())

        if self.get_wavelength():
            colspot.set_wavelength(self.get_wavelength())

        auto_logfiler(colspot, 'COLSPOT')

        return colspot

    def Idxref(self):
        idxref = _Idxref()
        idxref.set_working_directory(self.get_working_directory())

        idxref.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        if self.get_distance():
            idxref.set_distance(self.get_distance())

        if self.get_wavelength():
            idxref.set_wavelength(self.get_wavelength())

        auto_logfiler(idxref, 'IDXREF')

        return idxref

    # helper functions

    def _index_select_images(self):
        '''Select correct images based on image headers.'''
        
        phi_width = self.get_header_item('phi_width')
        
        if phi_width == 0.0:
            Debug.write('Phi width 0.0? Assuming 1.0!')
            phi_width = 1.0

        images = self.get_matching_images()

        # characterise the images - are there just two (e.g. dna-style
        # reference images) or is there a full block?

        if len(images) < 3:
            # work on the assumption that this is a reference pair
        
            self.add_indexer_image_wedge(images[0])
            if len(images) > 1:
                self.add_indexer_image_wedge(images[-1])

        else:
            # work on the assumption that this is a full sweep of images
            # so I can use two blocks... of 5 degrees - perhaps this should
            # be three blocks? testing with 5 degrees, used to be 3.

            # five degree blocks are excessive - especially if we have 0.1
            # degree oscillations => just use 5 image blocks...
            
            block_size = 5

            Debug.write('Adding images for indexer: %d -> %d' % \
                        (images[0], images[block_size] - 1))

            self.add_indexer_image_wedge((images[0], images[block_size] - 1))

            if int(90.0 / phi_width) + block_size in images:
                # assume we can add a wedge around 45 degrees as well...
                Debug.write('Adding images for indexer: %d -> %d' % \
                            (int(45.0 / phi_width) + 1,
                             int(45.0 / phi_width) +
                             block_size))
                Debug.write('Adding images for indexer: %d -> %d' % \
                            (int(90.0 / phi_width) + 1,
                             int(90.0 / phi_width) +
                             block_size))
                self.add_indexer_image_wedge((int(45.0 / phi_width) + 1,
                                              int(45.0 / phi_width) +
                                              block_size))
                self.add_indexer_image_wedge((int(90.0 / phi_width) + 1,
                                              int(90.0 / phi_width) +
                                              block_size))
                
            else:

                # add some half-way anyway
                first = (len(images) / 2) - (block_size / 2) + 1
                last = first + block_size - 1

                Debug.write('Adding images for indexer: %d -> %d' % \
                            (first, last))
                self.add_indexer_image_wedge((first, last))
                Debug.write('Adding images for indexer: %d -> %d' % \
                            (images[- block_size], images[-1]))
                self.add_indexer_image_wedge((images[- block_size],
                                              images[-1]))
            
        return

    # do-er functions

    def _index_prepare(self):
        '''Prepare to do autoindexing - in XDS terms this will mean
        calling xycorr, init and colspot on the input images.'''

        # decide on images to work with

        Debug.write('XDS INDEX PREPARE:')
        Debug.write('Wavelength: %.6f' % self.get_wavelength())
        Debug.write('Distance: %.2f' % self.get_distance())

        if self._indxr_images == []:
            # note well that this may reset the "done" flag so
            # override this...
            self._index_select_images()
            self.set_indexer_prepare_done(True)
            
        all_images = self.get_matching_images()

        first = min(all_images)
        last = max(all_images)

        # next start to process these - first xycorr

        xycorr = self.Xycorr()

        xycorr.set_data_range(first, last)
        xycorr.set_background_range(self._indxr_images[0][0],
                                    self._indxr_images[0][1])
        for block in self._indxr_images:
            xycorr.add_spot_range(block[0], block[1])

        # FIXME need to set the origin here

        xycorr.run()

        for file in ['X-CORRECTIONS.pck',
                     'Y-CORRECTIONS.pck']:
            self._data_files[file] = xycorr.get_output_data_file(file)

        # next start to process these - then init

        init = self.Init()

        for file in ['X-CORRECTIONS.pck',
                     'Y-CORRECTIONS.pck']:
            init.set_input_data_file(file, self._data_files[file])

        init.set_data_range(first, last)
        init.set_background_range(self._indxr_images[0][0],
                                  self._indxr_images[0][1])
        for block in self._indxr_images:
            init.add_spot_range(block[0], block[1])

        init.run()

        for file in ['BLANK.pck',
                     'BKGINIT.pck',
                     'GAIN.pck']:
            self._data_files[file] = init.get_output_data_file(file)
        

        # next start to process these - then colspot

        colspot = self.Colspot()

        for file in ['X-CORRECTIONS.pck',
                     'Y-CORRECTIONS.pck',
                     'BLANK.pck',
                     'BKGINIT.pck',
                     'GAIN.pck']:
            colspot.set_input_data_file(file, self._data_files[file])

        colspot.set_data_range(first, last)
        colspot.set_background_range(self._indxr_images[0][0],
                                     self._indxr_images[0][1])
        for block in self._indxr_images:
            colspot.add_spot_range(block[0], block[1])

        colspot.run()

        for file in ['SPOT.XDS']:
            self._data_files[file] = colspot.get_output_data_file(file)

        # that should be everything prepared... all of the important
        # files should be loaded into memory to be able to cope with
        # integration happening somewhere else

        return

    def _index(self):
        '''Actually do the autoindexing using the data prepared by the
        previous method.'''

        idxref = self.Idxref()

        for file in ['SPOT.XDS']:
            idxref.set_input_data_file(file, self._data_files[file])
            
        idxref.set_data_range(self._indxr_images[0][0],
                              self._indxr_images[0][1])
        idxref.set_background_range(self._indxr_images[0][0],
                                    self._indxr_images[0][1])

        # set the phi start etc correctly

        for block in self._indxr_images[:1]:
            starting_frame = block[0]
            
            dd = Diffdump()
            dd.set_image(self.get_image_name(starting_frame))
            starting_angle = dd.readheader()['phi_start']

            idxref.set_starting_frame(starting_frame)
            idxref.set_starting_angle(starting_angle)
            
            idxref.add_spot_range(block[0], block[1])

        for block in self._indxr_images[1:]:
            idxref.add_spot_range(block[0], block[1])

        # FIXME need to also be able to pass in the known unit
        # cell and lattice if already available e.g. from
        # the helper... indirectly

        if self._indxr_input_lattice and self._indxr_input_cell:
            idxref.set_indexer_input_lattice(self._indxr_input_lattice)
            idxref.set_indexer_input_cell(self._indxr_input_cell)

            Debug.write('Set lattice: %s' % self._indxr_input_lattice)
            Debug.write('Set cell: %f %f %f %f %f %f' % \
                        self._indxr_input_cell)
            
            original_cell = self._indxr_input_cell
        elif self._indxr_input_lattice:
            idxref.set_indexer_input_lattice(self._indxr_input_lattice)
            original_cell = None
        else:
            original_cell = None

        # FIXED need to set the beam centre here - this needs to come
        # from the input .xinfo object or header, and be converted
        # to the XDS frame... done.

        mosflm_beam_centre = self.get_beam()
        xds_beam_centre = beam_centre_mosflm_to_xds(
            mosflm_beam_centre[0], mosflm_beam_centre[1], self.get_header())
        
        idxref.set_beam_centre(xds_beam_centre[0],
                               xds_beam_centre[1])

        # fixme need to check if the lattice, cell have been set already,
        # and if they have, pass these in as input to the indexing job.

        done = False

        while not done:
            try:
                done = idxref.run()
            except XDSException, e:
                # inspect this - if we have complaints about not
                # enough reflections indexed, and we have a target
                # unit cell, and they are the same, well ignore it

                if 'solution is inaccurate' in str(e):
                    Debug.write(
                        'XDS complains solution inaccurate - ignoring')
                    done = idxref.run(ignore_errors = True)
                elif 'insufficient percentage (< 70%)' in str(e) and \
                         original_cell:
                    done = idxref.run(ignore_errors = True)                    
                    lattice, cell, mosaic = \
                             idxref.get_indexing_solution()
                    # compare solutions
                    for j in range(3):
                        # allow two percent variation in unit cell length
                        if math.fabs((cell[j] - original_cell[j]) / \
                                     original_cell[j]) > 0.02 and \
                                     not Flags.get_relax():
                            Debug.write('XDS unhappy and solution wrong')
                            raise e
                        # and two degree difference in angle
                        if math.fabs(cell[j + 3] - original_cell[j + 3]) \
                               > 2.0 and not Flags.get_relax():
                            Debug.write('XDS unhappy and solution wrong')
                            raise e                        
                    Debug.write('XDS unhappy but solution ok')
                elif 'insufficient percentage (< 70%)' in str(e):
                    done = idxref.run(ignore_errors = True)                    
                    Debug.write('XDS unhappy but solution probably ok')
                else:
                    raise e

        for file in ['SPOT.XDS',
                     'XPARM.XDS']:
            self._data_files[file] = idxref.get_output_data_file(file)

        # need to get the indexing solutions out somehow...

        self._indxr_other_lattice_cell = idxref.get_indexing_solutions()
        self._indxr_lattice, self._indxr_cell, self._indxr_mosaic = \
                             idxref.get_indexing_solution()

        self._indxr_refined_beam = beam_centre_xds_to_mosflm(
            idxref.get_refined_beam()[0], idxref.get_refined_beam()[1],
            self.get_header())
        self._indxr_refined_distance = idxref.get_refined_distance()

        self._indxr_payload['xds_files'] = self._data_files

        return
        
if __name__ == '__main_old__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    xi = XDSIndexer()

    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    # directory = '/data/graeme/12287'
    xi.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))
    xi.set_beam((108.9, 105.0))

    xi.index()
    
    print 'Refined beam is: %6.2f %6.2f' % xi.get_indexer_beam()
    print 'Distance:        %6.2f' % xi.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % xi.get_indexer_cell()
    print 'Lattice: %s' % xi.get_indexer_lattice()
    print 'Mosaic: %6.2f' % xi.get_indexer_mosaic()


if __name__ == '__main__':

    xi = XDSIndexer()

    directory = os.path.join('/data', 'graeme', 'insulin', 'demo')

    xi.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))

    xi.index()
    
    print 'Refined beam is: %6.2f %6.2f' % xi.get_indexer_beam()
    print 'Distance:        %6.2f' % xi.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % xi.get_indexer_cell()
    print 'Lattice: %s' % xi.get_indexer_lattice()
    print 'Mosaic: %6.2f' % xi.get_indexer_mosaic()
    
