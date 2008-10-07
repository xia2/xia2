#!/usr/bin/env python
# Mtz2sca.py
#   Copyright (C) 2008 STFC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper for the jiffy program mtz2sca - this will help in copying
# mtz columns to scalepack files.

import sys
import os
import shutil

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory
from Wrappers.CCP4.Mtzdump import Mtzdump

def Mtz2sca(DriverType = None):
    '''Create a Mtz2sca instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class Mtz2scaWrapper(DriverInstance.__class__):
        '''A wrapper class for Mtz2sca.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('mtz2sca')

            # input files
            self._hklin = None
            self._scaout = None
            self._name = None

            return

        def set_hklin(self, hklin):
            self._hklin = hklin
            return

        def set_scaout(self, scaout):
            self._scaout = scaout
            return

        def set_name(self, name):
            self._name = name
            return

        def find_name(self):
            '''Try to identify the columns which belong to name.'''

            md = Mtzdump()
            md.set_hklin(self._hklin)
            md.dump()
            columns = md.get_columns()

            new_columns = []

            for c in columns:
                if self._name in c[0] and c[1] in ['K', 'M']:
                    new_columns.append(c[0])

            if len(new_columns) != 4:
                raise RuntimeError, 'did not find 4 matching columns'

            p = None
            P = None
            m = None
            M = None

            for c in new_columns:
                if 'SIG' in c:
                    if '+' in c:
                        P = c
                    else:
                        M = c
                else:
                    if '+' in c:
                        p = c
                    else:
                        m = c

            if not p or not P or not m or not M:
                raise RuntimeError, 'could not identify all columns'

            return p, P, m, M

        def run(self):
            if not self._hklin:
                raise RuntimeError, 'hklin not defined'

            scaout = self._scaout

            if not scaout:
                if self._name:
                    scaout = '%s_%s.sca' % \
                             (os.path.split(self._hklin)[-1][:-4],
                              self._name)
                else:
                    scaout = '%s.sca' % \
                             (os.path.split(self._hklin)[-1][:-4])
                    
            self.add_command_line(self._hklin)
            self.add_command_line(scaout)

            if self._name:
                p, P, m, M = self.find_name()
                self.add_command_line('-p')
                self.add_command_line(p)
                self.add_command_line('-P')
                self.add_command_line(P)
                self.add_command_line('-m')
                self.add_command_line(m)
                self.add_command_line('-M')
                self.add_command_line(M)

            self.start()
            self.close_wait()

            for record in self.get_all_output():
                if 'Please provide' in record:
                    raise RuntimeError, 'need to specify name'

            return scaout

    return Mtz2scaWrapper()

if __name__ == '__main__':

    if len(sys.argv) < 2:
        raise RuntimeError, '%s in.mtz [name]' % sys.argv[0]

    m2s = Mtz2sca()

    m2s.set_hklin(sys.argv[1])

    if len(sys.argv) == 2:
        m2s.run()

    else:
        for name in sys.argv[2:]:
            m2s.set_name(name)
            print m2s.run()
