#!/usr/bin/env python
# TestCCP4.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 31st May 2006
# 
# Unit test suite for the CCP4 Driver interface - this will ensure that 
# everything is working properly for CCP4 examples. This makes use of 
# provided input data (two wavelengths worth).
#  
# 

import os, sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python',
                             'Examples',
                             'CCP4'))

from Scala import Scala
from Sortmtz import Sortmtz

import unittest

class TestCCP4(unittest.TestCase):

    def setUp(self):
        pass

    def dosortinfl(self):
        '''Test sorting the inflection point data.'''

        s = Sortmtz()

        hklin = os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Data', 'Test', 'Mtz', '12287_1_E1.mtz')

        hklout = '12287_1_E1_sorted.mtz'

        s = Sortmtz()
        
        s.set_hklin(hklin)
        s.set_hklout(hklout)
        
        status = s.sort()

        self.assertEqual(status, 'Normal termination')

        return

    def dosortlrem(self):
        '''Test sorting the low remote data.'''

        s = Sortmtz()

        hklin = os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Data', 'Test', 'Mtz', '12287_1_E2.mtz')

        hklout = '12287_1_E2_sorted.mtz'

        s = Sortmtz()
        
        s.set_hklin(hklin)
        s.set_hklout(hklout)
        
        status = s.sort()

        self.assertEqual(status, 'Normal termination')

        return

    def doscaleinfl(self):
        '''Test scaling the inflection point data.'''

        s = Scala()

        hklin = '12287_1_E1_sorted.mtz'
        hklout = '12287_1_E1_scaled.broken'
        scalepack = '12287_1_E1_scaled.sca'

        s.set_hklin(hklin)
        s.set_hklout(hklout)
        s.set_scalepack(scalepack)

        status = s.scale()

        self.assertEqual(status, 'Normal termination')

    def doscalelrem(self):
        '''Test scaling the low remote data.'''

        s = Scala()

        hklin = '12287_1_E2_sorted.mtz'
        hklout = '12287_1_E2_scaled.broken'
        scalepack = '12287_1_E2_scaled.sca'

        s.set_hklin(hklin)
        s.set_hklout(hklout)
        s.set_scalepack(scalepack)

        status = s.scale()

        self.assertEqual(status, 'Normal termination')

    def testall(self):

        self.dosortinfl()
        self.dosortlrem()
        self.doscaleinfl()
        self.doscalelrem()

if __name__ == '__main__':
    unittest.main()
