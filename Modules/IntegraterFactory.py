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

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))
sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Wrappers.CCP4 import Mosflm
from Handlers.Streams import Admin
from Handlers.PipelineSelection import get_preferences, add_preference

from Modules.XDSIntegrater import XDSIntegrater

from NullIntegraterImplementation import NullIntegrater

from Exceptions.NotAvailableError import NotAvailableError

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
        integrater.set_integrater_sweep_name(xsweep.get_name())

    # check the epoch and perhaps pass this in for future reference
    # (in the scaling)
    if xsweep._epoch > 0:
        integrater.set_integrater_epoch(xsweep._epoch)

    # need to do the same for wavelength now as that could be wrong in
    # the image header...

    if xsweep.get_wavelength_value():
        integrater.set_wavelength(xsweep.get_wavelength_value())

    integrater.set_integrater_sweep(xsweep)

    return integrater

def Integrater():
    '''Return an  Integrater implementation.'''

    # FIXME this should take an indexer as an argument...

    integrater = None
    preselection = get_preferences().get('integrater')

    if not integrater and \
           (not preselection or preselection == 'xds'):
        try:
            integrater = XDSIntegrater()
            Admin.write('Using XDS Integrater')
            add_preference('scaler', 'xds')
        except NotAvailableError, e:
            if preselection == 'xds':
                raise RuntimeError, \
                      'preselected integrater xds not available'
            pass
            
    if not integrater and (not preselection or preselection == 'mosflm'):
        try:
            integrater = Mosflm.Mosflm()
            Admin.write('Using Mosflm Integrater')
            add_preference('scaler', 'ccp4')
        except NotAvailableError, e:
            if preselection == 'mosflm':
                raise RuntimeError, \
                      'preselected integrater xds not available'
            pass
            
    if not integrater:
        raise RuntimeError, 'no integrater implementations found'

    return integrater

if __name__ == '__main__':
    integrater = Integrater()

