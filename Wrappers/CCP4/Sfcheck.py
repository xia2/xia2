#!/usr/bin/env python
# Sfcheck.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 23rd February 2007
#
# A wrapper for the CCP4 program sfcheck, which is used to analyse
# reduced reflections to detect e.g. twinning amongst other things.
#
# This will do:
#
# Second moment analysis
# Determination of "optical" resolution
# Analysis of Eigenvalues
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Sfcheck(DriverType = None):
    '''Create a wrapper for the CCP4 program sfcheck.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class SfcheckWrapper(DriverInstance.__class__):
        '''A wrapper class for Sfcheck.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'sfcheck'))

            # next handle the input files etc.
            self._hklin = None

            # and the output results - this is all in the log file

            self._number_reflections = None
            self._resolution_range = None
            self._optical_resolution = None
            self._b_factor = None
            self._twinning_test = None
            self._anisotropic_eigenvalues = None
            self._anisotropic_eigenvalues_reliable = True
            self._pseudo_translation = False

            return

        def set_hklin(self, hklin):
            self._hklin = hklin
            return

        def analyse(self):
            if not self._hklin:
                raise RuntimeError, 'HKLIN not defined'

            self.add_command_line('-f')
            self.add_command_line(self._hklin)

            self.start()

            self.close_wait()

            for o in self.get_all_output():

                if 'Perfect twinning test' in o:
                    self._twinning_test = float(o.split()[-1])

                if 'Optical Resolution:' in o:
                    self._optical_resolution = float(o.split()[-1])

                if 'Ratio of Eigen values' in o:
                    self._anisotropic_eigenvalues = tuple(map(float,
                                                              o.split()[-3:]))

                if 'WARNING: program: "anisoscl" is terminated' in o:
                    self._anisotropic_eigenvalues_reliable = False


        def get_twinning(self):
            return self._twinning_test

        def get_optical_resolution(self):
            return self._optical_resolution

        def get_anisotropic_eigenvalues(self):
            return self._anisotropic_eigenvalues

        def get_anisotropic_eigenvalues_reliable(self):
            return self._anisotropic_eigenvalues_reliable

    return SfcheckWrapper()

if __name__ == '__main__':
    s = Sfcheck()

    directory = os.path.join(os.environ['X2TD_ROOT'],
                             'Test', 'MAD', 'TS03')

    s.set_hklin(os.path.join(directory, 'MAD_12287_merged_free.mtz'))

    s.analyse()

    print s.get_twinning()
    print s.get_optical_resolution()
    print s.get_anisotropic_eigenvalues()
