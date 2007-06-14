#!/usr/bin/env python
# FileName.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

def Shelxe(DriverType = None):
    '''Create a Shelxe instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShelxeWrapper(DriverInstance.__class__):
        '''A wrapper class for Shelxe.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('shelxe')

            self._name = None
            self._solvent = 0.0
            self._enantiomorph = False

            # output information
            self._contrast = []
            self._connectivity = []
            self._pf_cc = 0.0
            self._map_cc = []

        def set_solvent(self, solvent):
            self._solvent = solvent
            return

        def set_name(self, name):
            self._name = name
            return

        def set_enantiomorph(self, enantiomorph = True):
            self._enantiomorph = enantiomorph
            return

        def phase(self):
            '''Actually compute the phases from the heavy atom locations.'''

            self.add_command_line('%s' % self._name)
            self.add_command_line('%s_fa' % self._name)
            self.add_command_line('-h')
            self.add_command_line('-s%f' % self._solvent)
            self.add_command_line('-m20')
            if self._enantiomorph:
                self.add_command_line('-i')

            self.start()

            self.close_wait()

            output = self.get_all_output()
            # analyse the output

            for o in output:
                if '<wt>' in o and 'dens.mod.' in o:
                    contrast = float(o.split()[5].replace(',', ''))
                    connectivity = float(o.split()[8])

                    self._contrast.append(contrast)
                    self._connectivity.append(connectivity)

                if '<mapCC>' in o:
                    self._map_cc = map(float, o.split()[1:])

                if 'Pseudo-free CC' in o:
                    self._pf_cc = float(o.split()[-2])

            return

        def get_pf_cc(self):
            return self._pf_cc

    return ShelxeWrapper()

if __name__ == '__main__':
    # continue the test

    se = Shelxe()
    se.write_log_file('shelxe.log')
    se.set_name('TS00')
    se.set_solvent(0.49)
    se.phase()

    se = Shelxe()
    se.write_log_file('shelxe_oh.log')
    se.set_name('TS00')
    se.set_solvent(0.49)
    se.set_enantiomorph()
    se.phase()

    # convert files to mtz to help displaying

    from Wrappers.CCP4.F2mtz import F2mtz

    f = F2mtz()

    f.set_hklin('TS00.phs')
    f.set_hklout('TS00.mtz')
    f.set_cell((57.74, 76.93, 86.57, 90.00, 90.00, 90.00))
    # f.set_symmetry('P212121')
    f.set_symmetry('P222')
    f.f2mtz()
        
    f = F2mtz()

    f.set_hklin('TS00_i.phs')
    f.set_hklout('TS00_oh.mtz')
    f.set_cell((57.74, 76.93, 86.57, 90.00, 90.00, 90.00))
    # f.set_symmetry('P212121')
    f.set_symmetry('P222')
    f.f2mtz()
    
    
    
