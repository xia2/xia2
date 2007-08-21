#!/usr/bin/env python
# BESTStrategyComputer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 21st August 2007
#
# A strategy computer implementation which makes use of Mosflm (for
# integration) and BEST to perform strategy calculations. Also available
# will be Chooch, to analyse scans and decide if we should perform a MAD
# or SAD experiment, and also decide the wavelengths. If the scan is
# not available then we just need to know the atom and we should gun for a
# high remote SAD experiment.
#
# Actually this decision is probably best left to another entity which can
# "wrap" the beamline or analyse the scans etc.
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from lib.Guff import auto_logfiler

from Schema.Interfaces.FrameProcessor import FrameProcessor
from Schema.Interfaces.StrategyComputer import StrategyComputer
from Wrappers.CCP4.Mosflm import Mosflm
from Wrappers.EMBL.Best import Best
from Wrappers.XIA.Diffdump import Diffdump
from Wrappers.Labelit.LabelitScreen import LabelitScreen

class BESTStrategyComputer(FrameProcessor,
                          StrategyComputer):
    '''A strategy computer implentation using BEST and Mosflm...'''

    def __init__(self):
        FrameProcessor.__init__(self)
        StrategyComputer.__init__(self)

        self._working_directory = os.getcwd()

        return

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def _strategy_prepare(self):
        '''Use Mosflm to integrate all of the images available.'''

        # search for all of the matching images - these will all be
        # used for the stategy determination

        images = self.get_matching_images()

        mosflm = Mosflm()
        auto_logfiler(mosflm)
        
        mosflm.setup_from_image(self.get_image_name(images[0]))
        self._dat, self._par, self._hkl = mosflm.generate_best_files(
            self._stgcr_indexer, images)

        # ID the detector class from the first image

        diffdump = Diffdump()
        diffdump.set_image(self.get_image_name(images[0]))
        self._header = diffdump.readheader()

        self._exposure_time = self._header['exposure_time']
        self._detector_name = self.guess_detector_name()

        return

    def _strategy(self):
        '''Actually compute the strategy.'''

        # write the three BEST files out with helpful names

        open(os.path.join(self.get_working_directory(),
                          'strategy.dat'), 'w').write(self._dat)
        open(os.path.join(self.get_working_directory(),
                          'strategy.par'), 'w').write(self._par)
        open(os.path.join(self.get_working_directory(),
                          'strategy.hkl'), 'w').write(self._hkl)

        best = Best()
        auto_logfiler(best)
        
        best.set_dat_file('strategy.dat')
        best.set_par_file('strategy.par')
        best.add_hkl_file('strategy.hkl')

        best.set_exposure_time(self._exposure_time)
        best.set_detector_name(self._detector_name)

        if self._stgcr_strategy_type == 'native':
            best.set_anomalous(False)
        else:
            best.set_anomalous(True)

        if self._stgcr_strategy_type == 'sad':
            best.set_i_over_sig(4.0)

        best.compute_strategy()

        self._stgcr_strategy = best.get_strategy()

        return

    def guess_detector_name(self):
        class_to_name = {
            'adsc q4':'q4',
            'adsc q4 2x2 binned':'q4-2x',
            'adsc q210':'q210',
            'adsc q210 2x2 binned':'q210-2x',
            'adsc q315':'q315',
            'adsc q315 2x2 binned':'q315-2x',
            'mar 135':'mar135',
            'mar 165':'mar165',
            'mar 225':'mar225',
            'mar 325':'mar325',
            'raxis IV':'raxis'
            }
            
        detector_class = self._header['detector_class']
        
        return class_to_name[detector_class]

    
if __name__ == '__main__':
    # then run a test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    ls = LabelitScreen()

    directory = os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Images')

    ls.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    ls.index()

    bsc = BESTStrategyComputer()

    bsc.set_strategy_indexer(ls)
    bsc.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    # native strategy

    print 'Strategies:'

    bsc.set_strategy_type('native')
    strategy = bsc.get_strategy()

    for s in strategy:
        print s

    # MAD strategy

    bsc.set_strategy_type('mad')
    strategy = bsc.get_strategy()

    for s in strategy:
        print s

    # SAD strategy

    bsc.set_strategy_type('sad')
    strategy = bsc.get_strategy()

    for s in strategy:
        print s
