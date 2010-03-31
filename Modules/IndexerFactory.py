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
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

# from LabelitIndexer import LabelitIndexer

from Wrappers.Labelit.LabelitIndex import LabelitIndex
from Wrappers.CCP4.Mosflm import Mosflm
from Modules.XDSIndexer import XDSIndexer
from Modules.XDSIndexerII import XDSIndexerII

from Exceptions.NotAvailableError import NotAvailableError
from Handlers.Streams import Debug
from Handlers.Flags import Flags
from Handlers.PipelineSelection import get_preferences

def IndexerForXSweep(xsweep):
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

    # FIXME need to code something in here to make a "good" decision
    # about the correct Indexer to return...

    detector = xsweep.get_header()['detector']

    indexer = Indexer(detector = detector)

    if crystal_lattice:
        # this is e.g. ('aP', (1.0, 2.0, 3.0, 90.0, 98.0, 88.0))
        indexer.set_indexer_input_lattice(crystal_lattice[0])
        indexer.set_indexer_input_cell(crystal_lattice[1])

    # configure the indexer
    indexer.setup_from_image(os.path.join(xsweep.get_directory(),
                                          xsweep.get_image()))

    # FIXME - it is assumed that all programs which implement the Indexer
    # interface will also implement FrameProcessor, which this uses.
    # verify this, or assert it in some way...

    # BIG FIXED - need to standardize on getBeam or get_beam - I prefer the
    # latter.
    if xsweep.get_beam():
        indexer.set_beam(xsweep.get_beam())

    if xsweep.get_reversephi() or Flags.get_reversephi():
        Debug.write('Setting reverse-phi')
        indexer.set_reversephi()

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

    if xsweep.get_wavelength_value():
        Debug.write('Indexer factory: Setting wavelength: %.6f' % \
                    xsweep.get_wavelength_value())
        indexer.set_wavelength(xsweep.get_wavelength_value())
    
    return indexer
    

# FIXME need to provide framework for input passing

def Indexer(detector = None):
    '''Create an instance of Indexer for use with a dataset.'''

    # FIXME need to check that these implement indexer

    indexer = None

    # return XDSIndexer()

    preselection = get_preferences().get('indexer')

    if not preselection:
        if Flags.get_small_molecule():
            preselection = 'mosflm'

    if not indexer and (not preselection or preselection == 'labelit'):
        try:
            if detector == 'dectris' and False:
                Debug.write('Labelit does not support dectris detectors')
                raise NotAvailableError, 'Labelit does not support dectris'
            indexer = LabelitIndex()
            Debug.write('Using LabelitIndex Indexer')
        except NotAvailableError, e:
            if preselection:
                raise RuntimeError, \
                      'preselected indexer labelit not available'            
            pass

    if not indexer and (not preselection or preselection == 'mosflm'):
        try:
            indexer = Mosflm()
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
            indexer = XDSIndexerII()
            Debug.write('Using XDS II Indexer')
        except NotAvailableError, e:
            if preselection:
                raise RuntimeError, 'preselected indexer xds not available'
            pass

    if not indexer:
        raise RuntimeError, 'no indexer implementations found'

    return indexer

if __name__ == '__main__':
    
    directory = os.path.join(os.environ['X2TD_ROOT'], 
                             'DL', 'insulin', 'images')
    
    i = Indexer()

    i.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))

    print 'Refined beam is: %6.2f %6.2f' % i.get_indexer_beam()
    print 'Distance:        %6.2f' % i.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % i.get_indexer_cell()
    print 'Lattice: %s' % i.get_indexer_lattice()
    print 'Mosaic: %6.2f' % i.get_indexer_mosaic()
    
