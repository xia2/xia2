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
from Modules.Refiner.MosflmRefiner import MosflmRefiner
from Modules.Refiner.XDSRefiner import XDSRefiner

# selection stuff
from Handlers.PipelineSelection import get_preferences

# other odds and ends
from DriverExceptions.NotAvailableError import NotAvailableError
from Handlers.Streams import Debug



def RefinerForXSweep(xsweep, json_file=None):
  '''Create a Refiner implementation to work with the provided
  XSweep.'''

  # FIXME this needs properly implementing...
  if xsweep == None:
    raise RuntimeError, 'XSweep instance needed'

  if not xsweep.__class__.__name__ == 'XSweep':
    raise RuntimeError, 'XSweep instance needed'

  refiner = Refiner()

  if json_file is not None:
    assert os.path.isfile(json_file)
    Debug.write("Loading refiner from json: %s" %json_file)
    refiner = refiner.__class__.from_json(filename=json_file)

  refiner.add_refiner_sweep(xsweep)

  return refiner


def Refiner():
  '''Create a Refiner implementation.'''

  refiner = None
  preselection = get_preferences().get('refiner')

  if not refiner and \
    (not preselection or preselection == 'dials'):
    try:
      refiner = DialsRefiner()
      Debug.write('Using Dials Refiner')
    except NotAvailableError, e:
      if preselection == 'dials':
        raise RuntimeError, 'preselected refiner dials not available'
      pass

  if not refiner and \
     (not preselection or preselection == 'mosflm'):
    try:
      refiner = MosflmRefiner()
      Debug.write('Using Mosflm Refiner')
    except NotAvailableError, e:
      if preselection == 'mosflm':
        raise RuntimeError, 'preselected refiner mosflm not available'
      pass

  if not refiner and \
     (not preselection or preselection == 'xds'):
    try:
      refiner = XDSRefiner()
      Debug.write('Using XDS Refiner')
    except NotAvailableError, e:
      if preselection == 'xds':
        raise RuntimeError, 'preselected refiner xds not available'
      pass

  return refiner
