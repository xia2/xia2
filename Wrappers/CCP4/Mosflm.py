#!/usr/bin/env python
# Mosflm.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 23rd June 2006
# 
# A wrapper for the data processing program Mosflm, with the following
# methods to provide functionality:
# 
# index: autoindexing functionality (not implemented)
# integrate: process a frame or a dataset (not implemented)
#
# Internally this will also require cell refinement and so on, but this
# will be implicit - the cell refinement is a local requirement for
# mosflm only - though this will provide some useful functionality
# for diagnosing wrong indexing solutions.
#
# Input requirements:
# 
# At the minimum the indexing needs a beam centre, some images to index
# from and the template and directory where these images may be found.
# The indexing will return the most likely solution, or the one specified
# if this has been done. The interface should look like indexing with 
# labelit. However, a matrix file to index against could optionally be 
# supplied, to help with processing MAD data.
# 
# For integration, an appropriate matrix file, beam centre, lattice
# (spacegroup) and mosaic spread are needed, along with (optionally) a
# gain and definately images to process. A resolution limit may also be
# supplied.
# 
# The following are good example scripts of how this could work:
# 
# [autoindexing + cell refinement]
# 
# ipmosflm << eof
# beam 108.9 105.0
# directory /data/graeme/12287
# template 12287_1_E1_###.img
# autoindex dps image 1   ! can add refine after dps
# autoindex dps image 60  ! can add refine after dps
# mosaic estimate
# newmat index.mat
# go
# ! cell refinement stuff - needs more than 2 images
# newmat refined.mat
# postref multi segments 2
# process 1 3
# go
# process 58 60
# go
# eof
# 
# [integration]
# 
# ipmosflm hklout 12287_1_E1.mtz << eof
# resolution 1.65
# beam 108.9 105.0
# directory /data/graeme/12287
# template 12287_1_E1_###.img
# matrix refined.mat
# mosaic 0.51
# limits esclude   0.9 103.9 208.9 105.5
# limits exclude 103.5   4.4 106.0 209.0
# limits quadriateral 110.6 105.5 107.2 105.8 104.4 4.7 108.7 4.7
# gain 0.13
# separation close
# postref fix all
# process 1 60
# go
# eof

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

# interfaces that this will present
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Interfaces.Indexer import Indexer

def Mosflm(DriverType = None):
    '''A factory for MosflmWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class MosflmWrapper(CCP4DriverInstance.__class__,
                        FrameProcessor,
                        Indexer):
        '''A wrapper for Mosflm, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.setExecutable('ipmosflm')

            FrameProcessor.__init__(self)
            Indexer.__init__(self)

        def _index(self):
            '''Implement the indexer interface.'''

            _images = []
            for i in self._indxr_images:
                for j in i:
                    if not j in _images:
                        _images.append(j)
                    
            _images.sort()

            task = 'Autoindex from images:'

            for i in _images:
                task += ' %s' % self.getImage_name(i)

            self.setTask(task)
            
            self.start()

            self.input('template %s' % self.getTemplate())
            self.input('directory %s' % self.getDirectory())
            self.input('newmat xiaindex.mat')

            if self.getBeam_prov() == 'user':
                self.input('beam %f %f' % self.getBeam())

            if self.getWavelength_prov() == 'user':
                self.input('wavelength %f %f' % self.getWavelength())

            if self.getDistance_prov() == 'user':
                self.input('distance %f' % self.getDistance())

            for i in _images:
                self.input('autoindex dps refine image %d' % i)

            self.input('mosaic estimate')
            self.input('go')

            self.close_wait()

            output = self.get_all_output()

            for o in output:
                if 'Final cell (after refinement)' in o:
                    self._indxr_cell = tuple(map(float, o.split()[-6:]))
                if 'Beam coordinates of' in o:
                    self._indxr_refined_beam = tuple(map(float, o.split(
                        )[-2:]))
                if 'Symmetry:' in o:
                    self._indxr_lattice = o.split(':')[1].split()[0]
                if 'The mosaicity has been estimated' in o:
                    self._indxr_mosaic = float(o.split('>')[1].split()[0])

                # mosflm doesn't refine this...
                if 'Crystal to detector distance' in o:
                    self._indxr_refined_distance = float(o.split(
                        )[5].replace('mm', ''))

            self._indxr_payload['mosflm_orientation_matrix'] = open(
                'xiaindex.mat', 'r').readlines()
    
    return MosflmWrapper()


if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('DPA_ROOT'):
        raise RuntimeError, 'DPA_ROOT not defined'

    m = Mosflm()

    directory = os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images')

    # from Labelit
    m.setBeam((108.9, 105.0))

    m.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    m.addIndexer_image_wedge(1)
    m.addIndexer_image_wedge(90)

    m.index()

    print 'Refined beam is: %6.2f %6.2f' % m.getIndexer_beam()
    print 'Distance:        %6.2f' % m.getIndexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % m.getIndexer_cell()
    print 'Lattice: %s' % m.getIndexer_lattice()
    print 'Mosaic: %6.2f' % m.getIndexer_mosaic()


        
