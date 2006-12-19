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

# helper functions

from Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from Wrappers.XDS.XDS import beam_centre_xds_to_mosflm

# interfaces that this must implement to be an indexer

from Schema.Interfaces.Indexer import Indexer
from Schema.Interfaces.FrameProcessor import FrameProcessor

# odds and sods that are needed

from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter

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

        auto_logfiler(xycorr)

        return xycorr

    def Init(self):
        init = _Init()
        init.set_working_directory(self.get_working_directory())

        init.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        auto_logfiler(init)

        return init

    def Colspot(self):
        colspot = _Colspot()
        colspot.set_working_directory(self.get_working_directory())

        colspot.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        auto_logfiler(colspot)

        return colspot

    def Idxref(self):
        idxref = _Idxref()
        idxref.set_working_directory(self.get_working_directory())

        idxref.setup_from_image(self.get_image_name(
            self._indxr_images[0][0]))

        auto_logfiler(idxref)

        return idxref

    # helper functions

    def _index_select_images(self):
        '''Select correct images based on image headers.'''
        
        phi_width = self.get_header_item('phi_width')
        
        if phi_width == 0.0:
            Chatter.write('Phi width 0.0? Assuming 1.0!')
            phi_width = 1.0

        images = self.get_matching_images()

        # characterise the images - are there just two (e.g. dna-style
        # reference images) or is there a full block?

        if len(images) < 3:
            # work on the assumption that this is a reference pair
        
            self.add_indexer_image_wedge(images[0])
            
            if int(90.0 / phi_width) in images:
                self.add_indexer_image_wedge(int(90.0 / phi_width))
            else:
                self.add_indexer_image_wedge(images[-1])

        else:
            # work on the assumption that this is a full sweep of images
            # so I can use two blocks...

            block_size = int(3.0 / phi_width)

            self.add_indexer_image_wedge((images[0], images[block_size] - 1))

            if int(90.0 / phi_width) + block_size in images:
                self.add_indexer_image_wedge((int(90.0 / phi_width),
                                              int(90.0 / phi_width) +
                                              block_size))
            else:
                self.add_indexer_image_wedge((images[- block_size],
                                              images[-1]))
            
        return

    # do-er functions

    def _index_prepare(self):
        '''Prepare to do autoindexing - in XDS terms this will mean
        calling xycorr, init and colspot on the input images.'''

        # decide on images to work with

        if self._indxr_images == []:
            self._index_select_images()

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

        # next start to process these - then init

        init = self.Init()

        init.set_data_range(first, last)
        init.set_background_range(self._indxr_images[0][0],
                                  self._indxr_images[0][1])
        for block in self._indxr_images:
            init.add_spot_range(block[0], block[1])

        init.run()

        # next start to process these - then colspot

        colspot = self.Colspot()

        colspot.set_data_range(first, last)
        colspot.set_background_range(self._indxr_images[0][0],
                                     self._indxr_images[0][1])
        for block in self._indxr_images:
            colspot.add_spot_range(block[0], block[1])

        colspot.run()

        # that should be everything prepared... all of the important
        # files should be loaded into memory to be able to cope with
        # integration happening somewhere else

        return

    def _index(self):
        '''Actually do the autoindexing using the data prepared by the
        previous method.'''

        idxref = self.Idxref()

        idxref.set_data_range(self._indxr_images[0][0],
                              self._indxr_images[0][1])
        idxref.set_background_range(self._indxr_images[0][0],
                                    self._indxr_images[0][1])

        for block in self._indxr_images:
            idxref.add_spot_range(block[0], block[1])

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
            done = idxref.run()

        # need to get the indexing solutions out somehow...

        self._indxr_other_lattice_cell = idxref.get_indexing_solutions()
        self._indxr_lattice, self._indxr_cell, self._indxr_mosaic = \
                             idxref.get_indexing_solution()

        self._indxr_refined_beam = beam_centre_xds_to_mosflm(
            idxref.get_refined_beam()[0], idxref.get_refined_beam()[1],
            self.get_header())
        self._indxr_refined_distance = idxref.get_refined_distance()

        return
        
if __name__ == '__main__':

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


