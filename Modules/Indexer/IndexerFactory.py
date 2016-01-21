#!/usr/bin/env python
# IndexerFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 13th June 2006
#
# A factory for Indexer class instances. This will return an indexer
# suitable for using in the context defined in the input.
#
# 04/SEP/06 FIXME this needs to handle Mosflm, LabelitIndex as
#           implementations of indexer, since the constructors will
#           now raise an exception if the program is not available
#           can encode the expertise on which to provide in here.
#           This module should also check that the class in question
#           at some stage inherits from Schema/Interfaces/Indexer.py
#           since that is the core definition.
#
# This supports the following Indexer implementations:
#
# Mosflm/Indexer
# LabelitIndex/Indexer
# XDS/Indexer
#
# And will make a decision based on the screen information if available.
# Integral unit test was also out of date, because the interface has changed.

import os
import sys
import copy

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from Modules.Indexer.MosflmIndexer import MosflmIndexer
from Modules.Indexer.LabelitIndexer import LabelitIndexer
from Modules.Indexer.LabelitIndexerII import LabelitIndexerII
from Modules.Indexer.XDSIndexer import XDSIndexer
from Modules.Indexer.XDSIndexerII import XDSIndexerII
from Modules.Indexer.XDSIndexerInteractive import XDSIndexerInteractive
from Modules.Indexer.XDSIndexerSum import XDSIndexerSum
from Modules.Indexer.DialsIndexer import DialsIndexer

from DriverExceptions.NotAvailableError import NotAvailableError
from Handlers.Streams import Debug
from Handlers.Flags import Flags
from Handlers.PipelineSelection import get_preferences

def IndexerForXSweep(xsweep, json_file=None):
  '''Provide an indexer to work with XSweep instance xsweep.'''

  # check what is going on

  if xsweep == None:
    raise RuntimeError, 'XSweep instance needed'

  if not xsweep.__class__.__name__ == 'XSweep':
    raise RuntimeError, 'XSweep instance needed'

  # if the xsweep has a crystal lattice defined, use mosflm which
  # FIXME needs to be modified to take a crystal cell as input.
  # Ignore this - both mosflm and labelit can take this as
  # input and it is implemented for both via the Indexer interface.

  crystal_lattice = xsweep.get_crystal_lattice()

  from Handlers.Phil import PhilIndex
  params = PhilIndex.params
  multi_sweep_indexing = params.xia2.settings.developmental.multi_sweep_indexing

  # FIXME SCI-599 decide from the width of the sweep and the preference
  # which indexer to return...

  sweep_images = xsweep.get_image_range()
  imageset = xsweep.get_imageset()
  scan = imageset.get_scan()
  oscillation = scan.get_oscillation()
  sweep_width = (oscillation[1] * (sweep_images[1] - sweep_images[0] + 1))

  # hack now - if XDS integration switch to XDS indexer if (i) labelit and
  # (ii) sweep < 10 degrees
  if multi_sweep_indexing and len(xsweep.get_xsample().get_sweeps()) > 1:
    xsample = xsweep.get_xsample()
    indexer = xsample.get_multi_indexer()

    if indexer is None:
      indexer = Indexer()
      xsample.set_multi_indexer(indexer)

  elif sweep_width < 10.0 and not get_preferences().get('indexer') and \
      'xds' in get_preferences().get('integrater'):
    Debug.write('Overriding indexer as XDSII')
    indexer = Indexer(preselection = 'xdsii')
  else:
    indexer = Indexer()

  if json_file is not None:
    assert os.path.isfile(json_file)
    Debug.write("Loading indexer from json: %s" %json_file)
    import time
    t0 = time.time()
    indexer = indexer.__class__.from_json(filename=json_file)
    t1 = time.time()
    Debug.write("Loaded indexer in %.2f seconds" %(t1-t0))
  else:
    # configure the indexer
    indexer.add_indexer_imageset(xsweep.get_imageset())

  if crystal_lattice:
    # this is e.g. ('aP', (1.0, 2.0, 3.0, 90.0, 98.0, 88.0))
    indexer.set_indexer_input_lattice(crystal_lattice[0])
    indexer.set_indexer_input_cell(crystal_lattice[1])

  # FIXME - it is assumed that all programs which implement the Indexer
  # interface will also implement FrameProcessor, which this uses.
  # verify this, or assert it in some way...

  if xsweep.get_beam_centre():
    indexer.set_beam_centre(xsweep.get_beam_centre())

  # N.B. This does not need to be done for the integrater, since
  # that gets it's numbers from the indexer it uses.

  if xsweep.get_distance():
    Debug.write('Indexer factory: Setting distance: %.2f' % \
                xsweep.get_distance())
    indexer.set_distance(xsweep.get_distance())

  # FIXME more - need to check if we should be indexing in a specific
  # lattice - check xsweep.get_crystal_lattice()

  # need to do the same for wavelength now as that could be wrong in
  # the image header...

  #if xsweep.get_wavelength_value():
    #Debug.write('Indexer factory: Setting wavelength: %.6f' % \
                #xsweep.get_wavelength_value())
    #indexer.set_wavelength(xsweep.get_wavelength_value())

  indexer.set_indexer_sweep(xsweep)

  if xsweep.get_xsample().get_multi_indexer() is not None:
    xsample = xsweep.get_xsample()
    multi_indexer = xsample.get_multi_indexer()
    assert multi_indexer is indexer

    if len(indexer._indxr_imagesets) == 1:

      for xsweep_other in xsample.get_sweeps()[1:]:
        xsweep_other._get_indexer()

  return indexer


# FIXME need to provide framework for input passing

def Indexer(preselection = None):
  '''Create an instance of Indexer for use with a dataset.'''

  # FIXME need to check that these implement indexer

  indexer = None

  if not preselection:
    preselection = get_preferences().get('indexer')

  # FIXME perhaps find a less baroque way of coding this up

  if not indexer and (not preselection or preselection == 'dials'):
    try:
      indexer = DialsIndexer()
      Debug.write('Using DialsIndexer')
    except NotAvailableError, e:
      if preselection:
        raise RuntimeError, \
              'preselected indexer dials not available'
      pass

  if not indexer and (not preselection or preselection == 'labelit'):
    try:
      indexer = LabelitIndexer()
      Debug.write('Using Labelit Indexer')
    except NotAvailableError, e:
      if preselection:
        raise RuntimeError, \
              'preselected indexer labelit not available'
      elif 'xds' in get_preferences().get('integrater'):
        preselection = 'xds'

  if not indexer and (not preselection or preselection == 'mosflm'):
    try:
      indexer = MosflmIndexer()
      Debug.write('Using Mosflm Indexer')
    except NotAvailableError, e:
      if preselection:
        raise RuntimeError, 'preselected indexer mosflm not available'
      pass

  if not indexer and (not preselection or preselection == 'xds'):
    try:
      indexer = XDSIndexer()
      Debug.write('Using XDS Indexer')
    except NotAvailableError, e:
      if preselection:
        raise RuntimeError, 'preselected indexer xds not available'
      pass

  if not indexer and (not preselection or preselection == 'xdsii'):
    try:
      if Flags.get_interactive():
        indexer = XDSIndexerInteractive()
        Debug.write('Using XDS Interactive Indexer')
      else:
        indexer = XDSIndexerII()
        Debug.write('Using XDS II Indexer')
    except NotAvailableError, e:
      if preselection:
        raise RuntimeError, 'preselected indexer xds not available'
      pass

  if not indexer and (not preselection or preselection == 'xdssum'):
    try:
      indexer = XDSIndexerSum()
      Debug.write('Using XDS Indexer on summed images')
    except NotAvailableError, e:
      if preselection:
        raise RuntimeError, 'preselected indexer xds not available'
      pass

  if not indexer and (not preselection or preselection == 'labelitii'):
    try:
      indexer = LabelitIndexerII()
      Debug.write('Using LabelitIndexerII')
    except NotAvailableError, e:
      if preselection:
        raise RuntimeError, \
              'preselected indexer labelit not available'
      pass

  if not indexer:
    raise RuntimeError, 'no indexer implementations found'

  return indexer

if __name__ == '__main__':

  directory = os.path.join(os.environ['X2TD_ROOT'],
                           'DL', 'insulin', 'images')

  i = Indexer()

  i.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))

  print 'Refined beam is: %6.2f %6.2f' % i.get_indexer_beam_centre()
  print 'Distance:        %6.2f' % i.get_indexer_distance()
  print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % i.get_indexer_cell()
  print 'Lattice: %s' % i.get_indexer_lattice()
  print 'Mosaic: %6.2f' % i.get_indexer_mosaic()
