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

class BP3PhaseComputer(PhaseComputer):

    # constructor

    # need working directory stuff

    # factory

    # stuff to implement phase_compute_prepare
    # this should include estimating Wilson B factors if not already
    # assigned - perhaps taking an average for all wavelengths provided

    # stuff to implement phase_compute - this should perform the phasing
    # with both hands until I can find a way of doing both at once

    pass



