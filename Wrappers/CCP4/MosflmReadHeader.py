#!/usr/bin/env python
# MosflmReadHeader.py
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 8th July 2010
#
# A replacement for the CCP4 program Diffdump using Mosflm - yes, this is a
# sledgehammer to crack a nut but hopefully more portable.

import os
import sys
import math
import exceptions
from xml.dom.minidom import parseString as parse

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'
if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def MosflmReadHeader(DriverType = None):
    '''A factory for MosflmReadHeaderWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class MosflmReadHeaderWrapper(DriverInstance.__class__):
        '''A wrapper for Mosflm to read image headers.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('ipmosflm')
            
            self._header = { }

            return
            
    return MosflmReadHeaderWrapper()
    

