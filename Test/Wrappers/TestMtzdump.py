#!/usr/bin/env python
# TestMtzdump.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
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
        m.set_hklin(hklin)
        status = m.dump()

        self.assertEqual(status, 'Normal termination')

        # this file has but one dataset
        self.assertEqual(len(m.get_datasets()), 1)

        # and has spacegroup P43212
        self.assertEqual(m.get_spacegroup(), 'P43212')

    def testnotmtzfile(self):
        '''Test mtzdump with an input file in the wrong format.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'not-mtz.txt')
        
        m = Mtzdump()
        m.set_hklin(hklin)
        self.assertRaises(RuntimeError, m.dump)

    def testnofile(self):
        '''Test mtzdump with a missing input file.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'nosuchfile.mtz')
        
        m = Mtzdump()
        m.set_hklin(hklin)
        self.assertRaises(RuntimeError, m.dump)

if __name__ == '__main__':
    unittest.main()

