#!/usr/bin/env python
# Best.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 20th August 2007
# 
# A wrapper for the EMBL strategy program BEST.
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Schema.Interfaces.StrategyComputer import StrategyElement

# class to use to return strategy information - this should probably
# be moved somewhere more useful like the strategy interface

def Best(DriverType = None):
    '''A factory for wrappers for the best.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class BestWrapper(DriverInstance.__class__):
        '''Provide access to the functionality in best.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('best')

            # BEST parameters

            self._detector_name = None
            self._i_over_sig = 2.0
            self._exposure_time = None
            self._completeness = 0.99
            self._redundancy = 2.0
            self._anomalous = False
            self._dat_file = None
            self._par_file = None
            self._hkl_files = []

            # resulting strategies - will be a list of
            # StrategyElements

            self._strategy = []

            return

        def set_detector_name(self, detector_name):
            self._detector_name = detector_name
            return

        def set_i_over_sig(self, i_over_sig):
            self._i_over_sig = i_over_sig
            return

        def set_exposure_time(self, exposure_time):
            self._exposure_time = exposure_time
            return

        def set_completeness(self, completeness):
            self._completeness = completeness
            return

        def set_redundancy(self, redundancy):
            self._redundancy = redundancy
            return

        def set_anomalous(self, anomalous = True):
            self._anomalous = anomalous
            return

        def set_dat_file(self, dat_file):
            self._dat_file = dat_file
            return

        def set_par_file(self, par_file):
            self._par_file = par_file
            return

        def add_hkl_file(self, hkl_file):
            self._hkl_files.append(hkl_file)
            return

        def compute_strategy(self):
            
            if self._detector_name is None:
                raise RuntimeError, 'no detector_name set'

            if self._exposure_time is None:
                raise RuntimeError, 'no exposure_time set'

            if self._dat_file is None:
                raise RuntimeError, 'no dat_file set'

            if self._par_file is None:
                raise RuntimeError, 'no par_file set'

            if self._hkl_files is []:
                raise RuntimeError, 'no hkl files set'

            self.add_command_line('-f')
            self.add_command_line(self._detector_name)
            self.add_command_line('-i2s')
            self.add_command_line(str(self._i_over_sig))
            self.add_command_line('-t')
            self.add_command_line(str(self._exposure_time))
            self.add_command_line('-C')
            self.add_command_line(str(self._completeness))
            self.add_command_line('-R')
            self.add_command_line(str(self._redundancy))
            self.add_command_line('-e')
            self.add_command_line('none')
            if self._anomalous:
                self.add_command_line('-a')
            self.add_command_line('-mos')
            self.add_command_line(self._dat_file)
            self.add_command_line(self._par_file)
            for hkl in self._hkl_files:
                self.add_command_line(hkl)
            self.start()
            self.close_wait()

            # parse the output

            output = self.get_all_output()

            for j in range(len(output)):
                line = output[j]

                if 'Phi_start| N.of.images' in line:
                    i = j + 2
                    while not '--------' in output[i]:
                        line = output[i]
                        list = line.split()
                        self._strategy.append(
                            StrategyElement(float(list[1]),
                                            float(list[3]),
                                            float(list[5]),
                                            int(list[2]),
                                            float(list[4])))
                                            
                        i += 1
                        print self._strategy[-1]

    return BestWrapper()

if __name__ == '__main__':
    best = Best()

    best.set_detector_name('q315-2x')
    best.set_exposure_time(1.0)
    best.set_anomalous()
    best.set_dat_file('bestfile.dat')
    best.set_par_file('bestfile.par')
    best.add_hkl_file('bestfile_001.hkl')
    best.add_hkl_file('bestfile_002.hkl')

    best.compute_strategy()
