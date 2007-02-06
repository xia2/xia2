#!/usr/bin/env python
# PhaseImprover.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
#
# An interface to represent improvers of phases, for example through 
# density modification, which may be implemented by e.g. dm, pirate,
# solomon, resolve. This will take as input a solvent fraction (probably)
# and some initially phased reflections in a reflection file, most
# likely MTZ in the first instance. Actually this should take a phase
# computer as input...

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])


