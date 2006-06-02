#!/usr/bin/env python
# TestPointless.py
# Maintained by G.Winter
# 2nd June 2006
# 
# Unit tests to ensure that the Pointless wrapper is behaving
# properly.
# 
# 

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

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
        
        p.setHklin(hklin)
        
        p.decide_pointgroup()
        
        self.assertEqual(p.getPointgroup(), 'P 4 2 2')

if __name__ == '__main__':
    unittest.main()

