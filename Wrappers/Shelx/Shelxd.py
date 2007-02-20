#!/usr/bin/env python
# Shelxd.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
# 
# A wrapper for the substructure determination program shelxd - this will 
# provide a source of heavy atom information based on prepared reflection
# files from shelxc and a few interesting pieces of information. It will
# return some interesting facts about the substructure and the substructure
# itself, if it worked.
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

            # check the status

            # read the statistics from the file

            # read the sites and populate a substructure
            # object - these are in '%s_fa.pdb' % self._name

            return

    return ShelxdWrapper()

if __name__ == '__main__':
    # run the test - continued from Shelxc.py

    sd = Shelxd()
    sd.write_log_file('shelxd.log')
    sd.set_name('TS00')
    sd.find_sites()
