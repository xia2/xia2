#!/usr/bin/env python
# Xtriage.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A wrapper for the phenix program phenix.xtriage. This is to inspect 
# reduced data and look for e.g. twinning.
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Xtriage(DriverType = None):
    '''A factory for an xtriage wrapper class.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class XtriageWrapper(DriverInstance.__class__):
        def __init__(self):

            DriverInstance.__class__.__init__(self)            
            self.set_executable('phenix.xtriage')

            self._hklin = None

        def set_hklin(self, hklin):
            self._hklin = hklin
            return

        def analyse(self):

            if not self._hklin:
                raise RuntimeError, 'hklin not defined'

            self.add_command_line(self._hklin)

            # in here need to be able to select the right
            # reflection sets...

            self.start()

            self.close_wait()

            self.check_for_errors()

            # read the output

            return

    return XtriageWrapper()

