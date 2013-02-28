#!/usr/bin/env python
# Scala.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 31st May 2006
# 
# An illustration wrapper for the program scala.
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Scala(DriverType = None):
    '''Create a Scala instance based on the requirements proposed in the
    DriverType argument.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class ScalaWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Scala, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('scala')

            self._scalepack = None

        def set_scalepack(self, scalepack):
            self._scalepack = scalepack

        def scale(self):
            self.check_hklin()
            self.check_hklout()

            self.set_task('Scale reflections from %s to %s' % \
                          (os.path.split(self.get_hklin())[-1],
                           os.path.split(self.get_hklout())[-1]))

            if self._scalepack:
                self.add_command_line('SCALEPACK')
                self.add_command_line(self._scalepack)

            self.start()

            if self._scalepack:
                self.input('output polish unmerged')

            self.input('resolution 1.65')
            self.input(
                'scales rotation spacing 5 secondary 6 bfactor on tails')
            self.input('cycles 20')
            self.input('anomalous on')
            self.input('sdcorrection full 1.0 15.0 0.02')
            self.input('sdcorrection partial 1.0 15.0 0.00')

            self.close_wait()

            return self.get_ccp4_status()


    return ScalaWrapper()

if __name__ == '__main__':

    # this must be run after the Sortmtz.py example

    hklin = '12287_1_E1_sorted.mtz'
    hklout = '12287_1_E1_scaled.mtz'

    s = Scala()

    s.set_hklin(hklin)
    s.set_hklout(hklout)

    print s.describe()

    status = s.scale()

    s.write_log_file('scala.log')
    
    results = s.parse_ccp4_loggraph()
    
    print '%s => %s' % (s.get_Task(), status)

    scalepack = '12287_1_E1_scaled.sca'
    hklout = '12287_1_E1_scaled.broken'
    
    s = Scala()

    s.set_scalepack(scalepack)
    s.set_hklin(hklin)
    s.set_hklout(hklout)

    status = s.scale()

    results = s.parse_ccp4_loggraph()
    
    print '%s => %s' % (s.get_task(), status)

    
