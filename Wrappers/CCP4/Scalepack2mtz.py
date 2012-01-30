#!/usr/bin/env python
# Scalepack2mtz.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper for the jiffy program scalepack2mtz to convert merged
# scalepack files to MTZ format - with an added spacegroup and
# pname/xname/dname stuff.
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Scalepack2mtz(DriverType = None):
    '''A factory for Scalepack2mtzWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class Scalepack2mtzWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Scalepack2mtz, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'scalepack2mtz'))

            # specific information
            self._pname = None
            self._xname = None
            self._dname = None
            self._spacegroup = None

            # optional information
            self._cell = None

            return

        def set_spacegroup(self, spacegroup):
            self._spacegroup = spacegroup

        def set_cell(self, cell):
            self._cell = cell

        def set_project_info(self, pname, xname, dname):
            self._pname = pname
            self._xname = xname
            self._dname = dname

        def convert(self):
            self.check_hklin()
            self.check_hklout()

            if not self._spacegroup:
                raise RuntimeError, 'spacegroup must be assigned'

            self.start()

            self.input('symmetry %s' % self._spacegroup)
            if self._pname and self._xname and self._dname:
                self.input('name project %s crystal %s dataset %s' % \
                           (self._pname, self._xname, self._dname))
            if self._cell:
                self.input('cell %f %f %f %f %f %f' % self._cell)

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

                raise e

            return

    return Scalepack2mtzWrapper()

if __name__ == '__main__':

    # then run a test

    hklin = os.path.join(os.environ['X2TD_ROOT'],
                         'Test', 'UnitTest', 'Interfaces',
                         'Scaler', 'Merged', 'TS00_13185_scaled_INFL.sca')

    hklout = 'TS00_13185_INFL.mtz'

    s2m = Scalepack2mtz()

    s2m.set_hklin(hklin)
    s2m.set_hklout(hklout)
    s2m.set_spacegroup('P212121')
    s2m.set_project_info('TS00', 'X13185', 'INFL')
    s2m.convert()
