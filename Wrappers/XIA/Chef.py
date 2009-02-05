#!/usr/bin/env python
# Chef.py
#   Copyright (C) 2008 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 5th February 2008
#
# A wrapper for the new program "chef". This has been developed for xia2
# to analyse the bulk properties of intensity measurements, particularly
# looking at how well they agree. The idea is that reflection files with
# DOSE columns added in by DOSER may be inspected to determine the 
# dose / resolution envelope optimal for given analysis processes, viz:
# 
# - substructure determination
# - phase calculation
# - density modification & refinement
# 
# This should give "proper" resolution limits...

import os
import sys
import math

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory
from lib.Guff import transpose_loggraph
from Wrappers.CCP4.Mtzdump import Mtzdump

def Chef(DriverType = None):
    '''A factory for wrappers for the chef.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class ChefWrapper(CCP4DriverInstance.__class__):
        '''Provide access to the functionality in chef.'''

        def __init__(self):

            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable('chef')

            self._hklin_list = []
            self._anomalous = False
            self._b_width = 0.0
            self._b_max = 0.0
            self._b_labin = None
            self._resolution = 0.0

            self._p_crd = True
            
            return

        def add_hklin(self, hklin):
            self._hklin_list.append(hklin)
            return

        def set_anomalous(self, anomalous):
            self._anomalous = anomalous
            return

        def set_resolution(self, resolution):
            self._resolution = resolution
            return

        def set_width(self, width):
            self._b_width = width
            return

        def set_max(self, max):
            self._b_max = max
            return

        def set_labin(self, labin):
            self._b_labin = labin
            return

        def run(self):
            '''Actually run chef...'''

            if len(self._hklin_list) == 0:
                raise RuntimeError, 'HKLIN not defined'

            for j in range(len(self._hklin_list)):
                self.add_command_line('HKLIN%d' % (j + 1))
                self.add_command_line(self._hklin_list[j])

            self.start()

            self.input('print chi comp')

            if self._anomalous:
                self.input('anomalous on')
            if self._b_width > 0.0:
                self.input('range width %f' % self._b_width)
            if self._b_max > 0.0:
                self.input('range max %f' % self._b_max)

            if self._resolution > 0.0:
                self.input('resolution %.2f' % self._resolution)

            self.input('labin BASE=%s' % self._b_labin)

            self.close_wait()

            # FIXME should check the status here...

            results = self.parse_ccp4_loggraph()

            rd = transpose_loggraph(
                results['Cumulative RD analysis'])

            dose = rd['1_FIXME_DOSE']
            overall = rd['2_Overall']

            for j in range(len(dose)):
                print '%8.0f %5.2f' % (float(dose[j]), float(overall[j]))
            

    return ChefWrapper()
        
if __name__ == '__main__':
    # then run a test...

    source = os.path.join(os.environ['X2TD_ROOT'], 'Test', 'Chef',
                          'TestData')

    # first find the maximum dose... and minimum resolution range

    dmax = 0.0
    dmin = 100.0

    for hklin in ['TS03_12287_doser_INFL.mtz',
                  'TS03_12287_doser_LREM.mtz',
                  'TS03_12287_doser_PEAK.mtz']:

        md = Mtzdump()
        md.set_hklin(os.path.join(source, hklin))
        md.dump()
        dmax = max(dmax, max(md.get_column_range('DOSE')[:2]))
        dmin = min(dmin, md.get_column_range('DOSE')[2])

    chef = Chef()
    chef.write_log_file('chef.log')

    for hklin in ['TS03_12287_doser_INFL.mtz',
                  'TS03_12287_doser_LREM.mtz',
                  'TS03_12287_doser_PEAK.mtz']:
        chef.add_hklin(os.path.join(source, hklin))

    chef.set_anomalous(True)
    chef.set_width(0.01 * dmax)
    chef.set_max(dmax)
    chef.set_resolution(dmin)
    chef.set_labin('DOSE')

    chef.run()


