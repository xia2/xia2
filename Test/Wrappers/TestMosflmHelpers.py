#!/usr/bin/env python
# TestMosflmHelpers.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 12th December 2006
#
# Code to test Mosflm Helper routines against difficult cases.
#
#

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ.has_key('X2TD_ROOT'):
    raise RuntimeError, 'X2TD_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.MosflmHelpers import _parse_mosflm_index_output

def test_tf_index_log():
    '''Test the parsing of the index output provided by Takaaki Fumaki
    12th December 2006.'''

    lp_data = open(os.path.join(os.environ['X2TD_ROOT'],
                                'Test', 'UnitTest', 'Wrappers', 'Mosflm',
                                'difficult_indexing_example_tf_12dec06.txt'),
                   'r').readlines()

    print _parse_mosflm_index_output(lp_data)

if __name__ == '__main__':
    test_tf_index_log()
    
