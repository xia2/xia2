#!/usr/bin/env python
# Sortmtz.py
# Maintained by G.Winter
# 5th June 2006
# 
# A wrapper for the CCP4 program sortmtz.
# 
# 
# Provides:
# 
# Reflection sorting functionality for going from Mosflm to Scala.
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
    '''A factory for SortmtzWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class SortmtzWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Sortmtz, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.setExecutable('sortmtz')

            self._sort_order = 'H K L M/ISYM BATCH'

        def sort(self):
            self.checkHklin()
            self.checkHklout()

            self.setTask('Sorting reflections %s -> %s' % \
                         (os.path.split(self.getHklin())[-1],
                          os.path.split(self.getHklout())[-1]))

            self.start()
            self.input(self._sort_order)

            self.close_wait()

            # general errors - SEGV and the like
            self.check_for_errors()

            # ccp4 specific errors
            self.check_ccp4_errors()

            return self.get_ccp4_status()

    return SortmtzWrapper()

if __name__ == '__main__':
    # run some tests

    import os

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    xia2core = os.environ['XIA2CORE_ROOT']

    hklin = os.path.join(xia2core,
                         'Data', 'Test', 'Mtz', '12287_1_E1.mtz')

    s = Sortmtz()
    s.setHklin(hklin)
    s.setHklout('null.mtz')

    try:
        print s.sort()
    except RuntimeError, e:
        print 'Error => %s' % e
    
    if not os.environ.has_key('DPA_ROOT'):
        raise RuntimeError, 'DPA_ROOT not defined'

    dpa = os.environ['DPA_ROOT']

    hklin = os.path.join(dpa, 'Wrappers', 'CCP4', 'not-mtz.txt')

    s = Sortmtz()
    s.setHklin(hklin)
    s.setHklout('null.mtz')

    try:
        print s.sort()
    except RuntimeError, e:
        print 'Error => %s' % e

    
    s = Sortmtz()
    s.setHklin('idontexist.mtz')
    s.setHklout('null.mtz')

    try:
        print s.sort()
    except RuntimeError, e:
        print 'Error => %s' % e

    
    
