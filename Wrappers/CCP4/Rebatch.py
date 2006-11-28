#!/usr/bin/env python
# Rebatch.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 21/SEP/06
# 
# A wrapper for the CCP4 program REBATCH.
# 
# 
import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Rebatch(DriverType = None):
    '''A factory for RebatchWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class RebatchWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Rebatch, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('rebatch')

            self._first_batch = 0
            self._add_batch = 0

            self._pname = None
            self._xname = None
            self._dname = None

            return

        def set_project_information(self, pname, xname, dname):
            self._pname = pname
            self._xname = xname
            self._dname = dname
            return

        def set_first_batch(self, first_batch):
            self._first_batch = first_batch
            return

        def set_add_batch(self, add_batch):
            self._add_batch = add_batch
            return

        def rebatch(self):
            self.check_hklin()
            self.check_hklout()

            if self._first_batch > 0 and self._add_batch > 0:
                raise RuntimeError, 'both first and add specified'

            if self._first_batch == 0 and self._add_batch == 0:
                raise RuntimeError, 'neither first nor add specified'

            self.start()

            if self._first_batch > 0:
                command = 'batch all start %d' % self._first_batch
            else:
                command = 'batch all add %d' % self._add_batch

            if self._pname and self._xname and self._dname:
                command += ' pname %s xname %s dname %s' % (pname,
                                                            xname,
                                                            dname)

            self.input(command)

            self.close_wait()

            # check for errors...
            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

                raise e

            # get out the new batch range...

            output = self.get_all_output()

            min = 10000000
            max = -10000000
            
            for i in range(len(output)):
                o = output[i]
                if o.split()[:5] == ['Old', 'batch', 'New', 'batch', 'Max']:
                    j = i + 2
                    m = output[j]
                    while not 'SUMMARY_END' in m:
                        l = m.split()
                        if len(l) == 3:
                            batch = int(l[1])
                            if batch < min:
                                min = batch
                            if batch > max:
                                max = batch
                        j += 1
                        m = output[j]
            
            new_batches = (min, max)

            return new_batches

    return RebatchWrapper()

if __name__ == '__main__':
    # add a test here

    hklin = os.path.join(os.environ['XIA2_ROOT'],
                         'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')
    hklout = 'temp.mtz'

    rb = Rebatch()

    rb.set_hklin(hklin)
    rb.set_hklout(hklout)
    rb.set_first_batch(100)

    new = rb.rebatch()

    print new
