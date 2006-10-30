#!/usr/bin/env python
# NullIntegraterImplementation.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 30/OCT/06
#
# An empty integrater - this presents the Integrater interface but does 
# nothing, making it ideal for when you have the integrated intensities
# passed in already. This will simply return the intensities.
# 

import os
import sys

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

from Schema.Interfaces.Integrater import Integrater

class NullIntegrater(Integrater):
    '''A null class to present the integrater interface.'''

    def __init__(self, integrated_reflection_file):
        '''Create a null integrater pointing at this reflection file.'''

        Integrater.__init__(self)
        self._intgr_hklout = integrated_reflection_file

        # also need to be able to set the epoch of myself
        # FIXME - this is also generally true... need to add
        # this to the .xinfo file...

        # set up little things like the number of batches in this
        # "wedge"...

        return

    # things that this interface needs to present...

    # bodges - from Driver &c.

    def set_working_directory(self, directory):
        pass

    # "real" methods

    def _integrate_prepare(self):
        '''Do nothing!'''
        pass

    def _integrate(self):
        '''Do nothing - except return a pointer to the reflections...'''

        return self._intgr_hklout


    
