#!/usr/bin/env python
# HyssSubstructureFinder.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th December 2006
# 
# An implementation of the SubstructureFinder interface using phenix.hyss
# (a separately licensed program) and, possibly, shelxc to prepare the data
# if available.
# 
# FIXME 04/DEC/06 if there are no wavelengths which "look" anomalous - e.g.
#                 they are called PEAK, INFL, LREM, HREM, SAD - then this
#                 should barf.

import sys
import os
import exceptions

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Schema.Interfaces.SubstructureFinder import SubstructureFinder

from Wrappers.Shelx.Shelxc import Shelxc
from Wrappers.Phenix.Hyss import Hyss

from Handlers.Streams import Debug
from lib.Guff import auto_logfiler

class HyssSubstructureFinder(SubstructureFinder):
    '''An implementation of the SubstructureFinder interfaces using
    the phenix program hyss and perhaps, if available, shelxc to
    prepare the input data.'''

    def __init__(self):
        SubstructureFinder.__init__(self)

        self._hklf3_in = None

        # check that hyss exists...

        hyss = Hyss()

        return

    def _shelxc_prepare_data(self):
        '''Use shelxc to prepare the data (now we know we have it...'''

        # FIXME 04/DEC/06 this should go through a get_scaler()

        shelxc = Shelxc()

	shelxc.set_working_directory(self.get_working_directory())
	auto_logfiler(shelxc)

        # FIXME need to be able to cope with these files not being
        # present => being able to run come kind of mtz2sca to
        # regenerate them...

        # scafiles = self._ssfnd_scaler.get_scaled_merged_reflections(
        # )['sca']
        scafiles = self._ssfnd_scaler.get_scaled_reflections('sca')
        wavelengths = scafiles.keys()

        # do the reflection file stuff - FIXED this should
        # check against the wavelengths it has been explicitly
        # given if provided. 

        for wavelength in wavelengths:
            if self._ssfnd_wavelength_info and \
                   not self._ssfnd_wavelength_info.has_key(wavelength):
                continue

            # if we get to here then we are either supposed to use it
            # or we are free to use whatever
            
            if wavelength.upper() == 'PEAK':
                shelxc.set_peak(scafiles[wavelength])
            if wavelength.upper() == 'INFL':
                shelxc.set_infl(scafiles[wavelength])
            if wavelength.upper() == 'LREM':
                shelxc.set_lrem(scafiles[wavelength])
            if wavelength.upper() == 'HREM':
                shelxc.set_hrem(scafiles[wavelength])
            if wavelength.upper() == 'SAD':
                shelxc.set_sad(scafiles[wavelength])
            if wavelength.upper() == 'NATIVE':
                shelxc.set_native(scafiles[wavelength])

        # now set the symmetry, cell &c.

        shelxc.set_cell(self._ssfnd_scaler.get_scaler_cell())
        shelxc.set_symmetry(self._ssfnd_spacegroup)
        shelxc.set_n_sites(self._ssfnd_n_sites)

        shelxc.set_name(self._ssfnd_name)

        shelxc.prepare()
        
        self._hklf3_in = shelxc.get_fa_hkl()
        
    def _substructure_find_prepare(self):
        '''Prepare the data for site location using shelxc.'''

        # try:
        if True:
            shelxc = Shelxc()
            Debug.write('Using shelxc to prepare HA data.')
            self._shelxc_prepare_data()
        # except exceptions.Exception, e:
        # Debug.write('No shelxc? %s' % str(e))

        return

    def _substructure_find(self):
        '''Actually find the sites, perhaps with prepared data.'''

        hyss = Hyss()

	hyss.set_working_directory(self.get_working_directory())
	auto_logfiler(hyss)

        if self._hklf3_in:
            hyss.set_hklin(self._hklf3_in)
            hyss.set_hklin_type('hklf3')

            # this should be defined as a part of the interface...
            hyss.set_cell(self._ssfnd_scaler.get_scaler_cell())

        else:
            # hyss.set_hklin(self._ssfnd_scaler.get_scaled_merged_reflections(
            # )['mtz_merged_free'])
            hyss.set_hklin(self._ssfnd_scaler.get_scaled_reflections('mtz'))

        # set the spacegroup and number of sites

        hyss.set_spacegroup(self._ssfnd_spacegroup)
        hyss.set_n_sites(self._ssfnd_n_sites)
        hyss.set_atom(self._ssfnd_atom)
        hyss.find_substructure()

        self._ssfnd_sites = hyss.get_sites()

if __name__ == '__main__':
    # need to be able to add in a unit test here...

    pass
