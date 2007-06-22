#!/usr/bin/env python
# Truncate.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 26th October 2006
# 
# A wrapper for the CCP4 program Truncate, which calculates F's from
# I's and gives a few useful statistics about the data set.
#
# FIXME 26/OCT/06 this needs to be able to take into account the solvent
#                 content of the crystal (at the moment it will be assumed
#                 to be 50%.)
# 
# FIXME 16/NOV/06 need to be able to get the estimates B factor from the
#                 Wilson plot and also second moment stuff, perhaps?

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory
from lib.Guff import transpose_loggraph
from Handlers.Streams import Chatter

def Truncate(DriverType = None):
    '''A factory for TruncateWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class TruncateWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Truncate, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self._anomalous = False
            self._nres = 0

            self.set_executable('truncate')

            self._b_factor = 0.0
            self._moments = None

            self._wilson_fit_grad = 0.0
            self._wilson_fit_grad_sd = 0.0
            self._wilson_fit_m = 0.0
            self._wilson_fit_m_sd = 0.0
            self._wilson_fit_range = None
            
            return

        def set_anomalous(self, anomalous):
            self._anomalous = anomalous
            return

        def truncate(self):
            '''Actually perform the truncation procedure.'''
            
            self.check_hklin()
            self.check_hklout()

            self.start()

            # write the harvest files in the local directory, not
            # in $HARVESTHOME. Though we have set this for the project
            # so we should be fine to just plough ahead...
            # self.input('usecwd')

            if self._anomalous:
                self.input('anomalous yes')
            else:
                self.input('anomalous no')

            if self._nres:
                self.input('nres %d' % self._nres)

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

            # FIXME need to parse the output for interesting things here!

            for line in self.get_all_output():
                if 'Least squares straight line gives' in line:
                    list = line.replace('=', ' ').split()
                    if not '***' in list[6]:
                        self._b_factor = float(list[6])
                    else:
                        Debug.write('no B factor available')

                if 'LSQ Line Gradient' in line:
                    self._wilson_fit_grad = float(line.split()[-1])
                    resol_width = max(self._wilson_fit_range) - \
                                  min(self._wilson_fit_range)
                    if self._wilson_fit_grad > 0 and resol_width > 1.0:
                        raise RuntimeError, \
                              'wilson plot gradient positive: %.2f' % \
                              self._wilson_fit_grad
                    elif self._wilson_fit_grad > 0:
                        Debug.write(
                            'Positive gradient but not much wilson plot')
                        
                        
                if 'Uncertainty in Gradient' in line:
                    self._wilson_fit_grad_sd = float(line.split()[-1])
                if 'X Intercept' in line:
                    self._wilson_fit_m = float(line.split()[-1])
                if 'Uncertainty in Intercept' in line:
                    self._wilson_fit_m_sd = float(line.split()[-1])
                if 'Resolution range' in line:
                    self._wilson_fit_range = map(float, line.split()[-2:])
                    
                    
            results = self.parse_ccp4_loggraph()
            moments = transpose_loggraph(
                results['Acentric Moments of E for k = 1,3,4,6,8'])
            
            # keys we want in this are "Resln_Range" "1/resol^2" and
            # MomentZ2. The last of these should be around two, but is
            # likely to be a little different to this.
            self._moments = moments
            
            return

        def get_b_factor(self):
            return self._b_factor

        def get_wilson_fit(self):
            return self._wilson_fit_grad, self._wilson_fit_grad_sd, \
                   self._wilson_fit_m, self._wilson_fit_m_sd

        def get_wilson_fit_range(self):
            return self._wilson_fit_range

        def get_moments(self):
            return self._moments

    return TruncateWrapper()
