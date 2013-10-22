#!/usr/bin/env python
# Platform.py
#
#   Copyright (C) 2013 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Test platform for new Mosflm wrapper implementations.

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Schema.Interfaces.FrameProcessor import FrameProcessor

class Platform(FrameProcessor):
    def __init__(self, image):
        FrameProcessor.__init__(self, image)
        
    def findspots(self, images):
        from Wrappers.Mosflm.Findspots import Findspots
        fs = Findspots()
        return fs(self, images)

    def autoindex(self, images):
        from Wrappers.Mosflm.Autoindex import Autoindex
        ai = Autoindex()
        return ai(self, images)

if __name__ == '__main__':
    p = Platform(sys.argv[1])
    print p.findspots(p.get_matching_images()[:1])
    print p.autoindex(p.get_matching_images()[:1])
    
