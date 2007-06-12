#!/usr/bin/env python
# Reindex.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 5th June 2006
# 
# A wrapper for the CCP4 program reindex.
# 
# Provides:
# 
# Reindexing functionality for MTZ formatted reflection files.
# 

import os
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                             'Python'))

from Driver.DriverFactory import DriverFactory
from Decorators.DecoratorFactory import DecoratorFactory

def Reindex(DriverType = None):
    '''A factory for ReindexWrapper classes.'''

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, 'ccp4')

    class ReindexWrapper(CCP4DriverInstance.__class__):
        '''A wrapper for Reindex, using the CCP4-ified Driver.'''

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            self.set_executable('reindex')

            # reindex specific things
            self._spacegroup = None

            # this should be of the form e.g. k, l, h
            self._operator = None

            # results
            self._cell = None

        def set_spacegroup(self, spacegroup):
            '''Set the spacegroup to reindex the reflections to.'''

            self._spacegroup = spacegroup
            return

        def set_operator(self, operator):
            '''Set the reindexing operator for mapping from in to out.'''

            self._operator = operator
            return

        def get_cell(self):
            return self._cell

        def check_reindex_errors(self):
            '''Check the standard output for standard reindex errors.'''

            pass

        def reindex(self):
            '''Actually perform the reindexing.'''

            self.check_hklin()
            self.check_hklout()

            if not self._spacegroup and not self._operator:
                raise RuntimeError, 'reindex requires spacegroup or operator'

            self.start()

            if self._spacegroup:
                # this will need quoting
                self.input('symmetry \'%s\'' % self._spacegroup)

            if self._operator:
                # likewise
                self.input('reindex \'%s\'' % self._operator)

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_reindex_errors()

            except RuntimeError, e:
                try:
                    os.remove(self.get_hklout())
                except:
                    pass

                raise e

            for o in self.get_all_output():
                if 'New unit cell determined from reindexing:' in o:
                    self._cell = map(float, o.split()[-6:])

            return self.get_ccp4_status()

    return ReindexWrapper()

if __name__ == '__main__':
    # run some tests

    import os

    if not os.environ.has_key('XIA2CORE_ROOT'):
        raise RuntimeError, 'XIA2CORE_ROOT not defined'

    dpa = os.environ['XIA2_ROOT']

    hklin = os.path.join(dpa,
                         'Data', 'Test', 'Mtz', '12287_1_E1_1_10.mtz')

    r = Reindex()
    r.set_hklin(hklin)
    r.set_hklout('null.mtz')

    r.set_operator('h,k,l')
    r.set_spacegroup('P 4 2 2')

    print r.reindex()

    
