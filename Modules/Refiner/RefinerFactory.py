#!/usr/bin/env python
# RefinerFactory.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

import os
import sys
import copy

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

# scaler implementations
from Modules.Refiner.DialsRefiner import DialsRefiner

# selection stuff
from Handlers.PipelineSelection import get_preferences

# other odds and ends
from DriverExceptions.NotAvailableError import NotAvailableError
from Handlers.Streams import Debug

def Refiner():
  '''Create a Refiner implementation.'''

  refiner = None
  #preselection = get_preferences().get('refiner')
  preselection = 'dials'

  if not refiner and \
    (not preselection or preselection == 'dials'):
    try:
      scaler = DialsRefiner()
      Debug.write('Using Dials Refiner')
    except NotAvailableError, e:
      if preselection == 'dials':
        raise RuntimeError, 'preselected refiner dials not available'
      pass

  return scaler
