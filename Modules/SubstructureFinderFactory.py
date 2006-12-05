#!/usr/bin/env python
# SubstructureFinderFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.


# 
# A factory for SubstructureFinder implementations. At the moment this will 
# support only Hyss.
#

import os
import sys
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Modules.HyssSubstructureFinder import HyssSubstructureFinder

def SubstructureFinder():
    '''Return a substructure finder.'''

    return HyssSubstructureFinder()


    
