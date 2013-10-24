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

    def autoindex(self, images = None):
        from Wrappers.Mosflm.Autoindex import Autoindex
        ai = Autoindex()
        solutions = ai(self, images)
        for s in solutions:
            print '%3d %2s %.3f' % (s.penalty, s.latt, s.fracn), \
              '%5.1f %5.1f %5.1f %5.1f %5.1f %5.1f' % s.cell
        return

    def findspots_autoindex(self, images = None):
        from Wrappers.Mosflm.Findspots import Findspots
        from Wrappers.Mosflm.Autoindex import Autoindex

        ai = Autoindex()
        
        if images is None:
            images = ai.select_images(self)
        
        fs = Findspots()
        spot_file = fs(self, images)
        ai.set_spot_file(spot_file)
        solutions = ai(self, images)
        for s in solutions:
            print '%3d %2s %.3f' % (s.penalty, s.latt, s.fracn), \
              '%5.1f %5.1f %5.1f %5.1f %5.1f %5.1f' % s.cell
        return
        
def tst_autoindex(image):
    p = Platform(image)
    return p.autoindex(p.get_matching_images()[:1])
    
def tst_findspots(image):
    p = Platform(image)
    return p.findspots(p.get_matching_images()[:1])

def tst_findspots_autoindex(image):
    p = Platform(image)
    return p.findspots_autoindex(p.get_matching_images()[:1])

def tst_findspots_autoindex_select(image):
    p = Platform(image)
    return p.findspots_autoindex()

def tst_all():
    import sys
    tst_findspots(sys.argv[1])
    tst_autoindex(sys.argv[1])
    tst_findspots_autoindex(sys.argv[1])
    tst_findspots_autoindex_select(sys.argv[1])

if __name__ == '__main__':
    tst_all()    
