#!/usr/bin/env python
# StrategyComputer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 4th May 2007
#
# An interface to strategy calculation - this should compute a strategy
# completely given e.g. some images and an Indexer. The Indexer is to allow
# some external control over the indexing, as this should be external. If
# the strategy computer wants to do some integration of the images (e.g.
# for BEST) then that's fine.
#
# See bug # 2335
# 
# Reference implementation of this will be the BESTStrategyComputer. This
# will integrate the frames provided (which means that a StrategyComputer
# will also need to present a FrameProcessor interface) and then run BEST
# with the results.
#
# This class will use the prefix stgcr.
#

import os
import sys
import copy
import exceptions

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from lib.Guff import inherits_from

class StrategyElement:
    '''An element of a strategy, that is a wedge to measure.'''

    def __init__(self, phi_start, phi_width, distance,
                 images, exposure_time):
        '''Create a new strategy element.'''

        self._phi_start = phi_start
        self._phi_width = phi_width
        self._phi_end = phi_start + images * phi_width
        self._distance = distance
        self._exposure_time = exposure_time

        return

    def __repr__(self):
        return '%6.2f -> %6.2f (%.2f) @ %6.2f mm [%6.2f s]' % \
               (self._phi_start, self._phi_end, self._phi_width,
                self._distance, self._exposure_time)

    def get_phi_start(self):
        return self._phi_start

    def get_phi_width(self):
        return self._phi_width

    def get_phi_end(self):
        return self._phi_end

    def get_distance(self):
        return self._distance

    def get_exposure_time(self):
        return self._exposure_time

class StrategyComputer:
    '''An interface which must be used to present the functionality of a
    program which performs stragegy calculations.'''

    def __init__(self):

        self._stgcr_indexer = None

        # flags to control program flow
        self._stgcr_prepare_done = done
        self._stgcr_done = done
        
        # strategy requirements - in simple terms MAD/SAD/NATIVE
        # resolution (where I/sigma ~ 2) and complexity.

        # this will be obtained from the input images...
        # though may be overloaded.
        self._stgcr_resolution = None

        # allowed values = 'native', 'sad', 'mad'
        self._stgcr_strategy_type = None

        # allowed values = 'simple', 'complex'
        self._stgcr_strategy_complexity = 'simple'

        # results - this will be a list of StrategyElements
        self._stgcr_strategy = []

    def set_strategy_indexer(self, indexer):
        '''Set the indexer implementation to use for this integration.'''

        if not inherits_from(indexer.__class__, 'Indexer'):
            raise RuntimeError, 'input %s is not an Indexer implementation' % \
                  indexer.__name__

        self._stgcr_indexer = indexer
        self.set_strategy_computer_prepare_done(False)
        return

    def set_strategy_resolution(self, resolution):
        self._stgcr_resolution = resolution
        return

    def set_strategy_type(self, strategy_type):
        # check that this is an allowed type
        if not strategy_type.lower() in ['native', 'sad', 'mad']:
            raise RuntimeError, 'unknown strategy type "%s"' % \
                  strategy_type            
        self._stgcr_strategy_type = strategy_type.lower()
        return

    def set_strategy_complexity(self, strategy_complexity):
        # check that this is an allowed complexity
        if not strategy_complexity.lower() in ['simple', 'complex']:
            raise RuntimeError, 'unknown strategy complexity "%s"' % \
                  strategy_complexity
        self._stgcr_strategy_complexity = strategy_complexity.lower()
        return

    def get_strategy(self):
        '''Get the resulting strategy.'''

        self.strategy()

        return copy.deepcopy(self._stgcr_strategy)

    # flag handling
    
    def set_strategy_prepare_done(self, done = True):
        self._stgcr_prepare_done = done
        if not done:
            self.set_strategy_done(False)
        return
        
    def set_strategy_done(self, done = True):
        self._stgcr_done = done
        return

    # working functions to be overloaded - prepare is e.g. for the integration
    # of the images, strategy is for the actual strategy calculation.

    def _strategy_prepare(self):
        raise RuntimeError, 'overload me'

    def _strategy(self):
        raise RuntimeError, 'overload me'

    # main loop
        
    def strategy(self):
        '''Actually compute the strategy using the _strategy_prepare and
        _strategy functions.'''

        while not self.get_strategy_done():
            while not self.get_strategy_prepare_done():
                self.set_strategy_prepare_done(True)
                self._strategy_prepare()

            self.set_strategy_done(True)
            self._strategy()

        return

    
