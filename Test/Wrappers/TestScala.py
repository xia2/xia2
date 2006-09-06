#!/usr/bin/env python
# TestScala.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 6th June 2006
# 
# Unit tests to ensure that the Scala wrapper is behaving
# properly.
# 
# 

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Wrappers.CCP4.Scala import Scala
import unittest

class TestScala(unittest.TestCase):

    def setUp(self):
        pass

    def testdefault(self):
        '''Test scala with the data from XIA core unit tests. This version
        tests that simple things to work.'''
        
        hklin = os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python', 'UnitTest', '12287_1_E1_sorted.mtz')
        
        s = Scala()
        
        s.set_hklin(hklin)

        # write this to scratch 
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-scala.mtz'))

        s.set_resolution(1.65)
        
        # switch on all of the options I want
        s.set_anomalous()
        s.set_tails()
        s.set_bfactor()
        
        s.set_scaling_parameters('rotation')
        
        # this is in the order fac, add, B
        s.add_sd_correction('full', 1.0, 0.02, 15.0)
        s.add_sd_correction('partial', 1.0, 0.00, 15.0)
        
        status = s.scale()

        self.assertEqual(status, 'Normal termination')
        
        return

    def testnohklin(self):
        '''Test scala with the data from XIA core unit tests. This example
        checks that the system fails when passed a false input file.'''
        
        hklin = 'nosuchfile'
        
        s = Scala()
        
        s.set_hklin(hklin)

        # write this to scratch 
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-scala.mtz'))

        s.set_resolution(1.65)
        
        # switch on all of the options I want
        s.set_anomalous()
        s.set_tails()
        s.set_bfactor()
        
        s.set_scaling_parameters('rotation')
        
        # this is in the order fac, add, B
        s.add_sd_correction('full', 1.0, 0.02, 15.0)
        s.add_sd_correction('partial', 1.0, 0.00, 15.0)

        self.assertRaises(RuntimeError, s.scale)

        return

    def testnotmtzfile(self):
        '''Test scala with the data from XIA core unit tests. This example
        tests what happens when the input file is not mtz format.'''
        
        hklin = os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Mtz', 'not-mtz.txt')
        
        s = Scala()
        
        s.set_hklin(hklin)

        # write this to scratch 
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-scala.mtz'))

        s.set_resolution(1.65)
        
        # switch on all of the options I want
        s.set_anomalous()
        s.set_tails()
        s.set_bfactor()
        
        s.set_scaling_parameters('rotation')
        
        # this is in the order fac, add, B
        s.add_sd_correction('full', 1.0, 0.02, 15.0)
        s.add_sd_correction('partial', 1.0, 0.00, 15.0)

        self.assertRaises(RuntimeError, s.scale)

        return

    def testnotsorted(self):
        '''Test scala with the data from XIA core unit tests. This example
        tests what happens when the input file is not sorted.'''
        
        hklin = os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Data', 'Test', 'Mtz', '12287_1_E1.mtz')
        
        s = Scala()
        
        s.set_hklin(hklin)

        # write this to scratch 
        s.set_hklout(os.path.join(os.environ['CCP4_SCR'],
                                 'temp-test-scala.mtz'))

        s.set_resolution(1.65)
        
        # switch on all of the options I want
        s.set_anomalous()
        s.set_tails()
        s.set_bfactor()
        
        s.set_scaling_parameters('rotation')
        
        # this is in the order fac, add, B
        s.add_sd_correction('full', 1.0, 0.02, 15.0)
        s.add_sd_correction('partial', 1.0, 0.00, 15.0)

        self.assertRaises(RuntimeError, s.scale)

        return

if __name__ == '__main__':
    unittest.main()

