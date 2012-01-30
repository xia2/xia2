#!/usr/bin/env python
# Wilson.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 5th June 2006
#
# An example of an wilson CCP4 program wrapper, which can be used as the
# base for other wrappers.
#
# Provides:
#
# A program which will generate an estimate of the B factor for a data set.
# This data set needs to be udentified in the input. I will presume that the
# columns to use are called F_${DATASET} and SIGF_${DATASET} in the same
# way that the rest of xia2 works..

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Wilson(DriverType = None):
    '''A factory for WilsonWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class WilsonWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Wilson, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'wilson'))

            # input
            self._dataset = None
            self._nres = 0

            # results
            self._b_factor = None

            return

        def set_dataset(self, dataset):
            '''Set the dataset to compute a B-factor from.'''

            self._dataset = dataset
            return

        def set_nres(self, nres):
            '''Set the nres to compute a B-factor from.'''

            self._nres = nres
            return

        def compute_b(self):
            '''Run wilson to estimate the B factor.'''

            if not self._dataset:
                raise RuntimeError, 'dataset not assigned'
            if not self._nres:
                raise RuntimeError, 'nres not assigned'

            self.check_hklin()

            self.start()
            self.input('nres %d' % self._nres)
            self.input('labin FP=F_%s SIGFP=SIGF_%s' % (self._dataset,
                                                        self._dataset))
            self.close_wait()

            self.check_for_errors()
            self.check_ccp4_errors()

            # next go through the output and check for the
            # b factor in the output

            output = self.get_all_output()

            for o in output:
                if 'Least squares straight line gives' in o:
                    self._b_factor = float(o.split()[7])

            return

        def get_b_factor(self):
            return self._b_factor

    return WilsonWrapper()

if __name__ == '__main__':
    # then run a test

    w = Wilson()

    w.set_hklin(os.path.join(os.environ['XIA2_ROOT'],
                             'Data', 'Test', 'Mtz', 'reduced.mtz'))
    w.set_nres(180)
    w.set_dataset('INFL')

    w.compute_b()

    print w.get_b_factor()
