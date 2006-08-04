#!/usr/bin/env python
# LabelitIndexer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 13th June 2006
# 
# An implementation of Indexer using labelit.screen wrapper.
# 
# FIXME this needs to be removed now that there is a proper interface
# for Indexer which is implemented by LabelitScreen.py - this should
# be accessed directly by the IndexerFacory.

import os
import sys
import copy

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Schema.LatticeInfo import LatticeInfo
from Wrappers.Labelit.LabelitScreen import LabelitScreen
from Modules.Prototype.Indexer import Indexer
from Experts.FindImages import template_directory_number2image

class LabelitIndexer(Indexer):
    '''An indexer implementation using the LabelitScreen Wrapper class.'''

    def __init__(self, dataset, images = None):
        Indexer.__init__(self, dataset)

        if images is None:
            self._select_images()

        else:
            # verify that these frames exist

            for i in images:
                if not i in dataset.getImages():
                    raise RuntimeError, 'image %d does not exist' % i
            
            self._images = images

        return

    def _select_images(self):
        '''From the information contained in the dataset object,
        select some images.'''

        # FIXME this needs properly implementing - just as a demo use the
        # first, last images

        images = self.getDataset().getImages()
        self._images = [min(images), max(images)]

        return
        

    def _index(self):
        '''Actually perform the autoindexing.'''
        
        ls = LabelitScreen()

        for i in self._images:
            ls.addImage(template_directory_number2image(
                self.getDataset().getTemplate(),
                self.getDataset().getDirectory(),
                i))
            
        if self.getDataset().getBeam() != (0.0, 0.0):
            ls.setBeam(self.getDataset().getBeam()[0],
                       self.getDataset().getBeam()[1])


        if self.getDataset().getLattice():
            ls.setLattice(self.getDataset().getLattice())

        ls.write_log_file('labelit.log')
        ls.index()
                
        solution = ls.getSolution()
        beam = ls.getBeam()        
        self._setLattice_info(LatticeInfo(solution['lattice'],
                                          solution['cell'],
                                          mosaic = solution['mosaic'],
                                          beam = beam))
        
        
        return

if __name__ == '__main__':
    # run a light test
    from Schema.Dataset import Dataset
    d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img'))

    i = LabelitIndexer(d)
    li = i.getLattice_info()

    cell = li.getCell()

    print '%s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
          (li.getLattice(), cell[0], cell[1], cell[2],
           cell[3], cell[4], cell[5])

    
    
        
