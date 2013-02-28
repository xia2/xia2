#!/usr/bin/env python
# TestDriverHelper.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 25th May 2006
# 
# Tests for the Driver Helper functions.
# 

import os, sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python',
                             'Driver'))

import DriverHelper

# this is used to execute test scripts
import subprocess

import unittest

class TestDriverHelper(unittest.TestCase):

    def setUp(self):
        pass

    def testscript(self):
        '''Test the DriverHelper script writing function.'''

        DriverHelper.script_writer(os.getcwd(),
                                   'testscript',
                                   'ExampleProgramCommandLineStandardInput',
                                   ['foobar'],
                                   os.environ,
                                   ['4\n'])

        if os.name == 'nt':
            subprocess.call(['testscript.bat'])
        else:
            subprocess.call(['bash', 'testscript.sh'])

        results = open('testscript.xout', 'r').readlines()

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].strip(), 'Hello, foobar!')

        return

    def testrandomnames(self):
        '''Test that the random name generation works.'''

        names = []
        for i in range(1000):
            n = DriverHelper.generate_random_name()
            if not n in names:
                names.append(n)

        self.assertEqual(len(names), 1000)

if __name__ == '__main__':
    unittest.main()


            
