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

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.XDS.XDSCorrect import XDSCorrect as _Correct
from Wrappers.CCP4.Pointless import Pointless as _Pointless
from Wrappers.CCP4.Combat import Combat as _Combat
from Schema.Interfaces.FrameProcessor import FrameProcessor


from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter

class XDSPointgroup(FrameProcessor):
    '''A class to allow determination of pointgroups from the results
    of XDS INTEGRATE. This should be run prior to correct.'''

    def __init__(self):
        '''Set up and check all programs are available.'''

        FrameProcessor.__init__(self)
        
        self._hklin = None
        self._working_directory = os.getcwd()
        
        self._pointless_results = None

        # check the programs

        x = _Correct()
        c = _Combat()
        p = _Pointless()

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

    def Correct(self):
        correct = _Correct()
        correct.set_working_directory(self.get_working_directory())

        correct.setup_from_image(self.get_image_name(
            self.get_matching_images()[0]))

        auto_logfiler(correct)

        return correct

    def Combat(self):
        combat = _Combat()
        combat.set_working_directory(self.get_working_directory())
        auto_logfiler(combat)

        return combat

    def Pointless(self):
        pointless = _Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)

        return pointless

    def run(self):
        '''INTEGRATE.HKL + [combat] -> MTZ + [pointless] -> pointgroup.'''

        correct = self.Correct()

        # correct.set_spacegroup_number(1)
        correct.set_integrate_hkl(self._hklin)

        correct.set_data_range(min(self.get_matching_images()),
                               max(self.get_matching_images()))

        correct.run()

        combat = self.Combat()
        combat.set_hklin(correct.get_xds_ascii_hkl())
        temp_mtz = os.path.join(self.get_working_directory(),
                                'xds-pointgroup-temp.mtz')
        combat.set_hklout(temp_mtz)
        combat.run()

        pointless = self.Pointless()
        pointless.set_hklin(temp_mtz)
        pointless.decide_pointgroup()

        print pointless.get_pointgroup()
        print pointless.get_reindex_operator()
        print pointless.get_reindex_matrix()        

if __name__ == '__main__':

    xp = XDSPointgroup()

    directory = os.path.join('/data', 'graeme', 'insulin', 'demo')

    xp.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))
    xp.set_hklin('INTEGRATE.HKL')

    xp.run()
