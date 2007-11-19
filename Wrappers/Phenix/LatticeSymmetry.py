#!/usr/bin/env python
# LatticeSymmetry.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper for the CCTBX jiffy program iotbx.lattice_symmetry which is
# used like:
# 
# iotbx.lattice_symmetry --unit-cell=a,b,c,alpha,beta,gamma --space-group=sg
# 
# And gives a list of possible spacegroup / unit cell / reindex operators
# for other likely lattices. Last is always P1 (P-1 strictly).
# 
# 19 November 2007
#

import os
import sys

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

from Wrappers.XIA.Symop2mat import Symop2mat

def LatticeSymmetry(DriverType = None):
    '''A factory for the LatticeSymmetry wrappers.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class LatticeSymmetryWrapper(DriverInstance.__class__):
        '''A wrapper class for iotbx.lattice_symmetry.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('iotbx.lattice_symmetry')

            self._cell = None
            self._spacegroup = None

            return

        def set_cell(self, cell):
            self._cell = cell
            return

        def set_spacegroup(self, spacegroup):
            self._spacegroup = spacegroup
            return

        def generate_primative_reindex(self):
            if not self._cell:
                raise RuntimeError, 'no unit cell specified'

            if not self._spacegroup:
                raise RuntimeError, 'no spacegroup specified'

            self.add_command_line('--unit_cell=%f,%f,%f,%f,%f,%f' % \
                                  tuple(self._cell))
            self.add_command_line('--space-group=%s' % self._spacegroup)

            self.start()
            self.close_wait()

            # triclinic solution will always come last so use this...

            cell = None
            reindex = None
            
            for line in self.get_all_output():
                # print line[:-1]
                if 'Unit cell:' in line:
                    cell_text = line.replace('Unit cell: (', '').replace(
                        ')', '').strip().replace(',', ' ')
                    cell = tuple(map(float, cell_text.split()))
                # if 'Change of basis:' in line:
                # reindex = line.replace('Change of basis:', '').strip()
                if 'Inverse:' in line:
                    reindex = line.replace('Inverse:', '').strip()

            return cell, reindex.replace('*', '')

    return LatticeSymmetryWrapper()

if __name__ == '__main__':

    ls = LatticeSymmetry()

    ls.set_cell((90.22, 90.22, 90.22, 90.0, 90.0, 90.0))
    ls.set_spacegroup('F23')

    cell, reindex = ls.generate_primative_reindex()

    s2m = Symop2mat()

    print 'Unit cell: %.2f %.2f %.2f %.2f %.2f %.2f' % cell
    print 'Reindex: %s' % reindex
    print 'Matrix: %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f ' % \
          tuple(s2m.convert(reindex))
    
    
