#!/usr/bin/env python
# TestSortmtz.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 6th June 2006
# 
# Unit tests to ensure that the Sortmtz wrapper is behaving
# properly.
# 
# 

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Wrappers.CCP4.Sortmtz import Sortmtz
import unittest

class TestSortmtz(unittest.TestCase):

    def setUp(self):
        pass

    def testdefault(self):
        '''Test sortmtz with the data from XIA core unit tests.'''
        xia2core = os.environ['XIA2CORE_ROOT']
        
        hklin = os.path.join(xia2core,
                             'Data', 'Test', 'Mtz', '12287_1_E1.mtz')
        
        s = Sortmtz()
        
        s.set_hklin(hklin)

        # write this to scratch 
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))
        
        status = s.sort()

        self.assertEqual(status, 'Normal termination')
        
    def testmultiple(self):
        '''Test sortmtz with the data from XIA/DPA core unit tests.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin1 = os.path.join(dpa,
                              'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')
        hklin2 = os.path.join(dpa,
                              'Data', 'Test', 'Mtz', '12287_1_E1_11_20.mtz')
        
        s = Sortmtz()
        
        s.add_hklin(hklin1)
        s.add_hklin(hklin2)

        # write this to scratch 
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))
        
        status = s.sort()

        self.assertEqual(status, 'Normal termination')
        
    def testmultiplebadbatches(self):
        '''Test sortmtz with the data from XIA/DPA core unit tests.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin1 = os.path.join(dpa,
                              'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')
        
        s = Sortmtz()
        
        s.add_hklin(hklin1)
        s.add_hklin(hklin1)

        # write this to scratch 
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))
        
        self.assertRaises(RuntimeError, s.sort)
        
    def testnotmtzfile(self):
        '''Test sortmtz with an input file in the wrong format.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'not-mtz.txt')
        
        s = Sortmtz()
        
        s.set_hklin(hklin)
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))

        self.assertRaises(RuntimeError, s.sort)

    def testnofile(self):
        '''Test sortmtz with a missing input file.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'nosuchfile.mtz')
        
        s = Sortmtz()
        
        s.set_hklin(hklin)
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))

        self.assertRaises(RuntimeError, s.sort)

if __name__ == '__main__':
    unittest.main()

