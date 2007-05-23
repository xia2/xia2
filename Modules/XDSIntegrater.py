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
from Wrappers.XDS.XDSCorrect import XDSCorrect as _Correct

# helper functions

from Wrappers.XDS.XDS import beam_centre_mosflm_to_xds
from Wrappers.XDS.XDS import beam_centre_xds_to_mosflm
from Experts.SymmetryExpert import r_to_rt

# interfaces that this must implement to be an integrater

from Schema.Interfaces.Integrater import Integrater
from Schema.Interfaces.FrameProcessor import FrameProcessor

# indexing functionality if not already provided - even if it is
# we still need to reindex with XDS.

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

    def Correct(self):
        integrate = _Correct()
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

        if not self._intgr_wedge:
            images = self.get_matching_images()
            self.set_integrater_wedge(min(images),
                                      max(images))

        if not self._intgr_indexer:
            self.set_integrater_indexer(XDSIndexer())

            self._intgr_indexer.set_working_directory(
                self.get_working_directory())
            
            self._intgr_indexer.setup_from_image(self.get_image_name(
                self._intgr_wedge[0]))

            # this needs to be set up from the contents of the
            # Integrater frame processer - wavelength &c.

            if self.get_beam():
                self._intgr_indexer.set_beam(self.get_beam())

            if self.get_distance():
                self._intgr_indexer.set_distance(self.get_distance())

            if self.get_wavelength():
                self._intgr_indexer.set_wavelength(
                    self.get_wavelength())

        # get the unit cell from this indexer to initiate processing
        # if it is new... and also copy out all of the information for
        # the XDS indexer if not...

        cell = self._intgr_indexer.get_indexer_cell()
        lattice = self._intgr_indexer.get_indexer_lattice()
        beam = self._intgr_indexer.get_indexer_beam()
        distance = self._intgr_indexer.get_indexer_distance()

        # check that the indexer is an XDS indexer - if not then
        # create one...

        if not self._intgr_indexer.get_indexer_payload('xds_files'):
            self.set_integrater_indexer(XDSIndexer())
            
            # now copy information from the old indexer to the new
            # one - lattice, cell, distance etc.

            self._intgr_indexer.set_indexer_input_cell(cell)
            self._intgr_indexer.set_indexer_input_latice(lattice)
            self._intgr_indexer.set_distance(distance)
            self._intgr_indexer.set_beam(beam)

            # re-get the unit cell &c. and check that the indexing
            # worked correctly
            cell = self._intgr_indexer.get_indexer_cell()
            lattice = self._indgr_indexer.get_indexer_lattice()

        # copy the data across
        self._data_files = self._intgr_indexer.get_indexer_payload(
            'xds_files')
            
        first_image_in_wedge = self.get_image_name(self._intgr_wedge[0])

        defpix = self.Defpix()

        # pass in the correct data

        for file in ['X-CORRECTIONS.pck',
                     'Y-CORRECTIONS.pck',
                     'BKGINIT.pck',
                     'XPARM.XDS']:
            defpix.set_input_data_file(file, self._data_files[file])

        defpix.set_data_range(self._intgr_wedge[0],
                              self._intgr_wedge[1])

        defpix.run()

        # and gather the result files
        for file in ['BKGPIX.pck',
                     'ABS.pck']:
            self._data_files[file] = defpix.get_output_data_file(file)
        

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

        for file in ['X-CORRECTIONS.pck',
                     'Y-CORRECTIONS.pck',
                     'BLANK.pck',
                     'BKGPIX.pck',
                     'GAIN.pck',
                     'XPARM.XDS']:
            integrate.set_input_data_file(file, self._data_files[file])

        integrate.run()

        return

    def _integrate_finish(self):
        '''Finish off the integration by running correct.'''

        # then run correct..

        correct = self.Correct()

        correct.set_data_range(self._intgr_wedge[0],
                               self._intgr_wedge[1])
        
        if self.get_integrater_spacegroup_number():
            correct.set_spacegroup_number(
                self.get_integrater_spacegroup_number())

        if self.get_integrater_reindex_matrix():
            correct.set_reindex_matrix(
                r_to_rt(self.get_integrater_reindex_matrix_rt()))
        
        correct.run()

        # should get some interesting stuff from the XDS correct file
        # here, for instance the resolution range to use in integration
        # (which should be fed back if not fast) and so on...
        

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    xi = XDSIntegrater()

    directory = os.path.join('/data', 'graeme', 'insulin', 'demo')

    xi.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))


    xi.integrate()
