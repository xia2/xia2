#!/usr/bin/env python
# TestDataset.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 13th June 2006
# 
# UnitTests for the Dataset object. This will test a number of the
# basic properties as well as some more sophisticated functions.
# 
# 

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Schema.Dataset import Dataset
import unittest

class TestDataset(unittest.TestCase):

    def setUp(self):
        pass

    def testequality(self):
        '''Test the equality of objects.'''
        d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images',
                                 '12287_1_E1_001.img'))
        
        e = Dataset(os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images',
                                 '12287_1_E1_001.img'))

        self.assertEqual(d, e)

        return

    def testindex(self):
        '''Test simple indexing.'''
        d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images',
                                 '12287_1_E1_001.img'))
        lattice_info = d.getLattice_info()
        self.assertEqual(lattice_info.getLattice(), 'tP')

        return

    def testindexprior(self):
        '''Test defined indexing.'''
        d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images',
                                 '12287_1_E1_001.img'))

        d.setLattice('oP')
        lattice_info = d.getLattice_info()
        self.assertEqual(lattice_info.getLattice(), 'oP')

        return

    def testinequality(self):
        '''Test object inequality.'''        
        d = Dataset(os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images',
                                 '12287_1_E1_001.img'))
        d.setLattice('oP')
        e = Dataset(os.path.join(os.environ['DPA_ROOT'],
                                 'Data', 'Test', 'Images',
                                 '12287_1_E1_001.img'))

        self.assertNotEqual(d, e)

        return

if __name__ == '__main__':
    unittest.main()

    
