#!/usr/bin/python
# 
# DEVELOPMENT CODE DO NOT USE
# 
# HAPhaserClass.py
# Maintained by G.Winter
# 
# A super class for implementing HA phasing systems. This is not really 
# designed to be used in anger, more for finding things out...

import os
import sys

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from lib.SubstructureLib import invert_hand
from lib.SymmetryLib import compute_enantiomorph

from Mtz2Scalepack import Mtz2Scalepack

class HAPhaserClass:

    def __init__(self):

        hap_input = __import__('hap_input')

        # next get the stuff we want from it

        self._input_dict = hap_input.input_dict
        self._mtz_file = hap_input.input_file

        # check we have enough input...
        if not self._input_dict.has_key('cell'):
            raise RuntimeError, 'cell not available'
        if not self._input_dict.has_key('spacegroup'):
            raise RuntimeError, 'spacegroup not available'
        if not self._input_dict.has_key('n_sites'):
            raise RuntimeError, 'n_sites not available'
        if not self._input_dict.has_key('atom'):
            raise RuntimeError, 'atom not available'
        if not self._input_dict.has_key('solvent'):
            raise RuntimeError, 'solvent not available'

        # check that the MTZ file has F columns etc. as well
        # as I's...

        self._cell = self._input_dict['cell']
        self._spacegroup = self._input_dict['spacegroup']
        self._nres = self._input_dict['nres']
        self._solvent = self._input_dict['solvent']

        m2s = Mtz2Scalepack()
        m2s.set_hklin(self._mtz_file)
        self._scalepack_files = m2s.convert()

        # next check we have metadata for each dataset
        for key in self._scalepack_files.keys():
            if not self._input_dict.has_key(key):
                raise RuntimeError, 'no input for %s' % key

        self._working_directory = os.getcwd()

        return

    def get_working_directory(self):
        return self._working_directory

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def compute_spacegroup_enantiomorph(self, spacegroup):
        return compute_enantiomorph(spacegroup)

    def compute_substructure_enantiomorph(self, substructure):
        return invert_hand(substructure)

    def phase(self):
        raise RuntimeError, 'overload me'

    
    
