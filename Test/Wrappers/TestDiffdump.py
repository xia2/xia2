#!/usr/bin/env python
# TestLabelitScreen.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 2nd June 2006
# 
# Unit tests to ensure that the LabelitScreen wrapper is behaving
# properly.
# 
# 

import os, sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('X2TD_ROOT'):
    raise RuntimeError, 'X2TD_ROOT (xia2 Test Data Root) not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.XIA.Diffdump import Diffdump
import unittest

from Handlers.Streams import streams_off

streams_off()

# this should be placed in a gwmath module or something...

def nint(a):
    b = int(a)
    if a - b > 0.5:
        b += 1
    return b

class TestDiffractionImage(unittest.TestCase):
    def setUp(self):
        pass

    def testadsc(self):
        image = os.path.join(os.environ['X2TD_ROOT'],
                             'Test', 'UnitTest', 'Wrappers', 'Diffdump',
                             '12287_1_E1_001.img')
        
        dd = Diffdump()
        dd.set_image(image)
        header = dd.readheader()

        # check that the values are correct
        
        self.assertEqual(nint(header['distance']), 170)
        self.assertEqual(nint(header['phi_start']), 290)
        self.assertEqual(nint(header['phi_end']), 291)
        self.assertEqual(nint(header['phi_width']), 1)
        self.assertEqual(nint(header['wavelength'] * 10000), 9797)
        self.assertEqual(nint(header['beam'][0]), 105)
        self.assertEqual(nint(header['beam'][1]), 109)
        
        return


if __name__ == '__main__':
    unittest.main()


    


