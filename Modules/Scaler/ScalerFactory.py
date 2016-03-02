#!/usr/bin/env python
# ScalerFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 21/SEP/06

import os
import sys
import copy

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

# scaler implementations
from CCP4ScalerA import CCP4ScalerA
from XDSScalerA import XDSScalerA

# selection stuff
from Handlers.PipelineSelection import get_preferences

# other odds and ends
from xia2.DriverExceptions.NotAvailableError import NotAvailableError
from Handlers.Streams import Debug

def Scaler():
  '''Create a Scaler implementation.'''

  scaler = None
  preselection = get_preferences().get('scaler')

  if not scaler and \
    (not preselection or preselection == 'ccp4a'):
    try:
      scaler = CCP4ScalerA()
      Debug.write('Using CCP4A Scaler')
    except NotAvailableError, e:
      if preselection == 'ccp4a':
        raise RuntimeError, 'preselected scaler ccp4a not available'
      pass

  if not scaler and \
    (not preselection or preselection == 'xdsa'):
    try:
      scaler = XDSScalerA()
      Debug.write('Using XDSA Scaler')
    except NotAvailableError, e:
      if preselection == 'xdsa':
        raise RuntimeError, 'preselected scaler xdsa not available'
    pass

  return scaler
