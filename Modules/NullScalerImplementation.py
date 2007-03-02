#!/usr/bin/env python
# NullScalerImplementation.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 30/OCT/06
#
# An empty scaler - this presents the Scaler interface but does 
# nothing, making it ideal for when you have the reduced data already -
# this will simply return that reduced data...
#
# FIXME 04/DEC/06 this will need to be able to transmogrify data from one
#                 format to another (e.g. to scalepack from mtz, for instance)
#                 and also be able to get reflection file information from
#                 "trusted" formats (that is, from mtz format - cell, symmetry
#                 information will not be trusted in scalepack files.)

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.Mtzdump import Mtzdump
from Schema.Interfaces.Scaler import Scaler

class NullScalerImplementation(Scaler):
    '''A null scaler implementation which looks like a real scaler
    but actually does nothing but wrap a couple of reflection files.
    This will also transmogrify reflection files if appropriate.'''

    def __init__(self):
        '''Set myself up - making room for reflection file handles if
        appropriate. Note that this should also have room to hold the
        correct spacegroup (or a list of likely candidates) and also
        the unit cell parameters. Setters will be needed for this,
        so that that information may come from some modification of
        a .xinfo file.'''

        Scaler.__init__(self)

        # the following need to be configured:
        # self._scalr_scaled_reflection_files - dictionary containing file
        #                                       links - this will want to
        #                                       have a structure like:
        #
        # ['sca'][WAVELENGTH] = filename - for merged scalepack
        # ['sca_unmerged'][WAVELENGTH] = filename - for unmerged
        # ['mtz_merged_free'] = filename - merged cadded + free mtz
        #
        # so these are the only formats which there is any value in
        # transforming to/from.
        # 
        # self._scalr_statistics - dictionary containing statistics from
        #                          scaling
        # self._scalr_cell - canonical unit cell from data reduction
        # self._scalr_likely_spacegroups - a list of likely spacegroups
        # self._scalr_highest_resolution - a float of the highest resolution
        #                                  achieved from this crystal
        # 
        # The following tokens will be defined (optionally) for the
        # whole resolution range of the data set in the .xinfo file
        # for this stage:
        # 
        # BEGIN WAVELENGTH_STATISTICS
        # ANOMALOUS_COMPLETENESS
        # ANOMALOUS_MULTIPLICITY
        # COMPLETENESS
        # MULTIPLICITY
        # HIGH_RESOLUTION_LIMIT
        # LOW_RESOLUTION_LIMIT
        # I_SIGMA
        # R_MERGE
        # N_REF
        # N_REF_UNIQUE
        # END WAVELENGTH_STATISTICS
        #
        # These need to be mapped to the following dictionary entries
        # (which should be defined in the Scaler interface...):
        #
        # 'High resolution limit'
        # 'Low resolution limit'
        # 'Completeness'
        # 'Multiplicity'
        # 'I/sigma'
        # 'Rmerge'
        # 'Anomalous completeness'
        # 'Anomalous multiplicity'
        # 'Total observations'
        # 'Total unique'
        #
        # There are other tokens defined but they are not very interesting
        # at the moment...

        self._scalr_scaled_reflection_files = { }

        return

    def add_scaled_reflection_file(self, format_tuple, filename):
        '''Add a reflection file keyed by format and optionally wavelength
        (for e.g. scalepack files).'''

        if type(format_tuple) == type('string'):
            format_tuple = (format_tuple,)

        if len(format_tuple) == 1:
            format = format_tuple[0]
            wavelength = None
        else:
            format = format_tuple[0]
            wavelength = format_tuple[1]
        
        if not wavelength:
            self._scalr_scaled_reflection_files[format] = filename
        else:
            self._scalr_scaled_reflection_files[format][wavelength] = filename

        # hack to allow the scale method to get started
        self._scalr_integraters['fake!'] = True

        return

    def set_scaler_statistics(self, statistics_dictionary):
        '''Set the scaling statistics for later return.'''

        # transform from .xinfo format to scaler dictionary

        xinfo_to_internal = {
            'I_SIGMA':'I/Sigma',
            'R_MERGE':'Rmerge',
            'N_REF':'Total observations',
            'N_REF_UNIQUE':'Total unique'
            }

        # store statistics
        
        self._scalr_statistics = { }

        for token in statistics_dictionary.keys():
            if token in xinfo_to_internal.keys:
                self._scalr_statistics[xinfo_to_internal[
                    token]] = statistics_dictionary[token]
            else:
                self._scalr_statistics[token.replace(' ', '_').upper(
                    )] = statistics_dictionary[token]

        return
            
    def set_scaler_cell(self, cell):
        self._scalr_cell = cell
        return

    def set_scaler_likely_spacegroups(self, likely_spacegroups):
        self._scalr_likely_spacegroups = likely_spacegroups

        return

    # null methods

    def _scale_prepare(self):
        pass

    def _scale(self):
        pass

    # that should be enough...

if __name__ == '__main__':

    # run some tests - these are based on the unit tests for the
    # Mtz2Scalepack and Scalepack2mtz modules...

    hklin = os.path.join(os.environ['X2TD_ROOT'],
                         'Test', 'UnitTest', 'Interfaces',
                         'Scaler', 'Merged', 'TS00_13185_merged_free.mtz')

    nsi = NullScalerImplementation()

    nsi.add_scaled_reflection_file('mtz', hklin)
    nsi.set_scaler_cell((57.74, 76.92, 86.57, 90.00, 90.00, 90.00))

    # print nsi.get_scaled_reflections('sca')

    # run a real test - search for HA sites...

    from HyssSubstructureFinder import HyssSubstructureFinder

    hssf = HyssSubstructureFinder()

    hssf.substructure_find_add_wavelength_info('INFL', 0.97950, -12.1, 5.8)
    hssf.substructure_find_add_wavelength_info('LREM', 1.00000, -2.5, 0.5)
    hssf.substructure_find_add_wavelength_info('PEAK', 0.97934, -10.0, 6.9)

    hssf.substructure_find_set_n_sites(5)
    hssf.substructure_find_set_atom('se')
    hssf.substructure_find_set_spacegroup('P 21 21 21')
    hssf.substructure_find_set_scaler(nsi)
    hssf.substructure_find_set_name('demo')

    sites = hssf.substructure_find_get_sites()

    from Wrappers.CCP4.BP3 import BP3
    from lib.SubstructureLib import invert_hand

    # original hand

    bp3 = BP3
    
    bp3.set_hklin(nsi.get_scaled_reflections('mtz'))
    bp3.set_hklout('demo_phased.mtz')
    bp3.set_sites(sites)
    
    bp3.add_dataset('INFL', -12.1, 5.8)
    bp3.add_dataset('LREM', -2.5, 0.5)
    bp3.add_dataset('PEAK', -10.0, 6.9)

    bp3.set_biso(12.0)
    bp3.set_xname(nsi.get_scaler_project_info()[1])
    bp3.write_log_file('demo_phased.log')

    bp3.phase()
    
    # other hand - spag still P212121

    bp3oh = BP3
    
    bp3oh.set_hklin(nsi.get_scaled_reflections('mtz'))
    bp3oh.set_hklout('demo_phased_oh.mtz')
    bp3oh.set_sites(invert_hand(sites))
    
    bp3oh.add_dataset('INFL', -12.1, 5.8)
    bp3oh.add_dataset('LREM', -2.5, 0.5)
    bp3oh.add_dataset('PEAK', -10.0, 6.9)

    bp3oh.set_biso(12.0)
    bp3oh.set_xname(nsi.get_scaler_project_info()[1])
    bp3oh.write_log_file('demo_phased_oh.log')

    bp3oh.phase()
    
    # do some DM

    from Wrappers.CCP4.DM import DM

    # original hand

    dm = DM()

    dm.set_hklin('demo_phased.mtz')
    dm.set_hklout('demo_dm.mtz')
    dm.set_solvent(0.500)
    dm.write_log_file('demo_dm.log')
    dm.improve_phases()
    
    # other hand...

    dmoh = DM()

    dmoh.set_hklin('demo_phased.mtz')
    dmoh.set_hklout('demo_dm_oh.mtz')
    dmoh.set_solvent(0.500)
    dmoh.write_log_file('demo_dm_oh.log')
    dmoh.improve_phases()
    
    
