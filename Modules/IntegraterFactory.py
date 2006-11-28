#!/usr/bin/env python
# IntegraterFactory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
# 
# A factory for Integrater implementations. At the moment this will 
# support only Mosflm.
# 

import os
import sys
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.CCP4 import Mosflm
from Handlers.Streams import Admin

from NullIntegraterImplementation import NullIntegrater

# FIXME 06/SEP/06 this should take an implementation of indexer to 
#                 help with the decision about which integrater to
#                 use, and also to enable invisible configuration.
# 
# FIXME 06/SEP/06 also need interface which will work with xsweep
#                 objects.

def IntegraterForXSweep(xsweep):
    '''Create an Integrater implementation to work with the provided
    XSweep.'''

    # FIXME this needs properly implementing...
    if xsweep == None:
        raise RuntimeError, 'XSweep instance needed'

    if not xsweep.__class__.__name__ == 'XSweep':
        raise RuntimeError, 'XSweep instance needed'

    # if we're working from preprocessed data, return a null
    # Integrater pointing at that
    
    if xsweep._integrated_reflection_file:
        integrater = NullIntegrater(xsweep._integrated_reflection_file)

    else:
        # return a real integrater
        integrater = Integrater()
        integrater.setup_from_image(os.path.join(xsweep.get_directory(),
                                                 xsweep.get_image()))

    # check the epoch and perhaps pass this in for future reference
    # (in the scaling)
    if xsweep._epoch > 0:
        integrater.set_integrater_epoch(xsweep._epoch)

    return integrater

def Integrater():
    '''Return an  Integrater implementation.'''

    # FIXME this should take an indexer as an argument...

    integrater = None

    if not integrater:
        try:
            integrater = Mosflm.Mosflm()
            Admin.write('Using Mosflm Integrater')
        except RuntimeError, e:
            Admin.write('Integrater Mosflm not available: %s' % str(e))
            
    if not integrater:
        raise RuntimeError, 'no integrater implementations found'

    return integrater

if __name__ == '__main__':
    integrater = Integrater()

