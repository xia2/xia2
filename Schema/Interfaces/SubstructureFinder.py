#!/usr/bin/env python
# SubstructureFinder.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
# 
# This is an interface which substructure determination programs should
# provide - note well that this will have two phases, prepare to find
# and find, and should be initiated by calling get_sites() - this method
# will return a list containing dictionaries describing the sites.
# 
# I need to decide what this will be provided as input - a Scaler,
# perhaps? Yes, it will have to be a scaler. This means I may need a 
# fake scaler...
#

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

class SubstructureFinder:
    '''A class to represent the problem of substructure determination.'''

    def __init__(self):

        # local parameters - these will need to come from somewhere

        self._ssfnd_n_sites = 0
        self._ssfnd_atom = None
        self._ssfnd_spacegroup = None

        # input actors - these are where the actual data will come from
        
        self._ssfnd_scaler = None

        # input parameters (these may or may not be used, e.g. using
        # solve or hyss to find sites) - this will be keyed to
        # provide wavelength, f', f'' and wavelength name, the last
        # of which should be usable to get specific information from the
        # Scaler (e.g. a .sca file for the PEAK, etc.)
        self._ssfnd_wavelength_info = {}

        # output

        self._ssfnd_sites = None

        # job management flags

        self._ssfnd_prepare_done = False
        self._ssfnd_done = False

        # handle information

        self._ssfnd_name = None
        self._working_directory = os.getcwd()

        return

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def find(self):
        '''Actually initiate the finding process...'''

        # fixme need to add the checks in here

        while not self._ssfnd_done:
            self._ssfnd_done = True

            while not self._ssfnd_prepare_done:
                self._ssfnd_prepare_done = True

                self._substructure_find_prepare()
                
            self._substructure_find()

        return

    # these methods need to be overloaded

    def _substructure_find_prepare(self):
        raise RuntimeError, 'overload me'

    def _substructure_find(self):
        raise RuntimeError, 'overload me'

    # getter, setter methods

    def substructure_find_add_wavelength_info(self,
                                              wavelength_name,
                                              wavelength,
                                              f_pr,
                                              f_prpr):
        '''Set input wavelength information.'''

        if self._ssfnd_wavelength_info.has_key(wavelength_name):
            raise RuntimeError, 'wavelength %s already defined' % \
                  wavelength_name

        self._ssfnd_wavelength_info[
            wavelength_name] = (wavelength, f_pr, f_prpr)

        return
                                                     
    def substructure_find_set_n_sites(self, n_sites):
        self._ssfnd_n_sites = n_sites
        return

    def substructure_find_set_atom(self, atom):
        self._ssfnd_atom = atom
        return

    def substructure_find_set_spacegroup(self, spacegroup):
        self._ssfnd_spacegroup = spacegroup
        return

    def substructure_find_set_scaler(self, scaler):
        self._ssfnd_scaler = scaler
        return

    def substructure_find_get_sites(self):
        '''Actually get out the sites.'''

        # this will only run if needed
        self.find()
        
        return self._ssfnd_sites

    def substructure_find_set_name(self, name):
        '''Set a name name.'''

        self._ssfnd_name = name

        return

    
