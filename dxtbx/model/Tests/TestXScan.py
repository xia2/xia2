#!/usr/bin/env python
# TestXScan.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# Tests for the XScan class, and it's helper classes.

import math
import os
import sys
import time

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from dxtbx.model.XScan import XScan
from dxtbx.model.XScan import XScanFactory
from dxtbx.model.XScanHelpers import XScanHelperImageFiles
from dxtbx.model.XScanHelpers import XScanHelperImageFormats

def work_helper_image_files():
    '''Test the static methods in XScanHelperImageFiles.'''

    helper = XScanHelperImageFiles()

    directory = os.path.join(os.environ['XIA2_ROOT'], 'dxtbx', 'model',
                             'Tests')
    
    template = 'image_###.dat'

    assert(len(XScanHelperImageFiles.template_directory_to_indices(
        template, directory)) == 20)

    assert(XScanHelperImageFiles.template_directory_index_to_image(
        template, directory, 1) == os.path.join(directory, 'image_001.dat'))

    assert(XScanHelperImageFiles.template_index_to_image(
        template, 1) == 'image_001.dat')

    assert(XScanHelperImageFiles.image_to_template_directory(
        os.path.join(directory, 'image_001.dat')) == (template, directory))
    
    assert(XScanHelperImageFiles.image_to_index('image_001.dat') == 1)
    
    assert(XScanHelperImageFiles.image_to_template(
        'image_001.dat') == 'image_###.dat')
    
    return

def work_helper_image_formats():
    '''Test the static methods and properties in XScanHelperImageFormats.'''

    assert(XScanHelperImageFormats.check_format(
        XScanHelperImageFormats.FORMAT_CBF))
    assert(not(XScanHelperImageFormats.check_format('CBF')))

def work_xscan_factory():
    '''Test out the XScanFactory.'''

    directory = os.path.join(os.environ['XIA2_ROOT'], 'dxtbx', 'model',
                             'Tests')
    
    template = 'image_###.dat'

    xscans = [XScanFactory.Single(
        XScanHelperImageFiles.template_directory_index_to_image(
        template, directory, j + 1), XScanHelperImageFormats.FORMAT_CBF,
        1.0, 18 + 0.5 * j, 0.5, j) for j in range(20)]

    xscans.reverse()

    try:
        print sum(xscans[1:], xscans[0])
        print 'I should not see this message'
    except AssertionError, e:
        pass

    xscans.sort()
    print sum(xscans[1:], xscans[0])

    a = XScanFactory.Sum(xscans[:10])
    b = XScanFactory.Sum(xscans[10:])

    print a + b

    filename = XScanHelperImageFiles.template_directory_index_to_image(
        template, directory, 1)

    assert(len(XScanFactory.Search(filename)) == 20)

    print (a + b)[1:5]
    print (a + b)[:10]

    cbf = os.path.join(directory, 'phi_scan_001.cbf')

    print XScanFactory.imgCIF(cbf)
    
if __name__ == '__main__':

    work_helper_image_files()
    work_helper_image_formats()
    work_xscan_factory()

    

    

