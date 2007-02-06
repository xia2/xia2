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


