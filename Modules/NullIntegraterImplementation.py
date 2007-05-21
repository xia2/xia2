#!/usr/bin/env python
# NullIntegraterImplementation.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 30/OCT/06
#
# An empty integrater - this presents the Integrater interface but does 
# nothing, making it ideal for when you have the integrated intensities
# passed in already. This will simply return the intensities.
#
# FIXME 08/NOV/06 need to be able to limit in both batches and in resolution.
#                 Therefore need to also include the Rebatch wrapper...
# 

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Schema.Interfaces.Integrater import Integrater
from Schema.Interfaces.FrameProcessor import FrameProcessor
from Wrappers.CCP4.Mtzutils import Mtzutils
from Wrappers.CCP4.Reindex import Reindex
from Handlers.Streams import Chatter

from lib.Guff import auto_logfiler

class NullIntegrater(FrameProcessor,
                     Integrater):
    '''A null class to present the integrater interface.'''

    def __init__(self, integrated_reflection_file):
        '''Create a null integrater pointing at this reflection file.'''

        FrameProcessor.__init__(self)
        Integrater.__init__(self)

        self._intgr_hklout_orig = integrated_reflection_file
        self._intgr_hklout = None

        self._working_directory = os.getcwd()

        # also need to be able to set the epoch of myself
        # FIXME - this is also generally true... need to add
        # this to the .xinfo file...

        return

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        pass

    def get_working_directory(self):
        return self._working_directory

    # overload these methods from the interface to provide a workaround
    def get_integrater_prepare_done(self):
        return self._intgr_prepare_done

    def get_integrater_done(self):
        return self._intgr_done    

    # "real" methods

    def _integrate_prepare(self):
        '''Do nothing!'''
        pass

    def _integrate(self):
        '''Do nothing - except return a pointer to the reflections...'''

        # FIXME 08/NUV/06 this should probably return a reflection file
        # which has been resolution limited appropriately...

        # run Mtzutils if we have defined a resolution limit, else just
        # return a pointer to the original reflection file...

        if not self._intgr_reso_high:
            self._intgr_hklout = self._intgr_hklout_orig
            
        else:
            # construct a name for hklout...
            hklout = os.path.join(self.get_working_directory(),
                                  os.path.split(self._intgr_hklout_orig)[-1])

            if hklout == self._intgr_hklout_orig:
                raise RuntimeError, 'cannot have input reflections in ' + \
                      'working directory'
            
            # run mtzutils

            mu = Mtzutils()

            mu.set_working_directory(self.get_working_directory())

            auto_logfiler(mu)

            Chatter.write('NULL integrater resolution limited to %5.2f' %
                          self._intgr_reso_high)
            Chatter.write('=> %s' % hklout)

            mu.set_hklin(self._intgr_hklout_orig)
            mu.set_hklout(hklout)
            mu.set_resolution(self._intgr_reso_high)

            mu.edit()

            self._intgr_hklout = hklout

        return self._intgr_hklout

    def _integrate_finish(self):
        '''Finish the integration - if necessary performing reindexing
        based on the pointgroup and the reindexing operator.'''
        
        # check if we need to perform any reindexing...
        
        if self._intgr_reindex_operator is None:
            return self._intgr_hklout

        # if the current indexer spacegroup is equal to the
        # given spacegroup and the reindexing operation is
        # identity then the result is ... no!
        
        if self._intgr_reindex_operator == 'h,k,l' and \
               self._intgr_spacegroup_number == 0:
            return self._intgr_hklout

        if self._intgr_reindex_operator == 'h,k,l' and \
               self._intgr_spacegroup_number == lattice_to_spacegroup(
            self.get_integrater_indexer().get_indexer_lattice()):
            Chatter.write('No reindexing as settings are correct.')
            return self._intgr_hklout  

        Chatter.write('Reindexing required: Spacegroup %d (%s)' % \
                      (self._intgr_spacegroup_number,
                       self._intgr_reindex_operator))

        hklin = self._intgr_hklout
        reindex = Reindex()
        reindex.set_working_directory(self.get_working_directory())
        auto_logfiler(reindex)
        
        reindex.set_operator(self._intgr_reindex_operator())
        
        if self._intgr_spacegroup_number:
            reindex.set_spacegroup(self._intgr_spacegroup_number)
            
        hklout = '%s_reindex.mtz' % hklin[:-4]

        reindex.set_hklin(hklin)
        reindex.set_hklout(hklout)
        
        reindex.reindex()
        
        self._intgr_hklout = hklout
        return hklout


    
