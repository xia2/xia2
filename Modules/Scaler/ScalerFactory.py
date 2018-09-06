#!/usr/bin/env python
# ScalerFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 21/SEP/06

from __future__ import absolute_import, division, print_function

# other odds and ends
from xia2.DriverExceptions.NotAvailableError import NotAvailableError
# selection stuff
from xia2.Handlers.PipelineSelection import get_preferences
from xia2.Handlers.Streams import Debug
# scaler implementations
from xia2.Modules.Scaler.CCP4ScalerA import CCP4ScalerA
from xia2.Modules.Scaler.XDSScalerA import XDSScalerA
from xia2.Modules.Scaler.DialsScaler import DialsScaler

def Scaler():
  '''Create a Scaler implementation.'''

  scaler = None
  preselection = get_preferences().get('scaler')

  if not scaler and \
    (not preselection or preselection == 'ccp4a'):
    try:
      scaler = CCP4ScalerA()
      Debug.write('Using CCP4A Scaler')
    except NotAvailableError:
      if preselection == 'ccp4a':
        raise RuntimeError('preselected scaler ccp4a not available')

  if not scaler and \
    (not preselection or preselection == 'xdsa'):
    try:
      scaler = XDSScalerA()
      Debug.write('Using XDSA Scaler')
    except NotAvailableError:
      if preselection == 'xdsa':
        raise RuntimeError('preselected scaler xdsa not available')

  if not scaler and \
    (not preselection or preselection == 'dials'):
    try:
      scaler = DialsScaler()
      Debug.write('Using DIALS Scaler')
    except NotAvailableError:
      if preselection == 'dials':
        raise RuntimeError('preselected scaler dials not available')

  return scaler
