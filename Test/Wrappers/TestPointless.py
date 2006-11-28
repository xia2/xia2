#!/usr/bin/env python
# TestPointless.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 2nd June 2006
# 
# Unit tests to ensure that the Pointless wrapper is behaving
# properly.
# 
# 

import os, sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.CCP4.Pointless import Pointless
import unittest

class TestPointless(unittest.TestCase):

    def setUp(self):
        pass

    def testtetragonal(self):
        '''Test pointless with the data from XIA core unit tests.'''
        xia2core = os.environ['XIA2CORE_ROOT']
        
        hklin = os.path.join(xia2core,
                             'Data', 'Test', 'Mtz', '12287_1_E1.mtz')
        
        p = Pointless()
        
        p.set_hklin(hklin)
        
        p.decide_pointgroup()
        
        self.assertEqual(p.get_pointgroup(), 'P 4 2 2')

if __name__ == '__main__':
    unittest.main()

