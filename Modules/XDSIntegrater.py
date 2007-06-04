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
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

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

        # set a low resolution limit (which isn't really used...)
        self.set_integrater_low_resolution(40.0)
        
        # internal parameters to pass around
        self._integrate_parameters = { } 

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
        correct = _Correct()
        correct.set_working_directory(self.get_working_directory())

        correct.setup_from_image(self.get_image_name(
            self._intgr_wedge[0]))

        auto_logfiler(correct)
        
        return correct

    # now some real functions, which do useful things

    def _integrate_prepare(self):
        '''Prepare for integration - in XDS terms this may mean rerunning
        IDXREF to get the XPARM etc. DEFPIX is considered part of the full
        integration as it is resolution dependent.'''

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
            # set the indexer up as per the frameprocessor interface...
            # this would usually happen within the IndexerFactory.
            self.get_integrater_indexer().setup_from_image(
                self.get_image_name(
                self._intgr_wedge[0]))
            self.get_integrater_indexer().set_working_directory(
                self.get_working_directory())
            
            # now copy information from the old indexer to the new
            # one - lattice, cell, distance etc.

            self._intgr_indexer.set_indexer_input_cell(cell)
            self._intgr_indexer.set_indexer_input_lattice(lattice)
            self._intgr_indexer.set_distance(distance)
            self._intgr_indexer.set_beam(beam)

            # re-get the unit cell &c. and check that the indexing
            # worked correctly
            cell = self._intgr_indexer.get_indexer_cell()
            lattice = self._intgr_indexer.get_indexer_lattice()

        # copy the data across
        self._data_files = self._intgr_indexer.get_indexer_payload(
            'xds_files')
            
        return

    def _integrate(self):
        '''Actually do the integration - in XDS terms this will mean running
        DEFPIX and INTEGRATE to measure all the reflections.'''

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

        if self._intgr_reso_high > 0.0:
            defpix.set_resolution_high(self._intgr_reso_high)

        defpix.run()

        # and gather the result files
        for file in ['BKGPIX.pck',
                     'ABS.pck']:
            self._data_files[file] = defpix.get_output_data_file(file)

        integrate = self.Integrate()

        integrate.set_updates(self._integrate_parameters)

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
                     'GAIN.pck']:
            integrate.set_input_data_file(file, self._data_files[file])

        # use the refined parameters for integration?

        fixed_2401 = True
       
        if self._data_files.has_key('GXPARM.XDS') and fixed_2401:
            Chatter.write('Using globally refined parameters')
            integrate.set_input_data_file(
                'XPARM.XDS', self._data_files['GXPARM.XDS'])
            integrate.set_refined_xparm()
        else:
            integrate.set_input_data_file(
                'XPARM.XDS', self._data_files['XPARM.XDS'])

        integrate.run()

        self._integrate_parameters = integrate.get_updates()

        return

    def _integrate_finish(self):
        '''Finish off the integration by running correct.'''

        # then run correct..

        correct = self.Correct()

        correct.set_data_range(self._intgr_wedge[0],
                               self._intgr_wedge[1])
        
        if self._intgr_reso_high > 0.0:
            correct.set_resolution_high(self._intgr_reso_high)

        if self.get_integrater_spacegroup_number():
            correct.set_spacegroup_number(
                self.get_integrater_spacegroup_number())
            # FIXME bug 2406 - need to have the unit cell set as
            # well as the spacegroup...
            if not self._intgr_cell:
                raise RuntimeError, 'no unit cell to recycle'
            correct.set_cell(self._intgr_cell)

        if self.get_integrater_reindex_matrix():
            correct.set_reindex_matrix(
                r_to_rt(self.get_integrater_reindex_matrix_rt()))
        
        correct.run()

        # should get some interesting stuff from the XDS correct file
        # here, for instance the resolution range to use in integration
        # (which should be fed back if not fast) and so on...

        self._intgr_hklout = os.path.join(
            self.get_working_directory(),
            'XDS_ASCII.HKL')

        # look at the resolution limit...
        resolution = correct.get_result('resolution_estimate')

        if not self._intgr_reso_high and not Flags.get_quick():
            self.set_integrater_high_resolution(resolution)
            Chatter.write('Set resolution limit: %5.2f' % resolution)
        elif Flags.get_quick():
            # ok we are going quickly but we will want the resolution
            # limit later on, so just record it without using the
            # setter which will reset me!
            self._intgr_reso_high = resolution
            Chatter.write(
                'Set resolution limit: %5.2f (quick, so no rerun)' % \
                resolution)
            

        # FIXME perhaps I should also feedback the GXPARM file here??
        for file in ['GXPARM.XDS']:
            self._data_files[file] = correct.get_output_data_file(file)

        # record the postrefined cell parameters
        self._intgr_cell = correct.get_result('cell')
        self._intgr_n_ref = correct.get_result('n_ref')

        return self._intgr_hklout
            
        

if __name__ == '__main__':

    # run a demo test

    if not os.environ.has_key('XIA2_ROOT'):
        raise RuntimeError, 'XIA2_ROOT not defined'

    xi = XDSIntegrater()

    directory = os.path.join('/data', 'graeme', 'insulin', 'demo')

    xi.setup_from_image(os.path.join(directory, 'insulin_1_001.img'))


    xi.integrate()
