#!/usr/bin/env python
# NullScalerImplementation.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 30/OCT/06
#
# An empty integrater - this presents the Scaler interface but does 
# nothing, making it ideal for when you have the reduced data already -
# this will simply return that reduced data...
#
# FIXME 04/DEC/06 this will need to be able to transmogrify data from one
#                 format to another (e.g. to scalepack from mtz, for instance)
#                 and also be able to get reflection file information from
#                 "trusted" formats (that is, from mtz format - cell, symmetry
#                 information will not be trusted in scalepack files.)

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.Mtzdump import Mtzdump
from Schema.Interfaces.Scaler import Scaler

class NullScalerImplementation(Scaler):
    '''A null scaler implementation which looks like a real scaler
    but actually does nothing but wrap a couple of reflection files.
    This will also transmogrify reflection files if appropriate.'''

    pass

