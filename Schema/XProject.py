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

# hooks to all of the child objects

from Schema.XCrystal import XCrystal
from Schema.XWavelength import XWavelength

# .xinfo parser

from Handlers.XInfo import XInfo
from Handlers.Flags import Flags
from Handlers.Syminfo import Syminfo

# output stream
from Handlers.Streams import Chatter, Debug

class XProject():
    '''A representation of a complete project. This will contain a dictionary
    of crystals.'''

    def __init__(self, xinfo_file = None):

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

    def summarise(self):
        '''Produce summary information.'''

        summary = ['Project: %s' % self._name]
        for crystal in self._crystals.keys():
            for record in self._crystals[crystal].summarise():
                summary.append(record)

        return summary

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

            if crystals[crystal].has_key('reference_reflection_file'):
                xc.set_reference_reflection_file(
                    crystals[crystal]['reference_reflection_file'])
            if crystals[crystal].has_key('freer_file'):
                xc.set_freer_file(crystals[crystal]['freer_file'])

            # user assigned spacegroup
            if crystals[crystal].has_key('user_spacegroup'):
                xc.set_user_spacegroup(crystals[crystal]['user_spacegroup'])
            elif Flags.get_spacegroup():
                xc.set_user_spacegroup(Flags.get_spacegroup())

            for wavelength in crystals[crystal]['wavelengths'].keys():
                # FIXME 29/NOV/06 in here need to be able to cope with
                # no wavelength information - this should default to the
                # information in the image header (John Cowan pointed
                # out that this was untidy - requiring that it agrees
                # with the value in the header makes this almost
                # useless.)

                wave_info = crystals[crystal]['wavelengths'][wavelength]

                if not wave_info.has_key('wavelength'):
                    Debug.write(
                        'No wavelength value given for wavelength %s' %
                        wavelength)
                else:
                    Debug.write(
                        'Overriding value for wavelength %s to %8.6f' % \
                        (wavelength, float(wave_info['wavelength'])))

                # handle case where user writes f" in place of f''

                if wave_info.has_key('f"') and not \
                   wave_info.has_key('f\'\''):
                    wave_info['f\'\''] = wave_info['f"']

                xw = XWavelength(wavelength, xc,
                                 wavelength = wave_info.get('wavelength', 0.0),
                                 f_pr = wave_info.get('f\'', 0.0),
                                 f_prpr = wave_info.get('f\'\'', 0.0),
                                 dmin = wave_info.get('dmin', 0.0),
                                 dmax = wave_info.get('dmax', 0.0))

                # in here I also need to look and see if we have
                # been given any scaled reflection files...

                # check to see if we have a user supplied lattice...
                if crystals[crystal].has_key('user_spacegroup'):
                    lattice = Syminfo.get_lattice(
                        crystals[crystal]['user_spacegroup'])
                elif Flags.get_spacegroup():
                    lattice = Syminfo.get_lattice(Flags.get_spacegroup())
                elif Flags.get_lattice():
                    lattice = Flags.get_lattice()
                else:
                    lattice = None

                # and also user supplied cell constants - from either
                # the xinfo file (the first port of call) or the
                # command-line.

                if crystals[crystal].has_key('user_cell'):
                    cell = crystals[crystal]['user_cell']
                elif Flags.get_cell():
                    cell = Flags.get_cell()
                else:
                    cell = None

                dmin = wave_info.get('dmin', 0.0)
                dmax = wave_info.get('dmax', 0.0)

                if dmin == 0.0 and dmax == 0.0:
                    dmin = Flags.get_resolution_high()
                    dmax = Flags.get_resolution_low()

                # want to be able to locally override the resolution limits
                # for this sweep while leaving the rest for the data set
                # intact...

                for sweep_name in crystals[crystal]['sweeps'].keys():
                    sweep_info = crystals[crystal]['sweeps'][sweep_name]

                    dmin_old = dmin
                    dmax_old = dmax
                    replace = False

                    if 'RESOLUTION' in sweep_info:

                        values = map(float, sweep_info['RESOLUTION'].split())
                        if len(values) == 1:
                            dmin = values[0]
                        elif len(values) == 2:
                            dmin = min(values)
                            dmax = max(values)
                        else:
                            raise RuntimeError, \
                                  'bad resolution for sweep %s' % sweep_name

                        replace = True
                    
                    # FIXME: AJP to implement
                    if 'ice' in sweep_info:
                        pass
                    if 'excluded_regions' in sweep_info:
                        pass


                    if sweep_info['wavelength'] == wavelength:

                        frames_to_process = sweep_info.get('start_end')

                        if not frames_to_process and Flags.get_start_end():
                            frames_to_process = Flags.get_start_end()

                        xw.add_sweep(
                            sweep_name,
                            directory = sweep_info.get('DIRECTORY'),
                            image = sweep_info.get('IMAGE'),
                            beam = sweep_info.get('beam'),
                            reversephi = sweep_info.get('reversephi', False),
                            distance = sweep_info.get('distance'),
                            gain = float(sweep_info.get('GAIN', 0.0)),
                            dmin = dmin, dmax = dmax,
                            polarization = float(sweep_info.get(
                            'POLARIZATION', 0.0)),
                            frames_to_process = frames_to_process,
                            user_lattice = lattice,
                            user_cell = cell,
                            epoch = sweep_info.get('epoch', 0),
                            ice = sweep_info.get('ice', False),
                            excluded_regions = sweep_info.get(
                                'excluded_regions', []),
                            )

                    dmin = dmin_old
                    dmax = dmax_old

                xc.add_wavelength(xw)

            self.add_crystal(xc)

        return

    def write_xifo(self):
        '''Write an updated .xinfo file which takes into account the input
        provided by the user on the command line and any input xinfo
        file: this is what xia2 understood to be the problem.'''

        raise RuntimeError, 'FIXME this method must be implemented'

if __name__ == '__main__':
    import os

    xi_file = os.path.join(os.environ['XIA2_ROOT'], 'Data', 'Test', 'Xinfo', '1vpj.xinfo')

    xp = XProject(xi_file)

    Chatter.write(str(xp))
