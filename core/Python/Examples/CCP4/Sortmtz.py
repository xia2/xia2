#!/usr/bin/env python
# Sortmtz.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 31st May 2006
# 
# An illustration of how to use a Driver/Decorator to run a program - 
# in this case sortmtz. Note well that this is an example!
# 
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Sortmtz(DriverType = None):
    '''Create a sortmtz instance based on the passed in (string) DriverType.
    If this is None (not specified) then just use whatever the DriverFactory
    produces.'''

    # Instantiate the appropriate kind of Driver to use in here
    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class SortmtzWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Sortmtz, using the CCP4Driver.'''

        def __init__(self):
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable('sortmtz')

        def sort(self):

            self.check_hklin()
            self.check_hklout()

            self.set_task('Sort reflections from %s to %s' % \
                          (os.path.split(self.get_hklin())[-1],
                           os.path.split(self.get_hklout())[-1]))

            self.start()

            self.input('H K L M/ISYM BATCH')

            self.close_wait()

            return self.get_ccp4_status()
                                       
    return SortmtzWrapper()

if __name__ == '__main__':
    # then run a quick test

    import os

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    xia2core = os.environ['XIA2CORE_ROOT']

    hklin = os.path.join(xia2core,
                         'Data', 'Test', 'Mtz', '12287_1_E1.mtz')

    hklout = '12287_1_E1_sorted.mtz'

    s = Sortmtz()

    s.set_hklin(hklin)
    s.set_hklout(hklout)

    status = s.sort()

    s.write_log_file('sortmtz.log')

    print '%s => %s' % (s.getTask(), status)
    

        
