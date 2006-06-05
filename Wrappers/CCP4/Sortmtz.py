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

            self._hklin_files = []

            return

        def addHklin(self, hklin):
            '''Add a reflection file to the list to be sorted together.'''
            self._hklin_files.append(hklin)
            return

        def check_sortmtz_errors(self):
            '''Check the output for "standard" errors.'''

            lwbat_warning = ''

            for l in self.get_all_output():

                if 'From ccp4_lwbat: warning:' in l:
                    lwbat_warning = l.split('warning:')[1].strip()
                
                if 'error in ccp4_lwbat' in l:
                    raise RuntimeError, lwbat_warning


        def sort(self):
            '''Actually sort the reflections.'''
            
            # if we have not specified > 1 hklin file via the add method,
            # check that the setHklin method has been used.
            if not self._hklin_files:
                self.checkHklin()
            
            self.checkHklout()

            if self._hklin_files:
                task = ''
                for hklin in self._hklin_files:
                    task += ' %s' % hklin
                self.setTask('Sorting reflections%s => %s' % \
                             (task,
                              os.path.split(self.getHklout())[-1]))
            else:
                self.setTask('Sorting reflections %s => %s' % \
                             (os.path.split(self.getHklin())[-1],
                              os.path.split(self.getHklout())[-1]))
                
            self.start()
            self.input(self._sort_order)

            # multiple mtz files get passed in on the command line...

            if self._hklin_files:
                for m in self._hklin_files:
                    self.input(m)

            self.close_wait()

            # general errors - SEGV and the like
            self.check_for_errors()

            # ccp4 specific errors
            self.check_ccp4_errors()

            # sortmtz specific errors
            self.check_sortmtz_errors()

            return self.get_ccp4_status()

    return SortmtzWrapper()

if __name__ == '__main__':
    # run some tests

    import os

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    dpa = os.environ['DPA_ROOT']

    hklin1 = os.path.join(dpa,
                          'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')
    hklin2 = os.path.join(dpa,
                          'Data', 'Test', 'Mtz', '12287_1_E1_11_20.mtz')

    s = Sortmtz()
    s.addHklin(hklin1)
    s.addHklin(hklin2)
    s.setHklout('null.mtz')

    try:
        print s.sort()
    except RuntimeError, e:
        print 'Error => %s' % e

    s = Sortmtz()
    s.addHklin(hklin1)
    s.addHklin(hklin1)
    s.setHklout('null.mtz')

    try:
        print s.sort()
    except RuntimeError, e:
        print 'Error => %s' % e

    
