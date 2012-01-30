#!/usr/bin/env python
# DM.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.


#
# 16th November 2006
#
# A wrapper for the CCP4 phase improvement program DM.
#
# FIXME 21/NOV/06 need to add the FreeR column if it is in the input
#                 data set. In practice, the input data from data
#                 reduction needs to be "cadded in" with the results
#                 of phasing prior to phase improvement.
#
# FIXME 21/NOV/06 need to consider cases where there may be some NCS
#                 (e.g. when the number of molecules in the ASU > 1)
#                 and switch on NCS averaging if this is the case.

import sys
import os

if not os.path.join(os.environ['XIA2CORE_ROOT'], 'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'], 'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])


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
            self.set_executable(os.path.join(
                os.environ.get('CBIN', ''), 'dm'))

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

            # FIXME these column labels should not be harded coded!

            self.input('labin FP=FPHASED SIGFP=SIGFPHASED FOMO=FOM ' +
                       'HLA=HLA HLB=HLB HLC=HLC HLD=HLD')
            self.input('labout PHIDM=PHIDM FOMDM=FOMDM')

            self.close_wait()

            self.check_for_errors()
            self.check_ccp4_errors()

            # get useful information out here...

            loggraphs = self.parse_ccp4_loggraph()

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
