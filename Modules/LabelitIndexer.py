#!/usr/bin/env python
# LabelitIndexer.py
# Maintained by G.Winter
# 13th June 2006
# 
# An implementation of Indexer using labelit.screen wrapper.
# 
# 
#

import os
import sys
import copy

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Schema.LatticeInfo import LatticeInfo
from Schema.Dataset import Dataset
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


        ls.write_log_file('labelit.log')
        ls.index()
                
        results = ls.getSolutions()
        beam = ls.getBeam()
        
        solution = results[max(results.keys())]
        
        self._setLattice_info(LatticeInfo(solution['lattice'],
                                          solution['cell'],
                                          mosaic = solution['mosaic'],
                                          beam = beam))
        
        
        return

if __name__ == '__main__':
    # run a light test

    d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img'))

    i = LabelitIndexer(d)
    li = i.getLattice_info()

    cell = li.getCell()

    print '%s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
          (li.getLattice(), cell[0], cell[1], cell[2],
           cell[3], cell[4], cell[5])

    
    
        
