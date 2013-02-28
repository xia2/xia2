#!/usr/bin/env python
# Shelxd.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 1st June 2006
# 
# An illustration of using Driver directly to operate a program - in this case
# shelxd for locating heavy atom sites.
# 
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

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
            # self.close_wait()

            self.close()

            while True:
                line = self.output()

                if not line:
                    break

                print line[:-1]

            return

    return ShelxdWrapper()

if __name__ == '__main__':

    # then run the demo example

    s = Shelxd()

    s.set_name('demo')

    s.find_sites()

    
