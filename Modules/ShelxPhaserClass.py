#!/usr/bin/python
# 
# DEVELOPMENT CODE DO NOT USE
# 
# ShelxPhaserClass.py
# Maintained by G.Winter

import os
import sys

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.Shelx.Shelxc import Shelxc
from Wrappers.Shelx.Shelxd import Shelxd
from Wrappers.Shelx.Shelxe import Shelxe
from Wrappers.CCP4.F2mtz import F2mtz
from Wrappers.CCP4.Cad import Cad
from Wrappers.CCP4.Freerflag import Freerflag

# interface that this will implement
from HAPhaserClass import HAPhaserClass

# output streams
from Handlers.Streams import Chatter, Debug

class ShelxPhaserClass(HAPhaserClass):

    def __init__(self):
        HAPhaserClass.__init__(self)

        # check we have the things we need
        shelxc = Shelxc()
        shelxd = Shelxd()
        shelxe = Shelxe()

        return

    def phase(self):

        # prepare the data

        Chatter.write('Preparing HA data with shelxc')
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

        # next look for the sites

        Chatter.write('Searching for sites with shelxd')
        shelxd = Shelxd()
        shelxd.set_name('strawman')
        shelxd.write_log_file('shelxd.log')
        shelxd.set_spacegroup(self._spacegroup)
        sites = shelxd.get_sites()

        cc_weak = shelxd.get_cc_weak()
        Chatter.write('Shelxd CC weak = %.2f' % cc_weak)

        Chatter.write('Phasing with shelxe')
        shelxe = Shelxe()
        shelxe.write_log_file('shelxe.log')
        shelxe.set_name('strawman')
        shelxe.set_solvent(self._input_dict['solvent'])
        shelxe.phase()

        pf_cc = shelxe.get_pf_cc()

        oh_best = False

        # phase in enantiomorph spacegroup if enantiomorphic possible

        if self.compute_spacegroup_enantiomorph(self._spacegroup) == \
           self._spacegroup:

            Chatter.write('Phasing with shelxe for enantiomorph')

            shelxe = Shelxe()
            shelxe.write_log_file('shelxe_oh.log')
            shelxe.set_name('strawman')
            shelxe.set_solvent(self._input_dict['solvent'])
            shelxe.set_enantiomorph()
            shelxe.phase()

            pf_cc_oh = shelxe.get_pf_cc()

            if pf_cc_oh > pf_cc:
                Chatter.write('Enantiomorph substructure chosen')
                oh_best = True
            else:
                Chatter.write('Original substructure chosen')

        else:
            Chatter.write('Not testing enantiomorph')

        if not oh_best:

            f = F2mtz()
            f.write_log_file('f2mtz.log')        
            f.set_hklin('strawman.phs')
            f.set_hklout('tmp_strawman.mtz')
            f.set_cell(self._cell)
            f.set_symmetry(self._spacegroup)
            f.f2mtz()

        else:

            f = F2mtz()
            f.set_hklin('strawman_i.phs')
            f.write_log_file('f2mtz.log')        
            f.set_hklout('tmp_strawman.mtz')
            f.set_cell(self._cell)
            f.set_symmetry(self._spacegroup)
            f.f2mtz()

        c = Cad()
        c.write_log_file('cad.log')
        c.add_hklin('tmp_strawman.mtz')
        c.set_hklout('strawman.mtz')
        c.update()

        f = Freerflag()
        f.write_log_file('freerflag.log')
        f.set_hklin('strawman.mtz')
        f.set_hklout('phased.mtz')
        f.add_free_flag()

        Chatter.write('Results in phased.mtz')
            
        return

        
if __name__ == '__main__':
    spc = ShelxPhaserClass()
    spc.phase()

    
        
