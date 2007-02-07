#!/usr/bin/env python
# PhaseComputer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
# 
# An interface to represent programs which will compute initial phases
# from heavy atoms sites, perhaps refining them along the way. Examples
# are bp3, phaser, sharp. This will take as input a list of heavy atom
# sites from a SubstructureFinder (actually it will take the finder) and
# some reflections with associated F', F'' values - most likely set up from
# an XCrystal object.

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Handlers.Streams import Chatter

class PhaseCalculator:
    '''An interface to represent programs which compute phases from anomalous
    data and heavy atom locations.'''

    def __init__(self):

        # definately needed input data
        self._pcr_sites = None

        # this will be used internally e.g. for passing information
        # from prepare to do...
        self._pcr_input_reflection_files = { }
        self._pcr_b_factor = 0.0

        # a place to store a scaler where much of the raw information
        # will come from - also needed if we are going through the .xinfo
        # hierarchy, otherwise (e.g. for testing) the correct information
        # can be pre-set. Or perhaps I should have a NULL scaler for this?
        self._pcr_scaler = None

        # optional input data 
        self._pcr_spacegroup = None
        self._pcr_test_enantionorph = True

        # places to store the output
        self._pcr_phased_reflection_files = { }
        self._pcr_statistics = { }

        # job management stuff
        self._pcr_prepare_done = False
        self._pcr_done = False
        self._working_directory = os.getcwd()

        return

    # functions which need to be overloaded

    def _phase_compute_prepare(self):
        raise RuntimeError, 'overload me'

    def _phase_compute(self):
        raise RuntimeError, 'overload me'

    # administrative guff to allow propogation of e.g. working
    # directories to actual processes
    
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    # job control flags

    def set_phase_computer_prepare_done(self, done = True):
        self._pcr_prepare_done = done
        return
        
    def set_phase_computer_done(self, done = True):
        self._pcr_done = done
        return

    def set_phase_computer_scaler(self, scaler):
        '''Set the input scaler.'''

        # check input is a scaler

        # save it

        self._pcr_scaler = scaler

        return

    def set_phase_computer_sites(self, sites):
        '''Set the input sites to phase from.'''

        # check that these are sites

        # store them

        self._pcr_sites = sites

        return

    def phase(self):
        '''Actually perform the phasing process - note that this should
        not be explicitly called by anyone else - this should really be
        an internal method.'''

        # check that the required input is present

        # should these be set at the calling stage, or by a reset method?

        self._pcr_done = False
        self._pcr_prepare_done = False

        # set up the processing with the standard framework...

        while not self._pcr_done:
            while not self._pcr_prepare_done:

                Chatter.write('Preparing to do some phasing...')

                self._pcr_prepare_done = True
                self._phase_compute_prepare()

            Chatter.write('Doing some phasing...')

            self._pcr_done = True
            self._phase_compute()

        return

    # in here need getter methods now which may perform the phasing...

    def get_phase_computer_phased_reflection_files(self):
        '''Get the phased reflection files.'''

        self.phase()

        # FIXME this should return a copy
        return self._pcr_phased_reflection_files

    def get_phase_computer_statistics(self):
        '''Get the statistics from phase calculation.'''

        self.phase()

        # FIXME this should return a copy
        return self._pcr_statistics

    
