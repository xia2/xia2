#!/usr/bin/env python
# IntegraterFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A factory for Integrater implementations. At the moment this will
# support only Mosflm, XDS and the null integrater implementation.
#

import os
import sys
import copy

from xia2.Handlers.Streams import Debug
from xia2.Handlers.Flags import Flags
from xia2.Handlers.PipelineSelection import get_preferences, add_preference

from xia2.Modules.Integrater.MosflmIntegrater import MosflmIntegrater
from xia2.Modules.Integrater.XDSIntegrater import XDSIntegrater
from xia2.Modules.Integrater.DialsIntegrater import DialsIntegrater

from xia2.DriverExceptions.NotAvailableError import NotAvailableError

# FIXME 06/SEP/06 this should take an implementation of indexer to
#                 help with the decision about which integrater to
#                 use, and also to enable invisible configuration.
#
# FIXME 06/SEP/06 also need interface which will work with xsweep
#                 objects.

def IntegraterForXSweep(xsweep, json_file=None):
  '''Create an Integrater implementation to work with the provided
  XSweep.'''

  # FIXME this needs properly implementing...
  if xsweep is None:
    raise RuntimeError, 'XSweep instance needed'

  if not xsweep.__class__.__name__ == 'XSweep':
    raise RuntimeError, 'XSweep instance needed'

  integrater = Integrater()

  if json_file is not None:
    assert os.path.isfile(json_file)
    Debug.write("Loading integrater from json: %s" %json_file)
    import time
    t0 = time.time()
    integrater = integrater.__class__.from_json(filename=json_file)
    t1 = time.time()
    Debug.write("Loaded integrater in %.2f seconds" %(t1-t0))
  else:
    integrater.setup_from_imageset(xsweep.get_imageset())
  integrater.set_integrater_sweep_name(xsweep.get_name())

  # copy across resolution limits
  if xsweep.get_resolution_high():

    dmin = xsweep.get_resolution_high()
    dmax = xsweep.get_resolution_low()

    if (dmin and dmax and
        (dmin != integrater.get_integrater_high_resolution() or
         dmax != integrater.get_integrater_low_resolution())):

      Debug.write('Assinging resolution limits from XINFO input:')
      Debug.write('dmin: %.3f dmax: %.2f' % (dmin, dmax))
      integrater.set_integrater_resolution(dmin, dmax, user = True)

    elif dmin != integrater.get_integrater_high_resolution():

      Debug.write('Assinging resolution limits from XINFO input:')
      Debug.write('dmin: %.3f' % dmin)
      integrater.set_integrater_high_resolution(dmin, user = True)

  # check the epoch and perhaps pass this in for future reference
  # (in the scaling)
  if xsweep._epoch > 0:
    integrater.set_integrater_epoch(xsweep._epoch)

  # need to do the same for wavelength now as that could be wrong in
  # the image header...

  if xsweep.get_wavelength_value():
    Debug.write('Integrater factory: Setting wavelength: %.6f' % \
                xsweep.get_wavelength_value())
    integrater.set_wavelength(xsweep.get_wavelength_value())

  # likewise the distance...
  if xsweep.get_distance():
    Debug.write('Integrater factory: Setting distance: %.2f' % \
                xsweep.get_distance())
    integrater.set_distance(xsweep.get_distance())

  integrater.set_integrater_sweep(xsweep, reset=False)

  return integrater

def Integrater():
  '''Return an  Integrater implementation.'''

  # FIXME this should take an indexer as an argument...

  integrater = None
  preselection = get_preferences().get('integrater')

  if not integrater and \
         (not preselection or preselection == 'dials'):
    try:
      integrater = DialsIntegrater()
      Debug.write('Using Dials Integrater')
    except NotAvailableError, e:
      if preselection == 'dials':
        raise RuntimeError, \
              'preselected integrater dials not available: ' + \
              'dials not installed?'

  if not integrater and (not preselection or preselection == 'mosflmr'):
    try:
      integrater = MosflmIntegrater()
      Debug.write('Using MosflmR Integrater')
      if not get_preferences().get('scaler'):
        add_preference('scaler', 'ccp4a')
    except NotAvailableError, e:
      if preselection == 'mosflmr':
        raise RuntimeError, \
              'preselected integrater mosflmr not available'

  if not integrater and \
         (not preselection or preselection == 'xdsr'):
    try:
      integrater = XDSIntegrater()
      Debug.write('Using XDS Integrater in new resolution mode')
    except NotAvailableError, e:
      if preselection == 'xdsr':
        raise RuntimeError, \
              'preselected integrater xdsr not available: ' + \
              'xds not installed?'

  if not integrater:
    raise RuntimeError, 'no integrater implementations found'

  # check to see if resolution limits were passed in through the
  # command line...

  dmin = Flags.get_resolution_high()
  dmax = Flags.get_resolution_low()

  if dmin:
    Debug.write('Adding user-assigned resolution limits:')

    if dmax:

      Debug.write('dmin: %.3f dmax: %.2f' % (dmin, dmax))
      integrater.set_integrater_resolution(dmin, dmax, user = True)

    else:

      Debug.write('dmin: %.3f' % dmin)
      integrater.set_integrater_high_resolution(dmin, user = True)


  return integrater

if __name__ == '__main__':
  integrater = Integrater()
