#!/usr/bin/env python
# TestMtzdump.py
# Maintained by G.Winter
# 6th June 2006
# 
# Unit tests to ensure that the Mtzdump wrapper is behaving
# properly.
# 
# 

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Wrappers.CCP4.Mtzdump import Mtzdump
import unittest

class TestMtzdump(unittest.TestCase):

    def setUp(self):
        pass

    def testdefault(self):
        '''Test mtzdump with the data from XIA core unit tests.'''
        xia2core = os.environ['XIA2CORE_ROOT']
        
        hklin = os.path.join(xia2core,
                             'Data', 'Test', 'Mtz', '12287_1_E1.mtz')
        
        m = Mtzdump()
        m.setHklin(hklin)
        status = m.dump()

        self.assertEqual(status, 'Normal termination')

        # this file has but one dataset
        self.assertEqual(len(m.getDatasets()), 1)

        # and has spacegroup P43212
        self.assertEqual(m.getSpacegroup(), 'P43212')

    def testnotmtzfile(self):
        '''Test mtzdump with an input file in the wrong format.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'not-mtz.txt')
        
        m = Mtzdump()
        m.setHklin(hklin)
        self.assertRaises(RuntimeError, m.dump)

    def testnofile(self):
        '''Test mtzdump with a missing input file.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'nosuchfile.mtz')
        
        m = Mtzdump()
        m.setHklin(hklin)
        self.assertRaises(RuntimeError, m.dump)

if __name__ == '__main__':
    unittest.main()

