#!/usr/bin/env python
# Resolve.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper for the density modification program RESOLVE (Tom Terwilliger)
#
# 11th June 207
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])


from Driver.DriverFactory import DriverFactory

def Resolve(DriverType = None):
    '''Create a Resolve instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ResolveWrapper(DriverInstance.__class__):
        '''A wrapper class for Resolve. This will take input from an
        MTZ file.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            # presume that this will use a "big" version of resolve...
            self.set_executable('resolve_huge')

            self._solvent = 0.0

            return

        def set_solvent(self, solvent):
            self._solvent = solvent
            return

        def run(self):
            
            self.start()
            self.input('solvent_content %f' % self._solvent)
            self.close_wait()

            # read the output here...

            return

    return ResolveWrapper()
