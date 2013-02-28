#!/usr/bin/env python
# TestDriver.py
# 
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root dorectory of this package.
#
# 24th May 2006
# 
# Unit tests for the python Driver class implementations.
#

import os, sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from DriverExceptions.NotAvailableError import NotAvailableError
import unittest

class TestDriver(unittest.TestCase):

    def setUp(self):
        pass

    def testsimple(self):
        '''Test the Driver class with the simple ExampleProgram.'''

        d = DriverFactory.Driver()

        d.set_executable('ExampleProgram')

        d.start()
        d.close()

        results = []

        while True:
            line = d.output()

            if not line:
                break

            results.append(line.strip())

        self.assertEqual(len(results), 10)
        self.assertEqual(results[0], 'Hello, world!')

    def testcript(self):
        '''Test the Driver class with the simple ExampleProgram.'''

        d = DriverFactory.Driver('script')

        d.set_name('unittest')

        d.set_executable('ExampleProgram')

        d.start()
        d.close()

        results = []

        while True:
            line = d.output()

            if not line:
                break

            results.append(line.strip())

        self.assertEqual(len(results), 10)
        self.assertEqual(results[0], 'Hello, world!')

    def testnoprogram(self):
        '''Test how the driver handles the executable not existing.'''

        d = DriverFactory.Driver()

        # UNIT TEST now much simpler, see changes in DefaultDriver detailed
        # 1/SEP/06 - however, should this also test against the environment
        # variable to switch off this test?

        self.assertRaises(NotAvailableError, d.set_executable, 'nosuchprogram')

        # d.start()

        # in some cases the termination of the child process may be caught
        # this is OK
        # try:
        # d.close()
        # except RuntimeError, re:
        # just make this so that it has to raise an exception?
        # self.assertEqual(1, 1)
        # self.assertEqual(str(re), 'child process has termimated')
        # return

        # while True:
        # line = d.output()
        # if not line:
        # break

        # found_exception = False
        # exception_str = ''

        # try:
        # d.check_for_errors()
        # except RuntimeError, re:
        # found_exception = True
        # exception_str = str(re)

        # self.assertEqual(found_exception, True)
        # self.assertEqual(exception_str, 
        # 'executable "nosuchprogram" does not exist')
        
    def testsignalkill(self):
        '''Test the kill signal.'''

        d = DriverFactory.Driver()

        d.set_executable('EPKill')
        d.start()

        # in some cases the termination of the child process may be caught
        # this is OK
        try:
            d.close()
        except RuntimeError, re:
            # this could have one or more records...
            # self.assertEqual(str(re), 'child process has termimated')
            self.assertEqual(1, 1)
            return
        
        while True:
            line = d.output()
            if not line:
                break

        
        found_exception = False
        exception_str = ''
        
        try:
            d.check_for_errors()
        except RuntimeError, re:
            found_exception = True
            exception_str = str(re)

        self.assertEqual(found_exception, True)

        # this is os specific: windows does not return the error code

        if os.name == 'nt':
            self.assertEqual(exception_str,
                             'child error')
        else:
            self.assertEqual(exception_str, 
                             'child killed')
            
    def testsignalsegv(self):
        '''Test the segmentation fault signal.'''

        d = DriverFactory.Driver()

        try:
            d.set_executable('EPSegv')
            d.start()
            d.close()
            while True:
                line = d.output()
                if not line:
                    break
                
        except RuntimeError, e:
            self.assertEqual(str(e), 'child segmentation fault')
            return
        
        found_exception = False
        exception_str = ''

        try:
            d.check_for_errors()
        except RuntimeError, re:
            found_exception = True
            exception_str = str(re)

        # this is os specific: windows does not return the error code
        # nor does the return code come back at all as an error. 
        # ergo no errors to report on windows

        if os.name == 'nt':
            pass
        else:
            self.assertEqual(found_exception, True)
            self.assertEqual(exception_str, 
                             'child segmentation fault')

    if os.name == 'nt':
        def testsignalsegv(self):
            pass
            
    def testsignalabrt(self):
        '''Test the abort signal.'''

        d = DriverFactory.Driver()

        try:
            d.set_executable('EPAbrt')
            d.start()
            d.close()
            while True:
                line = d.output()
                if not line:
                    break
        except RuntimeError, e:
            # this should probably error
            self.assertEqual(str(e), 'child aborted')
            return

        
        found_exception = False
        exception_str = ''
        
        try:
            d.check_for_errors()
        except RuntimeError, re:
            found_exception = True
            exception_str = str(re)

        self.assertEqual(found_exception, True)

        # this is os specific: windows does not return the error code

        if os.name == 'nt':
            self.assertEqual(exception_str,
                             'child error')
        else:
            self.assertEqual(exception_str, 
                             'child aborted')
            
        


if __name__ == '__main__':
    unittest.main()


            
