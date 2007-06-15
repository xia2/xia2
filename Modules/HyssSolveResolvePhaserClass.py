#!/usr/bin/python
# 
# DEVELOPMENT CODE DO NOT USE
# 
# HyssSolveResolvePhaserClass.py
# Maintained by G.Winter

import os
import sys

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.Solve.Solve import Solve
from Wrappers.Solve.Resolve import Resolve
from Wrappers.Shelx.Shelxc import Shelxc
from Wrappers.Phenix.Hyss import Hyss

from Wrappers.CCP4.Mtzdump import Mtzdump

# interface that this will implement
from HAPhaserClass import HAPhaserClass

class HyssSolveResolvePhaserClass(HAPhaserClass):

    def __init__(self):
        HAPhaserClass.__init__(self)

        # check we have the things we need
        solve = Solve()
        resolve = Resolve()
        hyss = Hyss()
        shelxc = Shelxc()

        return

    def phase(self):

        # prepare data
        shelxc = Shelxc()
        shelxc.write_log_file('shelxc.log')
        shelxc.set_cell(self._cell)
        shelxc.set_symmetry(self._spacegroup)
        shelxc.set_n_sites(self._input_dict['n_sites'])
        
        for wavelength in self._scalepack_files.keys():
            if wavelength.upper() == 'PEAK':
                shelxc.set_peak(self._scalepack_files[wavelength])
            if wavelength.upper() == 'INFL':
                shelxc.set_infl(self._scalepack_files[wavelength])
            if wavelength.upper() == 'LREM':
                shelxc.set_lrem(self._scalepack_files[wavelength])
            if wavelength.upper() == 'HREM':
                shelxc.set_hrem(self._scalepack_files[wavelength])
            if wavelength.upper() == 'SAD':
                shelxc.set_sad(self._scalepack_files[wavelength])

        shelxc.set_name('strawman')
        shelxc.prepare()

        hklf3_in = shelxc.get_fa_hkl()

        # find sites

        hyss = Hyss()
        hyss.write_log_file('hyss.log')
        hyss.set_hklin(hklf3_in)
        hyss.set_hklin_type('hklf3')
        hyss.set_cell(self._cell)
        hyss.set_spacegroup(self._spacegroup)
        hyss.set_n_sites(self._input_dict['n_sites'])
        hyss.set_atom(self._input_dict['atom'])
        hyss.find_substructure()
        sites = hyss.get_sites()

        # phase

        solve = Solve()
        solve.set_sites(sites)
        solve.write_log_file('solve.log')
        solve.set_hklin(self._mtz_file)
        for name in self._scalepack_files.keys():
            wavelength = self._input_dict[name]['wavelength']
            fp = self._input_dict[name]['fp']
            fpp = self._input_dict[name]['fpp']
            solve.add_wavelength(name, wavelength, fp, fpp)

        solve.set_n_sites(self._n_sites)
        solve.set_nres(self._nres)
        solve.set_atom(self._atom)

        # need to get the resolution range from the mtz file...

        mtzdump = Mtzdump()
        mtzdump.set_hklin(self._mtz_file)
        mtzdump.dump()
        resolution_range = mtzdump.get_resolution_range()
        solve.set_resolution_high(min(resolution_range))
        solve.set_resolution_low(max(resolution_range))
                
        # then run

        solve.run()

        # then run resolve

        resolve = Resolve()
        resolve.write_log_file('resolve.log')
        resolve.set_solvent(self._solvent) 
        resolve.run()
        
        return

        
if __name__ == '__main__':
    hsrpc = HyssSolveResolvePhaserClass()
    hsrpc.phase()

    
        
