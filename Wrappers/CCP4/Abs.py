#!/usr/bin/env python
# Abs.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 16th November 2006
# 
# A wrapper for the hand determination program Abs.
#

import sys
import os
import math

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Abs(DriverType = None):
    '''A factory for AbsWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class AbsWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Abs, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('abs')

            # this is a "sites" object as produced by SubstructureLib
            # parse_pdb_sites_file
            self._sites = None

            # need the input columns arranged in data sets
            # assert that these are called F(+)_INFL &c. for
            # wavelength INFL.
            self._input_dataset = None

            self._correct_hand = None
            self._atoms_good = None

            return


        def set_sites(self, sites):
            self._sites = sites
            return

        def set_dataset(self, dname):
            self._input_dataset = dname
            return

        def decide_hand(self):
            '''Perform phasing on the input data.'''

            self.check_hklin()

            if not self._input_dataset:
                raise RuntimeError, 'dataset not assigned'

            self.start()

            # ASSERT: there is only one heavy atom in here
            for site in self._sites['sites']:
                self.input('atom %f %f %f' % tuple(site['fractional']))

            self.input('resolution 3.0')
            dname = self._input_dataset
            labin = 'labin F=F_%s SIGF=SIGF_%s ' + \
                    'DANO=DANO_%s SIGDANO=SIGDANO_%s'
            self.input(labin % (dname, dname, dname, dname))

            self.close_wait()

            self.check_for_errors()
            self.check_ccp4_errors()

            for o in self.get_all_output():
                if '*incorrect configuration*' in o:
                    self._correct_hand = False
                    score = math.fabs(float(o.split()[2]))
                    if score < 0.01:
                        self._atoms_good = False
                    if score > 0.02:
                        self._atoms_good = True
                        
                if '*correct configuration*' in o:
                    self._correct_hand = True
                    score = math.fabs(float(o.split()[2]))
                    if score < 0.01:
                        self._atoms_good = False
                    if score > 0.02:
                        self._atoms_good = True
                    
            return self._correct_hand, self._atoms_good

    return AbsWrapper()

if __name__ == '__main__':

    # run a test

    if not os.path.join(os.environ['XIA2_ROOT'], 'lib') in sys.path:
        sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'lib'))
        
    from SubstructureLib import parse_pdb_sites_file, invert_hand

    if not os.environ.has_key('X2TD_ROOT'):
        raise RuntimeError, 'X2TD_ROOT not defined'

    hklin = os.path.join(os.environ['X2TD_ROOT'],
                         'Test', 'UnitTest', 'Wrappers', 'BP3',
                         'TS03_12287_merged_free.mtz')

    sites = parse_pdb_sites_file(os.path.join(
        os.environ['X2TD_ROOT'],
        'Test', 'UnitTest', 'Wrappers', 'BP3',
        'TS03_12287_fa_hyss_consensus_model.pdb'))

    for dataset in ['INFL', 'LREM', 'PEAK']:

        print dataset

        abs = Abs()
        
        abs.set_hklin(hklin)
        abs.set_sites(sites)
        abs.set_dataset(dataset)

        print abs.decide_hand()

        sites_invert = invert_hand(sites)
        hklin = os.path.join(os.environ['X2TD_ROOT'],
                             'Test', 'UnitTest', 'Wrappers', 'BP3',
                             'TS03_12287_merged_free_inv.mtz')

        abs = Abs()
        
        abs.set_hklin(hklin)
        abs.set_sites(sites_invert)
        abs.set_dataset(dataset)

        print abs.decide_hand()
    
