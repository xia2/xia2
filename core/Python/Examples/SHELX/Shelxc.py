#!/usr/bin/env python
# Shelxc.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 1st June 2006
# 
# An illustration of using Driver directly to operate a program - in this case
# shelxc for preparing experimental phasing data.
# 
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory

def Shelxc(DriverType = None):
    '''Create a Shelxc instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShelxcWrapper(DriverInstance.__class__):
        '''A wrapper class for Shelxc.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('shelxc')

            # input files
            self._infl = None
            self._lrem = None
            self._peak = None
            self._hrem = None
            self._sad = None
            self._native = None

            # heavy atom information
            self._nha = 0

            # cell and symmetry
            self._cell = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            self._symmetry = None

            # naming information
            self._name = None

        def set_cell(self, cell):
            self._cell = cell
            return

        def set_symmetry(self, symmetry):
            self._symmetry = symmetry
            return

        def set_nha(self, nha):
            self._nha = nha
            return

        def set_peak(self, peak):
            self._peak = peak
            return

        def set_infl(self, infl):
            self._infl = infl
            return

        def set_lrem(self, lrem):
            self._lrem = lrem
            return

        def set_hrem(self, hrem):
            self._hrem = hrem
            return

        def set_native(self, native):
            self._native = native
            return

        def set_sad(self, sad):
            self._sad = sad
            return

        def set_name(self, name):
            self._name = name
            return

        def prepare(self):
            '''Prepare the experimental phasing data.'''

            task = 'Preparing experimental phasing data using:\n'
            if self._peak:
                task += 'PEAK %s\n' % self._peak
            if self._infl:
                task += 'INFL %s\n' % self._infl
            if self._hrem:
                task += 'HREM %s\n' % self._hrem
            if self._lrem:
                task += 'LREM %s\n' % self._lrem
            if self._sad:
                task += 'SAD %s\n' % self._sad
            if self._native:
                task += 'NATIVE %s\n' % self._native

            self.setTask(task)

            self.add_command_line(self._name)

            self.start()

            if self._peak:
                self.input('PEAK %s\n' % self._peak)
            if self._infl:
                self.input('INFL %s\n' % self._infl)
            if self._hrem:
                self.input('HREM %s\n' % self._hrem)
            if self._lrem:
                self.input('LREM %s\n' % self._lrem)
            if self._sad:
                self.input('SAD %s\n' % self._sad)
            if self._native:
                self.input('NATIVE %s\n' % self._native)
            
            self.input('CELL %f %f %f %f %f %f' % tuple(self._cell))
            self.input('SPAG %s' % self._symmetry)
            self.input('FIND %d' % self._nha)
            self.input('NTRY 20')
            self.input('MIND -3.5')

            self.close()

            while True:
                line = self.output()

                if not line:
                    break

                print line[:-1]

            return

    return ShelxcWrapper()

if __name__ == '__main__':

    # then run the standard test

    s = Shelxc()

    s.set_name('demo')
    s.set_cell([51.69, 51.69, 157.80, 90.00, 90.00, 90.00])
    s.set_symmetry('P43212')
    s.set_infl('12287_1_E1_scaled.sca')
    s.set_lrem('12287_1_E2_scaled.sca')
    s.set_nha(9)

    s.prepare()
