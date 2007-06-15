#!/usr/bin/python
# 
# DEVELOPMENT CODE DO NOT USE
# 
# HyssBP3DMPhaserClass.py
# Maintained by G.Winter

import os
import sys

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.Shelx.Shelxc import Shelxc
from Wrappers.Phenix.Hyss import Hyss
from Wrappers.CCP4.BP3 import BP3
from Wrappers.CCP4.DM import DM
from Wrappers.CCP4.Freerflag import Freerflag
from Wrappers.CCP4.Mtzdump import Mtzdump
from Wrappers.CCP4.Wilson import Wilson

# interface that this will implement
from HAPhaserClass import HAPhaserClass

# helper functions
from Handlers.Streams import Chatter
from lib.SubstructureLib import invert_hand

class HyssBP3DMPhaserClass(HAPhaserClass):

    def __init__(self):
        HAPhaserClass.__init__(self)

        # check we have the things we need
        shelxc = Shelxc()
        hyss = Hyss()
        bp3 = BP3()
        dm = DM()

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

        Chatter.write('Finding HA sites')

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
        sites_oh = invert_hand(sites)

        Chatter.write('Estimating B factor')

        wilson = Wilson()
        wilson.set_log_file('wilson.log')
        wilson.set_hklin(self._mtz_file)
        wilson.set_nres(self._nres)
        wilson.set_dataset(self._scalepack_files.keys()[0])
        wilson.compute_b()
        b_factor = wilson.get_b_factor()

        Chater.write('Wilson B factor estimated as: %.2f' % b_factor)

        # phase

        Chatter.write('Computing MAD phases')

        bp3 = BP3()
        bp3.write_log_file('bp3.log')
        bp3.set_hklin(self._mtz_file)
        bp3.set_hklout('bp3.mtz')
        bp3.set_sites(sites)
        for name in self._scalepack_files.keys():
            fp = self._input_dict[name]['fp']
            fpp = self._input_dict[name]['fpp']
            bp3.add_dataset(name, fp, fpp)
        bp3.set_biso(b_factor)
        bp3.set_name('strawman')
        bp3.phase()
        
        # density modify

        Chatter.write('Performing density modification')

        dm = DM()
        dm.write_log_file('dm.log')
        dm.set_hklin('bp3.mtz')
        dm.set_hklout('dm.mtz')
        dm.set_solvent(self._solvent)
        dm.improve_phases()

        if self.compute_spacegroup_enantiomorph(self._spacegroup) == \
           self._spacegroup:

            Chatter.write('Testing other hand')
            
            # phase on other hand

            Chatter.write('Computing MAD phases (oh)')

            bp3 = BP3()
            bp3.write_log_file('bp3_oh.log')
            bp3.set_hklin(self._mtz_file)
            bp3.set_hklout('bp3_oh.mtz')
            bp3.set_sites(sites)
            for name in self._scalepack_files.keys():
                fp = self._input_dict[name]['fp']
                fpp = self._input_dict[name]['fpp']
                bp3.add_dataset(name, fp, fpp)
            bp3.set_biso(b_factor)
            bp3.set_name('strawman_oh')
            bp3.phase()
        
            # density modify
            
            Chatter.write('Performing density modification (oh)')

            dm = DM()
            dm.write_log_file('dm_oh.log')
            dm.set_hklin('bp3_oh.mtz')
            dm.set_hklout('dm.mtz')
            dm.set_solvent(self._solvent)
            dm.improve_phases()
            
        # select correct hand

        # add free flag
        
        return

        
if __name__ == '__main__':
    pc = HyssBP3DMPhaserClass()
    pc.phase()

    
        
