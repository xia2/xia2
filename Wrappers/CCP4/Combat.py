#!/usr/bin/env python
# Combat.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 5th June 2006
#
# An example of an combat CCP4 program wrapper, which can be used as the
# base for other wrappers.
#
# Provides:
#
# Conversion from XDS format and Unmerged scalepack format to MTZ
# unmerged format.
#

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory
from Handlers.Streams import Debug

def Combat(DriverType = None):
    '''A factory for CombatWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class CombatWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Combat, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'combat'))

            self._pname = None
            self._xname = None
            self._dname = None

            # optional information - useful if this is
            # a scalepack input file though as we need to get the
            # spacegroup and so on set...
            self._spacegroup = None
            self._cell = None
            self._wavelength = None

            return

        def _find_largest_negative_intensity_xds(self):
            '''Find the largest negative intensity in the reflection
            file - this will be used to define a scale factor.'''

            imin = 0.0

            for record in open(self.get_hklin(), 'r').readlines():
                if record[0] == '!':
                    continue
                i = float(record.split()[3])
                if i < imin:
                    imin = i

            return imin

        def set_project_info(self, pname, xname, dname):
            self._pname = pname
            self._xname = xname
            self._dname = dname
            return

        def set_cell(self, cell):
            self._cell = cell

        def set_spacegroup(self, spacegroup):
            self._spacegroup = spacegroup

        def set_wavelength(self, wavelength):
            self._wavelength = wavelength

        def run(self):
            '''Actually convert to MTZ.'''

            self.check_hklin()
            self.check_hklout()

            # inspect hklin to decide what format it is...

            format = None

            # check for XDS format

            first_char = open(self.get_hklin(), 'r').read(1)
            if first_char == '!':
                # may be XDS
                first_line = open(self.get_hklin(), 'r').readline()
                if 'XDS_ASCII' in first_line:
                    format = 'XDSASCII'

            # check for scalepack format...?

            if not format:
                format = 'SCAL_NM2'

            if not format:
                raise RuntimeError, 'unknown format input file %s' % \
                      self.get_hklin()

            if format == 'SCAL_NM2' and not self._cell:
                raise RuntimeError, 'need CELL for scalepack unmerged'
            if format == 'SCAL_NM2' and not self._spacegroup:
                raise RuntimeError, 'need SPACEGROUP for scalepack unmerged'

            self.start()
            self.input('input %s' % format)
            if format == 'XDSASCII':

                # determine the appropriate scale factor
                imin = self._find_largest_negative_intensity_xds()

                Debug.write('Imin found to be %f' % imin)

                scale = 1.0
                while imin * scale < -999999.0:
                    scale *= 0.1

                Debug.write('Determined scale factor of %f' % scale)
                self.input('scale %s' % scale)

            if self._pname and self._xname and self._dname:
                self.input('pname %s' % self._pname)
                self.input('xname %s' % self._xname)
                self.input('dname %s' % self._dname)

            if self._cell:
                self.input('cell %f %f %f %f %f %f' % self._cell)
            if self._spacegroup:
                self.input('symmetry %s' % self._spacegroup)
            if self._wavelength:
                self.input('wavelength %f' % self._wavelength)

            self.close_wait()

            # check the status

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

    return CombatWrapper()

if __name__ == '__main__':
    # run a test

    # test XDS_ASCII
    try:
        if len(sys.argv) > 1:
            hklin = sys.argv[1]
        else:
            hklin = 'XDS_ASCII.HKL'

        c = Combat()
        c.write_log_file('combat-debug.log')
        c.set_hklin(hklin)
        c.set_hklout('temp.mtz')
        c.run()
    except RuntimeError, e:
        print e

    if False:

        # test unmerged polish

        c = Combat()

        hklin = os.path.join(os.environ['X2TD_ROOT'],
                             'Test', 'UnitTest', 'Interfaces',
                             'Scaler', 'Unmerged', 'TS00_13185_unmerged_INFL.sca')

        c.set_hklin(hklin)
        c.set_project_information('TS00', '13185', 'INFL')
        c.set_spacegroup('P212121')
        c.set_cell((57.74, 73.93, 86.57, 90.00, 90.00, 90.00))
        c.set_hklout('TS00_13185_unmerged_INFL.mtz')
        c.run()
