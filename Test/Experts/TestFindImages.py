#!/usr/bin/env python
# TestFindImages.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 9th June 2006
# 
# Unit tests to ensure that the FindImages methods are working properly.
# 
# 

import os, sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

from Experts.FindImages import image2template, find_matching_images, \
     template_directory_number2image

import unittest

class TestFindImages(unittest.TestCase):

    def setUp(self):
        pass

    def testImage2template(self):
        '''Test image2template is working.'''
        
        self.assertEqual(image2template('foo_bar_1_001.img'),
                         'foo_bar_1_###.img')

        self.assertEqual(image2template('foo_bar_001.img'),
                         'foo_bar_###.img')
        self.assertEqual(image2template('foo_bar001.img'),
                         'foo_bar###.img')
        self.assertEqual(image2template('foo_bar.001'),
                         'foo_bar.###')

    def testFind_matching_images(self):

        self.assertEqual(find_matching_images(
            image2template('12287_1_E1_001.img'),
            os.path.join(os.environ['DPA_ROOT'],
                         'Data', 'Test', 'Images')), [1, 90])
        
        def testConstruct_imagename(self):
    
            self.assertEqual(template_directory_number2image(
                image2template('12287_1_E1_001.img'),
                os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images'), 1),
                             os.path.join(os.environ['DPA_ROOT'],
                                          'Data', 'Test', 'Images',
                                          '12287_1_E1_001.img'))

            
            self.assertRaises(template_directory_number2image,
                              image2template('12287_1_E1_001.img'),
                              os.path.join(os.environ['DPA_ROOT'],
                                           'Data', 'Test',
                                           'Images'), 1000)

if __name__ == '__main__':
    unittest.main()

    
