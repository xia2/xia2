#!/usr/bin/env python
# XProject.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A versioning object representation of a complete project - this
# represents the "top level" of the .xinfo hierarchy, and should
# exactly correspond to the contents of the .xinfo file.
# 
# Thoughts:
# Scaling will fix radiation damage issues, so I don't need epochs
# in the post-scaling universe.

import os
import sys
import math
import exceptions

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Object import Object

# hooks to all of the child objects

from Schema.XCrystal import XCrystal
from Schema.XWavelength import XWavelength

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
            #try:
            self.setup_from_xinfo_file(xinfo_file)
            #except exceptions.Exception, e:
            # there was an error in this .xinfo file...
            #raise RuntimeError, 'Error "%s" parsing .xinfo file:\n%s' % \
            # (str(e), open(xinfo_file, 'r').read())
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
            xc = XCrystal(crystal, self)
            if crystals[crystal].has_key('sequence'):
                xc.set_aa_sequence(crystals[crystal]['sequence'])
            if crystals[crystal].has_key('ha_info'):
                if crystals[crystal]['ha_info'] != { }:
                    xc.set_ha_info(crystals[crystal]['ha_info'])

            if crystals[crystal].has_key('scaled_merged_reflection_file'):
                xc.set_scaled_merged_reflections(
                    crystals[crystal]['scaled_merged_reflections'])

            for wavelength in crystals[crystal]['wavelengths'].keys():
                # FIXME 29/NOV/06 in here need to be able to cope with
                # no wavelength information - this should default to the
                # information in the image header (John Cowan pointed
                # out that this was untidy - requiring that it agrees
                # with the value in the header makes this almost
                # useless.)

                wave_info = crystals[crystal]['wavelengths'][wavelength]

                if not wave_info.has_key('wavelength'):
                    Chatter.write(
                        'No wavelength value given for wavelength %s' %
                        wavelength)
                else:
                    Chatter.write(
                        'Overriding value for wavelength %s to %8.6f' % \
                        (wavelength, float(wave_info['wavelength'])))

                xw = XWavelength(wavelength, xc,
                                 wave_info.get('wavelength', 0.0),
                                 wave_info.get('f\'', 0.0),
                                 wave_info.get('f\'\'', 0.0))

                # in here I also need to look and see if we have
                # been given any scaled reflection files...

                for sweep_name in crystals[crystal]['sweeps'].keys():
                    sweep_info = crystals[crystal]['sweeps'][sweep_name]
                    if sweep_info['wavelength'] == wavelength:
                        xw.add_sweep(
                            sweep_name,
                            directory = sweep_info.get('DIRECTORY'),
                            image = sweep_info.get('IMAGE'),
                            integrated_reflection_file = \
                            sweep_info.get('INTEGRATED_REFLECTION_FILE'),
                            beam = sweep_info.get('beam'),
                            distance = sweep_info.get('distance'),
                            gain = float(sweep_info.get('GAIN', 0.0)),
                            frames_to_process = sweep_info.get('start_end'),
                            epoch = sweep_info.get('epoch', 0))
                
                xc.add_wavelength(xw)

            self.add_crystal(xc)

        return

if __name__ == '__main__':
    import os

    xi_file = os.path.join(os.environ['XIA2_ROOT'], 'Data', 'Test', 'Xinfo', '1vpj.xinfo')
    
    xp = XProject(xi_file)

    Chatter.write(str(xp))

    
    
