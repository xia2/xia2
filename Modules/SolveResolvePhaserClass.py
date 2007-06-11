#!/usr/bin/python
# 
# DEVELOPMENT CODE DO NOT USE
# 
# SolveResolvePhaserClass.py
# Maintained by G.Winter

import os
import sys

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.Solve.Solve import Solve
from Wrappers.Solve.Resolve import Resolve

from Wrappers.CCP4.Mtzdump import Mtzdump

# interface that this will implement
from HAPhaserClass import HAPhaserClass

class SolveResolvePhaserClass(HAPhaserClass):

    def __init__(self):
        HAPhaserClass.__init__(self)

        # check we have the things we need
        solve = Solve()
        resolve = Resolve()

        return

    def phase(self):

        solve = Solve()
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
        mtzdump.set_hklin(self._hklin)
        mtzdump.dump()
        resolution_range = mtzdump.get_resolution_range()
        solve.set_resolution_high(min(resolution_range))
        solve.set_resolution_low(max(resolution_range))
                
        # then run

        solve.close_wait()

        # then run resolve

        resolve = Resolve()
        resolve.set_solvent(self._solvent) 
        resolve.close_wait()
        
        return

        
if __name__ == '__main__':
    spc = ShelxPhaserClass()
    spc.phase()

    
        
