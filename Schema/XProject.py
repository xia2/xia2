#!/usr/bin/env python
# XProject.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# A versioning object representation of a complete project - this
# represents the "top level" of the .xinfo hierarchy, and should
# exactly correspond to the contents of the .xinfo file.
# 
# 

import os
import sys
import math

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Object import Object

# hooks to all of the child objects

from Schema.XCrystal import XCrystal
from Schema.XWavelength import XWavelength
from Schema.XSweep import XSweep

# .xinfo parser

from Handlers.XInfo import XInfo

# output stream

from Handlers.Streams import Chatter

class XProject(Object):
    '''A versioning object representation of a complete project. This
    will contain a dictionary of crystals.'''

    def __init__(self, xinfo_file = None):
        Object.__init__(self)

        self._crystals = { }
        if xinfo_file:
            self.setup_from_xinfo_file(xinfo_file)
        else:
            self._name = None

        return

    def __repr__(self):
        result = 'Project: %s\n' % self._name
        for crystal in self._crystals.keys():
            result += str(self._crystals[crystal])
        return result[:-1]
        
    def __str__(self):
        return self.__repr__()

    def get_name(self):
        return self._name
    
    def add_crystal(self, xcrystal):
        '''Add a new xcrystal to the project.'''

        if not xcrystal.__class__.__name__ == 'XCrystal':
            raise RuntimeError, 'crystal must be class XCrystal.'

        if xcrystal.get_name() in self._crystals.keys():
            raise RuntimeError, 'XCrystal with name %s already exists' % \
                  xcrystal.get_name()

        self._crystals[xcrystal.get_name()] = xcrystal

        return

    def get_crystals(self):
        return self._crystals

    def setup_from_xinfo_file(self, xinfo_file):
        '''Set up this object & all subobjects based on the .xinfo
        file contents.'''

        xinfo = XInfo(xinfo_file)

        self._name = xinfo.get_project()
        crystals = xinfo.get_crystals()

        for crystal in crystals.keys():
            xc = XCrystal(crystal)
            if crystals[crystal].has_key('sequence'):
                xc.set_aa_sequence(crystals[crystal]['sequence'])
            if crystals[crystal].has_key('ha_info'):
                if crystals[crystal]['ha_info'] != { }:
                    xc.set_ha_info(crystals[crystal]['ha_info'])

            for wavelength in crystals[crystal]['wavelengths'].keys():
                wave_info = crystals[crystal]['wavelengths'][wavelength]
                xw = XWavelength(wavelength, xc,
                                 wave_info['wavelength'],
                                 wave_info.get('f\'', 0.0),
                                 wave_info.get('f\'\'', 0.0))

                for sweep in crystals[crystal]['sweeps'].keys():
                    sweep_info = crystals[crystal]['sweeps'][sweep]
                    if sweep_info['wavelength'] == wavelength:
                        xw.add_sweep(sweep,
                                     sweep_info['DIRECTORY'],
                                     sweep_info['IMAGE'],
                                     sweep_info.get('beam'))
                
                xc.add_wavelength(xw)

            self.add_crystal(xc)

        return

if __name__ == '__main__':
    import os

    xi_file = os.path.join(os.environ['DPA_ROOT'], 'Data', 'Test', 'Xinfo', '1vpj.xinfo')
    
    xp = XProject(xi_file)

    Chatter.write(str(xp))

    
    
