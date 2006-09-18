#!/usr/bin/env python
# IndexerFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 13th June 2006
# 
# A factory for Indexer class instances. This will return an indexer
# suitable for using in the context defined in the input.
# 
# 04/SEP/06 FIXME this needs to handle Mosflm, LabelitScreen as
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
# LabelitScreen/Indexer
# 
# And will make a decision based on the screen information if available.
# Integral unit test was also out of date, because the interface has changed.

import os
import sys
import copy

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['DPA_ROOT']))

# from LabelitIndexer import LabelitIndexer

from Wrappers.Labelit import LabelitScreen
from Wrappers.CCP4 import Mosflm

from Handlers.Streams import Admin

def IndexerForXSweep(xsweep):
    '''Provide an indexer to work with XSweep instance xsweep.'''

    # check what is going on

    if xsweep == None:
        raise RuntimeError, 'XSweep instance needed'

    if not xsweep.__class__.__name__ == 'XSweep':
        raise RuntimeError, 'XSweep instance needed'

    # if the xsweep has a crystal lattice defined, use mosflm which
    # FIXME needs to be modified to take a crystal cell as input.

    crystal_lattice = xsweep.get_crystal_lattice()

    if crystal_lattice:
        pass

    # FIXME need to code something in here to make a "good" decision
    # about the correct Indexer to return...

    indexer = Indexer()

    # configure the indexer
    indexer.setup_from_image(os.path.join(xsweep.get_directory(),
                                          xsweep.get_image()))

    # FIXME - it is assumed that all programs which implement the Indexer
    # interface will also implement FrameProcessor, which this uses.
    # verify this, or assert it in some way...

    # BIG FIXME - need to standardize on getBeam or get_beam - I prefer the
    # latter.
    if xsweep.get_beam():
        indexer.setBeam(xsweep.get_beam())

    # FIXME more - need to check if we should be indexing in a specific
    # lattice - check xsweep.get_crystal_lattice()
    
    return indexer
    

# FIXME need to provide framework for input passing

def Indexer():
    '''Create an instance of Indexer for use with a dataset.'''

    # FIXME need to check that these implement indexer

    indexer = None

    if not indexer:
        try:
            indexer = LabelitScreen.LabelitScreen()
            Admin.write('Using LabelitScreen Indexer')
        except RuntimeError, e:
            Admin.write('Indexer LabelitScreen not available: %s' % str(e))

    if not indexer:
        try:
            indexer = Mosflm.Mosflm()
            Admin.write('Using Mosflm Indexer')
        except RuntimeError, e:
            Admin.write('Indexer Mosflm not available: %s' % str(e))

    if not indexer:
        raise RuntimeError, 'no indexer implementations found'

    # configure indexer implementation here, e.g. pass in the
    # xsweep definition if available

    return indexer

if __name__ == '__main__':
    
    directory = os.path.join(os.environ['DPA_ROOT'],
                             'Data', 'Test', 'Images')

    i = Indexer()

    i.setBeam((108.9, 105.0))
    i.setup_from_image(os.path.join(directory, '12287_1_E1_001.img'))

    print 'Refined beam is: %6.2f %6.2f' % i.get_indexer_beam()
    print 'Distance:        %6.2f' % i.get_indexer_distance()
    print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % i.get_indexer_cell()
    print 'Lattice: %s' % i.get_indexer_lattice()
    print 'Mosaic: %6.2f' % i.get_indexer_mosaic()
    
