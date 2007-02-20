#!/usr/bin/env python
# Shelxd.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
# 
# A wrapper for the substructure determination program shelxd - this will 
# provide a source of heavy atom information based on prepared reflection
# files from shelxc and a few interesting pieces of information. It will
# return some interesting facts about the substructure and the substructure
# itself, if it worked.
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from lib.SubstructureLib import parse_pdb_sites_file, \
     write_pdb_sites_file
from Handlers.Syminfo import Syminfo

from Driver.DriverFactory import DriverFactory

def Shelxd(DriverType = None):
    '''Create a Shelxd instance based on the DriverType.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ShelxdWrapper(DriverInstance.__class__):
        '''A wrapper class for Shelxd.'''

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable('shelxd')

            # input parameters

            self._name = None

            # an optional list of peers
            self._peer_list = [self]

            # an optional spacegroup override if we are changing
            # what was in the .ins file
            self._spacegroup = None

            # some results - quality information
            self._cc_all = 0.0
            self._cc_weak = 0.0

            # the sites in a generic format e.g. for phasing with
            # bp3 or sharp or something
            self._sites = None

            # the shelx-suite specific files for phasing with
            # e.g. shelxe
            self._res = None

            return

        def __cmp__(self, other):
            if self.get_cc_weak() < other.get_cc_weak():
                return -1
            elif self.get_cc_weak() > other.get_cc_weak():
                return +1
            return 0

        def set_peer_list(self, peer_list):
            self._peer_list = peer_list

        def get_cc_weak(self):
            if self._cc_weak == 0.0:
                self._find_sites()

            return self._cc_weak

        def _get_spacegroup(self):
            return self._spacegroup

        def _get_res(self):
            return self._res

        def get_res(self):
            self._peer_list.sort()
            return self._peer_list[-1]._get_res()

        def get_spacegroup(self):
            '''This may initiate processing.'''
            self._peer_list.sort()
            return self._peer_list[-1]._get_spacegroup()

        def set_spacegroup(self, spacegroup):
            self._spacegroup = spacegroup

        def get_sites(self):
            self._peer_list.sort()
            return self._peer_list[-1]._get_sites()
            
        def set_name(self, name):
            self._name = name
            return

        def _get_sites(self):
            if not self._sites:
                self._find_sites()
            return self._sites

        def _find_sites(self):
            '''Find the HA sites.'''

            self.add_command_line('%s_fa' % self._name)

            # optionally jimmy the .ins file for the correct spacegroup
            if self._spacegroup:

                # do not want the identity - the rest will be popped
                # to prevent them from being written twice
                sym_tokens = Syminfo.get_symops(self._spacegroup)[1:]

                # reqrite the .ins file                
                ins = open(os.path.join(self.get_working_directory(),
                                        '%s_fa.ins' % self._name),
                           'r').readlines()
            
                out = open(os.path.join(self.get_working_directory(),
                                        '%s_fa.ins' % self._name), 'w')

                for i in ins:
                    if not 'SYMM' in i[:4]:
                        out.write(i)
                    else:
                        while sym_tokens:
                            out.write('SYMM %s\n' % sym_tokens.pop())

                out.close()

            self.start()
            self.close_wait()

            output = self.get_all_output()

            # check the status

            # read the statistics from the file

            for o in output:
                if 'Try' in o and 'CC All' in o:
                    self._cc_all = float(o.split()[8])
                    self._cc_weak = float(o.split()[10].replace(',', ''))

            # read the sites and populate a substructure
            # object - these are in '%s_fa.pdb' % self._name

            self._sites = parse_pdb_sites_file(os.path.join(
                self.get_working_directory(), '%s_fa.pdb' % self._name))

            # read the .res file

            self._res = open(os.path.join(
                self.get_working_directory(), '%s_fa.res' % self._name)).read()

            return

    return ShelxdWrapper()

if __name__ == '__main__':
    # run the test - continued from Shelxc.py

    sd = Shelxd()
    sd.write_log_file('shelxd.log')
    sd.set_name('TS00')
    sd.find_sites()
    write_pdb_sites_file(sd.get_sites())
