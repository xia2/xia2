#!/usr/bin/env python
# Indexer.py
# Maintained by G.Winter
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

        # make a place to store the results somewhere...

        

    def _index(self):
        raise RuntimeError, 'this method must be overloaded'
        
    def getLatticeEtc(self):
        '''This really needs to be improved.'''

        # since results are not datasets can compare epochs like this...

        if self._results and self._results > self._dataset:
            return self._results

        else:
            self._index()
            return self._results

        
