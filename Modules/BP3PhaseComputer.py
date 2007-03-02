#!/usr/bin/env python
# BP3PhaseComputer.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# An implementation of the PhaseComputer interface using the program BP3.
# This will also include Wilson for assignment of the B factor - just 
# in case it is not provided as input.
# 

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.PhaseComputer import PhaseComputer

# the wrappers that this will use - these are renamed so that the internal
# factory version can be used...

from Wrappers.CCP4.Wilson import Wilson as _Wilson
from Wrappers.CCP4.BP3 import BP3 as _BP3
from Wrappers.CCP4.Abs import Abs as _Abs

class BP3PhaseComputer(PhaseComputer):
    '''An implementation of PhaseComputer using BP3 and other CCP4 support
    applications.'''

    def __init__(self):

        # interface constructor
        PhaseComputer.__init__(self)

        # test that the programs we need are available

        bp3 = _BP3()
        a = Abs()
        w = Wilson()

        # set up internal odds and ends

        self._test_both_hands = None
        self._correct_hand = None

        return

    # factory

    def BP3(self):
        '''Create a BP3 wrapper from _BP3 - set the working directory
        and log file stuff as a part of this...'''
        bp3 = _BP3()
        bp3.set_working_directory(self.get_working_directory())
        auto_logfiler(bp3)
        return bp3    

    def Abs(self):
        '''Create a Abs wrapper from _Abs - set the working directory
        and log file stuff as a part of this...'''
        abs = _Abs()
        abs.set_working_directory(self.get_working_directory())
        auto_logfiler(abs)
        return abs
    
    def Wilson(self):
        '''Create a Wilson wrapper from _Wilson - set the working directory
        and log file stuff as a part of this...'''
        wilson = _Wilson()
        wilson.set_working_directory(self.get_working_directory())
        auto_logfiler(wilson)
        return wilson

    def _phase_compute_prepare(self):
        '''Prepare the phase computer for performing actual phasing.'''

        # if b factors unknown then guess them from an average from
        # running Wilson

        # see if we can get a consensus on the correct hand for the
        # input atoms - if we can then store whether we need to
        # switch to the enantiomorph or no

        # maybe reindex the input reflections to the enantiomorphic
        # spacegroup
    
        return

    # stuff to implement phase_compute - this should perform the phasing
    # with both hands until I can find a way of doing both at once, or
    # it should use the "correct" hand if this is "known" - this may involve
    # links to the enantiomorph stuff for spacegroups &c.

    def _phase_compute(self):
        '''Actually perform the phase calculation.'''

        # decide if we need to refine the sites or if straight phasing
        # will be ok

        return

    pass



