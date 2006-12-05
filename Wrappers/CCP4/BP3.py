#!/usr/bin/env python
# BP3.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.


#
# 16th November 2006
# 
# A wrapper for the phasing program BP3.
# 
# 
# 
# 
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def BP3(DriverType = None):
    '''A factory for BP3Wrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class BP3Wrapper(CCP4DriverInstance.__class__):
        '''A wrapper for BP3, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('bp3')

            # this is a "sites" object as produced by SubstructureLib
            # parse_pdb_sites_file
            self._sites = None

            # assume for the moment the same bfactor for all sites
            self._biso = None

            # crystal name
            self._xname = None

            # need the input columns arranged in data sets
            # assert that these are called F(+)_INFL &c. for
            # wavelength INFL.
            self._input_datasets = []

            # and also the f', f'' values which go with these
            # as a dictionary keyed by the above dataset name and
            # containing 2-tuples of (f', f'') as floats.
            self._input_form_factors = { }

            return

        def set_sites(self, sites):
            self._sites = sites
            return

        def set_xname(self, xname):
            '''Set the crystal name, prepending an "X" if it looks like
            a number.'''
            try:
                x = int(xname)
                self._xname = 'X%d' % x
            except:
                self._xname = xname
                
            return

        def set_biso(self, biso):
            self._biso = biso
            return

        def add_dataset(self, dname, fp, fpp):
            self._input_datasets.append(dname)
            self._input_form_factors[dname] = (fp, fpp)
            return

        def phase(self):
            '''Perform phasing on the input data.'''

            self.check_hklin()
            self.check_hklout()

            self.start()

            # ASSERT: there is only one heavy atom in here
            atom = None

            self.input('xtal %s' % self._xname)
            for site in self._sites['sites']:
                if not atom:
                    atom = site['atom']
                else:
                    if site['atom'] != atom:
                        raise RuntimeError, 'more than one atom type'
                self.input('atom %s' % site['atom'])
                self.input('xyz %f %f %f' % tuple(site['fractional']))
                self.input('occupancy %f' % site['occupancy'])
                self.input('biso %f' % self._biso)

            for dname in self._input_datasets:
                self.input('dname %s' % dname)
                columns = 'column F+=F(+)_%s SF+=SIGF(+)_%s ' + \
                          'column F-=F(-)_%s SF-=SIGF(-)_%s'
                self.input(columns % (dname, dname, dname, dname))
                self.input('form %s FP=%f FPP=%f' % \
                           (atom,
                            self._input_form_factors[dname][0],
                            self._input_form_factors[dname][1]))

            # FIXME should this be refine??? test it out - used to be phase
            self.input('refine')

            self.close_wait()

            self.check_for_errors()
            self.check_ccp4_errors()

            # get useful stuff out here... like did it work???

            loggraphs = self.parse_ccp4_loggraph()


    return BP3Wrapper()

if __name__ == '__main__':

    # run a test

    if not os.path.join(os.environ['XIA2_ROOT'], 'lib') in sys.path:
        sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'lib'))
        
    from SubstructureLib import parse_pdb_sites_file, invert_hand

    if not os.environ.has_key('X2TD_ROOT'):
        raise RuntimeError, 'X2TD_ROOT not defined'

    hklin = os.path.join(os.environ['X2TD_ROOT'],
                         'Test', 'UnitTest', 'Wrappers', 'BP3',
                         '1VR5_13193_merged_free.mtz')

    hklout = os.path.join(os.getcwd(), '1VR5_13193_phased.mtz')

    sites = parse_pdb_sites_file(os.path.join(
        os.environ['X2TD_ROOT'],
        'Test', 'UnitTest', 'Wrappers', 'BP3',
        '1VR5_13193_fa_hyss_consensus_model.pdb'))

    bp3 = BP3()

    bp3.set_hklin(hklin)
    bp3.set_hklout(hklout)
    bp3.set_sites(sites)
    bp3.add_dataset('INFL', -11.0, 4.0)
    bp3.add_dataset('LREM', -2.5, 0.5)
    bp3.add_dataset('PEAK', -8.0, 6.0)
    bp3.set_biso(22.0)

    bp3.set_xname('13193')

    bp3.write_log_file('bp3.log')
    
    bp3.phase()

    # run again with the other hand, for good measure!

    sites_invert = invert_hand(sites)
    hklout_invert = os.path.join(os.getcwd(), '1VR5_13193_phased_inverted.mtz')

    bp3 = BP3()

    bp3.set_hklin(hklin)
    bp3.set_hklout(hklout_invert)
    bp3.set_sites(sites_invert)
    bp3.add_dataset('INFL', -11.0, 4.0)
    bp3.add_dataset('LREM', -2.5, 0.5)
    bp3.add_dataset('PEAK', -8.0, 6.0)
    bp3.set_biso(22.0)

    bp3.set_xname('13193')

    bp3.write_log_file('bp3_inverted.log')
    
    bp3.phase()
