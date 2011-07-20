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

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.XScan import XScan
from Schema.XScanHelpers import XScanHelperImageFiles

def work_helper_image_files():
    '''Test the static methods in XScanHelperImageFiles.'''

    helper = XScanHelperImageFiles()

    directory = os.path.join(os.environ['XIA2_ROOT'], 'Schema', 'Tests')
    template = 'image_###.dat'

    assert(len(helper.template_directory_to_indices(
        template, directory)) == 20)

    assert(helper.template_directory_index_to_image(template, directory, 1) ==
           os.path.join(directory, 'image_001.dat'))

    assert(helper.template_index_to_image(template, 1) == 'image_001.dat')

    assert(helper.image_to_template_directory(
        os.path.join(directory, 'image_001.dat')) == (template, directory))

    assert(helper.image_to_index('image_001.dat') == 1)

    assert(helper.image_to_template('image_001.dat') == 'image_###.dat')
    
    return


if __name__ == '__main__':

    work_helper_image_files()

    

    

