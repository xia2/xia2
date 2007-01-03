#!/usr/bin/env python
# XDSIntegrater.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 14th December 2006
# 
# An implementation of the Integrater interface using XDS. This depends on the
# XDS wrappers to actually implement the functionality.
#
# This will "wrap" the XDS programs DEFPIX and INTEGRATE - CORRECT is
# considered to be a part of the scaling - see XDSScaler.py.
#
# 02/JAN/07 FIXME need to ensure that the indexing is repeated if necessary.

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# wrappers for programs that this needs

from Wrappers.XDS.XDSDefpix import XDSDefpix as _Defpix
from Wrappers.XDS.XDSIntegrate import XDSIntegrate as _Integrate

# helper functions

from Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from Wrappers.XDS.XDS import beam_centre_xds_to_mosflm

# interfaces that this must implement to be an integrater

from Schema.Interfaces.Integrater import Integrater
from Schema.Interfaces.FrameProcessor import FrameProcessor

# indexing functionality if not already provided

from Modules.XDSIndexer import XDSIndexer

# odds and sods that are needed

from lib.Guff import auto_logfiler
from Handlers.Streams import Chatter

class XDSIntegrater(FrameProcessor,
                    Integrater):
    '''A class to implement the Integrater interface using *only* XDS
    programs.'''

    def __init__(self):

        # set up the inherited objects
        
        FrameProcessor.__init__(self)
        Integrater.__init__(self)

        # check that the programs exist - this will raise an exception if
        # they do not...

        integrate = _Integrate()

        # admin junk
        self._working_directory = os.getcwd()

        # place to store working data
        self._data_files = { }

        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    # factory functions

    def Defpix(self):
        defpix = _Defpix()
        defpix.set_working_directory(self.get_working_directory())

        defpix.setup_from_image(self.get_image_name(
            self._intgr_wedge[0]))

        auto_logfiler(defpix)

        return defpix

    def Integrate(self):
        integrate = _Integrate()
        integrate.set_working_directory(self.get_working_directory())

        integrate.setup_from_image(self.get_image_name(
            self._intgr_wedge[0]))

        auto_logfiler(integrate)

        return integrate

    # now some real functions, which do useful things

    def _integrate_prepare(self):
        '''Prepare for integration - in XDS terms this will mean running
        DEFPIX to analyse the background etc.'''

        # decide what images we are going to process, if not already
        # specified

        if not self._intgr_indexer:
            self.set_integrater_indexer(XDSIndexer())

        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images),
                                      max(images))

        first_image_in_wedge = self.get_image_name(self._intgr_wedge[0])

        defpix = self.Defpix()

        defpix.set_data_range(self._intgr_wedge[0],
                              self._intgr_wedge[1])

        defpix.run()

        return

    def _integrate(self):
        '''Actually do the integration - in XDS terms this will mean running
        INTEGRATE to measure all the reflections.'''

        integrate = self.Integrate()

        # decide what images we are going to process, if not already
        # specified

        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images),
                                      max(images))

        first_image_in_wedge = self.get_image_name(self._intgr_wedge[0])

        integrate.set_data_range(self._intgr_wedge[0],
                                 self._intgr_wedge[1])

        integrate.run()

        return

    
