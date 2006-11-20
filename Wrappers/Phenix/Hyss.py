#!/usr/bin/env python
# Hyss.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
# 
# FIXME 16/NOV/06 this needs to express the interface for substructure
#                 determination.
# 
# FIXME 20/NOV/06 no it doesn't - that should be handled in the Hyss
#                 SubstructureFinder module, which can include some
#                 proper preparation of the data. This should just
#                 provide the simple interface to the program and allow
#                 composition to handle everything else.

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['SS_ROOT'] in sys.path:
    sys.path.append(os.environ['SS_ROOT'])

# explicitly add the "lib" directory to the path...

if not os.path.join(os.environ['SS_ROOT'], 'lib') in sys.path:
    sys.path.append(os.path.join(os.environ['SS_ROOT'], 'lib'))

from Driver.DriverFactory import DriverFactory
from SubstructureLib import parse_pdb_sites_file, \
     write_pdb_sites_file

# from Schema.Interfaces.SubstructureFinder import SubstructureFinder

def Hyss(DriverType = None):
    '''Factory for Hyss wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class HyssWrapper(DriverInstance.__class__):
        # SubstructureFinder):
        '''A wrapper for the program phenix.hyss, for locating the heavy
        atom substructure from an anomalous data set.'''

        def __init__(self):

            DriverInstance.__class__.__init__(self)            
            self.set_executable('phenix.hyss')

            # from the interface I will need to be able to record
            # the input reflection file, the number of heavy atoms
            # to find, the form of the input reflection file if it
            # happens to be hklf3, the type of heavy atoms and the
            # spacegroup...

            self._hklin = None
            self._hklin_type = None
            self._spacegroup = None
            self._cell = None
            self._n_sites = None
            self._atom = None

            # output stuff

            self._sites = None

        def set_hklin(self, hklin):
            self._hklin = hklin
            return
            
        def set_hklin_type(self, hklin_type):
            self._hklin_type = hklin_type
            return

        def set_spacegroup(self, spacegroup):
            self._spacegroup = spacegroup
            return

        def set_cell(self, cell):
            self._cell = cell

        def set_atom(self, atom):
            self._atom = atom
            return

        def set_n_sites(self, n_sites):
            self._n_sites = n_sites
            return

        def find_substructure(self):
            '''Actually run hyss to find the sites.'''

            # check the input

            if not self._hklin:
                raise RuntimeError, 'hklin not defined'

            if not self._n_sites:
                raise RuntimeError, 'number of sites not defined'

            if not self._atom:
                raise RuntimeError, 'atom type not defined'

            if not self._spacegroup:
                raise RuntimeError, 'spacegroup not set'

            # get the prepared reflection file

            if self._hklin_type:
                self.add_command_line('%s=%s' %
                                      (self._hklin, self._hklin_type))
            else:
                self.add_command_line('%s' % self._hklin)

            self.add_command_line('%d' % self._n_sites)
            self.add_command_line('%s' % self._atom)

            self.add_command_line('--space_group=%s' % self._spacegroup)

            if self._cell:
                self.add_command_line('--unit_cell=%f,%f,%f,%f,%f,%f' % \
                                      tuple(self._cell))

            # start hyss

            self.start()

            self.close_wait()

            self.check_for_errors()

            for line in self.get_all_output():
                if 'Writing consensus model as PDB' in line:
                    pdb_file = line.split()[-1]
                    self._sites = parse_pdb_sites_file(pdb_file)

            return

        def get_sites(self):
            return self._sites

    return HyssWrapper()

if __name__ == '__main__':

    # then run a test

    if not os.environ.has_key('X2TD_ROOT'):
        raise RuntimeError, 'X2TD_ROOT not defined'

    hklin = os.path.join(os.environ['X2TD_ROOT'],
                         'Test', 'UnitTest', 'Wrappers', 'Hyss',
                         '1VR5_13193_fa.hkl')

    hyss = Hyss()

    hyss.set_hklin(hklin)
    hyss.set_hklin_type('hklf3')
    hyss.set_spacegroup('p21212')
    hyss.set_cell((140.26, 96.79, 115.88, 90.0, 90.0, 90.0))
    hyss.set_n_sites(18)
    hyss.set_atom('se')

    hyss.write_log_file('hyss.log')
    hyss.find_substructure()

    sites = hyss.get_sites()

    write_pdb_sites_file(sites)
