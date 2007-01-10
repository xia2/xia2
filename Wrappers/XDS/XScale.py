#!/usr/bin/env python
# XScale.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper for XSCALE, the XDS Scaling program.
#

import os
import sys
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def XScale(DriverType = None):

    DriverInstance = DriverFactory.Driver(DriverType)

    class XScaleWrapper(DriverInstance.__class__):
        '''A wrapper for wrapping XSCALE.'''

        def __init__(self):

            # set up the object ancestors...
            DriverInstance.__class__.__init__(self)

            # now set myself up...
            self.set_executable('xscale')

            # overall information
            self._resolution_shells = []
            self._cell = None
            self._spacegroup_number = None

            # input reflections information - including grouping information
            # in the same way as the .xinfo files - through the wavelength
            # names, which will be used for the output files.
            self._input_reflection_files = []
            self._input_reflection_wavelength_names = []
            self._input_resolution_ranges = []

            # decisions about the scaling
            self._crystal = None
            self._zero_dose = False
            self._anomalous = True
            self._merge = False

            return

        def set_spacegroup_number(self, spacegroup_number):
            self._spacegroup_number = spacegroup_number
            return

        def set_cell(self, cell):
            self._cell = cell
            return

    return XScaleWrapper()
