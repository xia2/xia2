#!/usr/bin/env python
# AnalyseMyIntensities.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th June 2007
# 
# A tool to use for the analysis and gathering of scaled intensity data
# from a single macromolecular crystal. This will be both a module (for
# use in xia2) and an application in it's own right, AMI.
#

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.CCP4Factory import CCP4Factory


from Modules.Scalepack2Mtz import Scalepack2Mtz
from Modules.Mtz2Scalepack import Mtz2Scalepack



class AnalyseMyIntensities:
    '''A class to use for intensity analysis. This will gather intensities
    (merged or unmerged) from multiple data sets and merge them together
    as well as telling you all about your data.'''

    def __init__(self):
        self._hklin_list = []
        self._hklout = ''
        self._solvent = 0.0
        self._nres = 0
        self._nmol = 0
        self._cell = None
        self._symm = None
        self._reindex = None

        self._working_directory = os.getcwd()

        self._factory = CCP4Factory()

        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        return

    def get_working_directory(self):
        return self._working_directory 

    # input functions

    def add_hklin(self, hklin):
        self._hklin_list.append(hklin)
        return

    def set_hklout(self, hklout):
        self._hklout = hklout
        return

    def set_solvent(self, solvent):
        self._solvent = solvent
        return

    def set_nres(self, nres):
        self._nres = nres
        return

    def set_nmol(self, nmol):
        self._nmol = nmol
        return

    def set_cell(self, cell):
        self._cell = cell
        return

    def set_symm(self, symm):
        self._symm = symm
        return

    def set_reindex(self, reindex):
        self._reindex = reindex
        return

    
    
