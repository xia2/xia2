#!/usr/bin/env python
# XDSPointgroup.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 8th January 2007
# 
# A pointgroup determination module for XDS, which will run the results of
# CORRECT in P1 into Combat then Pointless. Nope, this will run CORRECT
# with whatever spacegroup was used for integration... Test this on the
# results from BA0296!
#
# 23/MAY/07 - now make it so that this works from the results of CORRECT
#             rather than from INTEGRATE.HKL...
# 

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.Pointless import Pointless as _Pointless
from Wrappers.CCP4.Combat import Combat as _Combat
from Wrappers.CCP4.Scala import Scala as _Scala
from Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz

from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter

class XDSPointgroup:
    '''A class to allow determination of pointgroups from the results
    of XDS CORRECT.'''

    def __init__(self):
        '''Set up and check all programs are available.'''

        self._hklin = None
        self._hklref = None
        
        self._working_directory = os.getcwd()
        
        self._pointless_results = None

        # check the programs

        c = _Combat()
        p = _Pointless()
        s = _Scala()

        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def set_hklin(self, hklin):
        self._hklin = hklin
        return

    def set_hklref(self, hklref):
        self._hklref = hklref
        return

    def Combat(self):
        combat = _Combat()
        combat.set_working_directory(self.get_working_directory())
        auto_logfiler(combat)

        return combat

    def Sortmtz(self):
        sortmtz = _Sortmtz()
        sortmtz.set_working_directory(self.get_working_directory())
        auto_logfiler(sortmtz)

        return sortmtz

    def Scala(self):
        scala = _Scala()
        scala.set_working_directory(self.get_working_directory())
        auto_logfiler(scala)

        return scala

    def Pointless(self):
        pointless = _Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)

        return pointless

    def run(self):
        '''XDS_ASCII.HKL + [combat] -> MTZ + [pointless] -> pointgroup.'''

        combat = self.Combat()
        combat.set_hklin(self._hklin)
        temp_mtz = os.path.join(self.get_working_directory(),
                                'xds-pointgroup-temp.mtz')
        combat.set_hklout(temp_mtz)
        combat.run()

        # if HKLREF assume that the reference file is also from XDS
        # CORRECT and therefore convert with COMBAT to MTZ, SORT and
        # quickly SCALE to give the reference data set.

        reference_mtz = None

        if self._hklref:
            combat = self.Combat()
            combat.set_hklin(self._hklin)
            ref_mtz = os.path.join(self.get_working_directory(),
                                   'xds-pointgroup-reference-unsorted.mtz')
            combat.set_hklout(ref_mtz)
            combat.run()

            sortmtz = self.Sortmtz()
            sortmtz.add_hklin(ref_mtz)
            ref_mtz = os.path.join(self.get_working_directory(),
                                   'xds-pointgroup-reference-sorted.mtz')
            sortmtz.set_hklout(ref_mtz)
            sortmtz.sort()
            
            scala = self.Scala()
            
            scala.set_hklin(ref_mtz)
            reference_mtz = os.path.join(self.get_working_directory(),
                                         'xds-pointgroup-reference.mtz')
            scala.set_hklout(reference_mtz)
            scala.quick_scale()

            pointless = self.Pointless()
            pointless.set_hklin(temp_mtz)
            pointless.set_hklref(reference_mtz)
            pointless.decide_pointgroup()
            
        else:
            pointless = self.Pointless()
            pointless.set_hklin(temp_mtz)
            pointless.decide_pointgroup()
            
        print pointless.get_pointgroup()
        print pointless.get_reindex_operator()
        print pointless.get_reindex_matrix()        
    

if __name__ == '__main__':

    xp = XDSPointgroup()
    xp.set_hklin('XDS_ASCII.HKL')
    xp.run()

    xp = XDSPointgroup()
    xp.set_hklin('XDS_ASCII.HKL')
    xp.set_hklref('XDS_ASCII.HKL')
    xp.run()
