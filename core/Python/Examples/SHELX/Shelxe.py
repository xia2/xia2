#!/usr/bin/env python
# Shelxe.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 1st June 2006
# 
# An illustration of using Driver directly to operate a program - in this case
# shelxe for phasing experimental data.
# 
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory

def Shelxe(DriverType = None):
    '''Create a Shelxe instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShelxeWrapper(DriverInstance.__class__):
        '''A wrapper class for Shelxe.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('shelxe')

            self._name = None

            self._solvent = 0.0

        def set_solvent(self, solvent):
            self._solvent = solvent
            return

        def set_name(self, name):
            self._name = name
            return

        def phase(self):
            '''Actually compute the phases from the heavy atom locations.'''

            self.add_command_line('%s' % self._name)
            self.add_command_line('%s_fa' % self._name)
            self.add_command_line('-h')
            self.add_command_line('-s%f' % self._solvent)
            self.add_command_line('-m20')

            self.start()

            self.close()

            while True:

                line = self.output()

                if not line:
                    break

                print line[:-1]

    return ShelxeWrapper()

if __name__ == '__main__':

    # run the demo

    s = Shelxe()

    s.set_name('demo')
    s.set_solvent(0.46)

    s.phase()

    
                
