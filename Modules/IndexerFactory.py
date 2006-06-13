#!/usr/bin/env python
# IndexerFactory.py
# Maintained by G.Winter
# 13th June 2006
# 
# A factory for Indexer class instances. This will return an indexer
# suitable for using in the context defined in the input.
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

from LabelitIndexer import LabelitIndexer

def Indexer(dataset,
            images = None):
    '''Create an instance of Indexer for use with this dataset.'''

    if True:
        return LabelitIndexer(dataset, images = images)

if __name__ == '__main__':
    
    from Schema.Dataset import Dataset
    d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images', '12287_1_E1_001.img'))

    i = Indexer(d)
    li = i.getLattice_info()

    cell = li.getCell()

    print '%s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
          (li.getLattice(), cell[0], cell[1], cell[2],
           cell[3], cell[4], cell[5])

    
    
