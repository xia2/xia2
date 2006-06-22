#!/usr/bin/env python
# Indexer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 12th June 2006
# 
# A prototype indexer module. This should be inherited from as a class for
# all "real" implementations of indexer. Do not use this class directly.
# 
# 

class Indexer:
    '''A pure virtual class defining the indexer interface.'''

    def __init__(self, dataset):
        '''The constructor - this should be used, to ensure that the
        instance satisfies the interface for indexer. In particular
        to ensure that the interface recieving dataset remains...'''

        if dataset.__class__.__name__ != 'Dataset':
            raise RuntimeError, 'dataset must be a Dataset'

        self._dataset = dataset

        # make a place to store the results
        self._lattice_info = None

        return

    def getDataset(self):
        return self._dataset

    def _index(self):
        raise RuntimeError, 'this method must be overloaded'

    def _setLattice_info(self, lattice_info):
        if lattice_info.__class__.__name__ != 'LatticeInfo':
            raise RuntimeError, 'result not LatticeInfo'
                  
        self._lattice_info = lattice_info
        return
        
    def getLattice_info(self):
        # get the results of the autoindexing, possibly performing
        # the calculation if the results are out-of-date or
        # something.

        if self._lattice_info and self._lattice_info > self._dataset:
            if self._lattice_info.__class__.__name__ != 'LatticeInfo':
                raise RuntimeError, 'result not LatticeInfo'
            return self._lattice_info

        else:
            self._index()
            if self._lattice_info.__class__.__name__ != 'LatticeInfo':
                raise RuntimeError, 'result not LatticeInfo'
            return self._lattice_info

        return

if __name__ == '__main__':
    # then do something interesting...
    pass
