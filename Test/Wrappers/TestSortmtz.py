#!/usr/bin/env python
# TestPointless.py
# Maintained by G.Winter
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

    def testtetragonal(self):
        '''Test sortmtz with the data from XIA core unit tests.'''
        xia2core = os.environ['XIA2CORE_ROOT']
        
        hklin = os.path.join(xia2core,
                             'Data', 'Test', 'Mtz', '12287_1_E1.mtz')
        
        s = Sortmtz()
        
        s.setHklin(hklin)

        # write this to scratch 
        s.setHklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))
        
        status = s.sort()

        self.assertEqual(status, 'Normal termination')
        
    def testnotmtzfile(self):
        '''Test sortmtz with the data from XIA core unit tests.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'not-mtz.txt')
        
        s = Sortmtz()
        
        s.setHklin(hklin)
        s.setHklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))

        self.assertRaises(RuntimeError, s.sort)

    def testnofile(self):
        '''Test sortmtz with the data from XIA core unit tests.'''
        dpa = os.environ['DPA_ROOT']
        
        hklin = os.path.join(dpa,
                             'Data', 'Test', 'Mtz', 'nosuchfile.mtz')
        
        s = Sortmtz()
        
        s.setHklin(hklin)
        s.setHklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-sortmtz.mtz'))

        self.assertRaises(RuntimeError, s.sort)

if __name__ == '__main__':
    unittest.main()

