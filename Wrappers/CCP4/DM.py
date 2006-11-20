#!/usr/bin/env python
# DM.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
#
# 16th November 2006
#  
# A wrapper for the CCP4 phase improvement program DM.
# 
# 
# 
# 

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])


if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def DM(DriverType = None):
    '''A factory for DMWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class DMWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for DM, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('dm')
            
            self._solvent = 0.0

            # FIXME this needs to be more sophisticated as it
            # will depend on the program which has done the phasing!

            return
        
        def set_solvent(self, solvent):
            self._solvent = solvent
            return

        def improve_phases(self):
            '''Run dm to improve phases.'''

            self.check_hklin()
            self.check_hklout()

            self.start()

            self.input('solc %f' % self._solvent)
            self.input('mode solv hist mult')
            self.input('ncyc auto')
            self.input('scheme all')
            self.input('labin FP=FPHASED SIGFP=SIGFPHASED FOMO=FOM ' +
                       'HLA=HLA HLB=HLB HLC=HLC HLD=HLD')
            self.input('labout PHIDM=PHIDM FOMDM=FOMDM')

            self.close()

            while True:

                line = self.output()

                if not line:
                    break

                print line[:-1]

            self.check_for_errors()
            self.check_ccp4_errors()

            # get useful information out here...

            return
        
    return DMWrapper()

if __name__ == '__main__':

    # then run a test - based on the bp3 wrapper output

    dm = DM()

    dm.set_hklin('1VR5_13193_phased.mtz')
    dm.set_hklout('1VR5_13193_phased_improved.mtz')
    dm.set_solvent(0.608)

    dm.write_log_file('dm.log')

    dm.improve_phases()

    # also do the alternative hand

    dm = DM()

    dm.set_hklin('1VR5_13193_phased_inverted.mtz')
    dm.set_hklout('1VR5_13193_phased_inverted_improved.mtz')
    dm.set_solvent(0.608)

    dm.write_log_file('dm_inverted.log')

    dm.improve_phases()

    
