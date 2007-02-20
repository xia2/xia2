#!/usr/bin/env python
# FileName.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Shelxd(DriverType = None):
    '''Create a Shelxd instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShelxdWrapper(DriverInstance.__class__):
        '''A wrapper class for Shelxd.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('shelxd')

            self._name = None

        def set_name(self, name):
            self._name = name

            return

        def find_sites(self):
            '''Find the HA sites.'''

            self.add_command_line('%s_fa' % self._name)

            self.start()
            self.close_wait()

            output = self.get_all_output()

            return

    return ShelxdWrapper()
