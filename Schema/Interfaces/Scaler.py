#!/usr/bin/env python
# Scaler.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# An interface for programs which do scaling - this will handle all of the
# input and output, delegating the actual implementation to a wrapper which
# implements this interface via inheritance.
# 
# This interface is designed to work with "high level" scaling, that
# is the case where all of the expertise about the scaling is delegated
# to the wrapper. 
# 
# The following cases need to be handled:
# 
# (1) multiple sweeps contributing to one wavelength of data (e.g.
#     1VR9 native data.)
# (2) multiple sweeps at different wavelengths for MAD data collection
#     (e.g. 1VR9 SeMet MAD data.)
#
# These cases need to be handled implicitly, which means that the collection
# order will have to be handled. A mechanism for separating out the data
# for different crystals will be needed, to allow the radiation damage
# handling stuff to do it's job.
#
# The overall data model will correspond to the CCP4 MTZ hierarchy, that
# is project/crystal/dataset. In this interface it is assumed that all
# data will correspond to a single project, since anything else is simply
# perverse!
# 
# Input data will take the form of handles to Integrater implementations, 
# which can provide the required data as and when it is asked for. At some
# point I will need to think about how to handle the issue that XSCALE does
# the best job of scaling data from XDS...
# 
# At least, I need to implement a mechanism for handling this. More effort
# is needed in the design of the Factories... Since this applies also for
# things like the Indexer in the xia2process implementation I should
# probably resolve this first.
# 
# Update 08/SEP/06
# ----------------
# 
# Factory for Integrater takes Indexer as argument. By analogy, a Scaler
# Factory will take one or more Integraters as input. These will then 
# allow the best scaler to be selected.
# 
# The scaling step should implicitly include scaling & reindexing to the 
# "standard" setting. This should raise an exception if the diferent sweeps
# have been integrated with different programs.
#
# In XModel terms, this will be available from:
# 
# XSweep - for characterization of a single sweep, looking for in sweep 
#          radiation damage, resolution limits & so on.
# XWavelength - for scaling together multiple passes which belong to the 
#               same wavelength, e.g. low and high resolution pass.
#               Also for looking for radiation damage.
# XCrystal - for scaling together all of the data measured for a given
#            crystal, e.g. multiwavelength, multi passes as for XWavelength,
#            looking for multi-set radiation damage. This is assumed to
#            provide the final reflection output.
#
# Note well: The XCrystal level scaling will also be responsible for producing
# the specialised data sets, e.g. for phasing & refinement. The former should
# optimise the "signal", while the latter should optimise the "resolution"
# and "quality" (this is to be assessed, for the moment think in terms of
# limiting radiation damage.)
#
# This will be most complicated, and will depend to a critical extent on the
# way in which the scaling is managed.
# 
# The scaling process should allow the following to be obtained:
# 
# merged reflections for phasing
# merged reflections for refinement
# unmerged reflections for phasing
# unmerged reflections for refinement
# r_merge
# r_pim
# resolution
# "anomalous signal/difference"
# "anomalous dispersion"
# twinning information (implies that Truncate will be included)
# 
# probably other things but they will have to wait.
# 
# As input, the following will be appropriate:
# 
# A managed list of Integrater implementations. These should be grouped
# into wavelengths &c. All must be integrated with a compatible unit cell.
# A resolution limit.
# Anomalous true, false.
# "standard" unit cell (optional)
# 
# Output formats:
# 
# The output will be available as MTZ, providing that the proper mtz hierarchy
# is available (need to make sure there is a way of providing this as input.) 
# Scalepack format files will be provided for unmerged. These will be named
# according to something which matches the MTZ hierarchy, e.g.
# crystal_dataset.sca.
# 
# Refinement data will be merged native.
# 
# Organisation 21/SEP/06
# 
# Ok, this is reasonably complicated, because I don't want to tie this 
# directly into the .xinfo hierarchy, so I will need to be able to express
# the input structure of the integraters in some relatively clever way.
# 
# In here, think in terms of XDS/XSCALE & Mosflm->Scala. For Mosflm->Scala
# this will need to:
# 
# (1) check that the unit cells are compatible.
# (2) sort the reflection files together.
# (3) organise the batches, runs - these need to be put in as 
#     information about the project/crystal/dataset which correspond
#     to each run.
# (4) actually perform the scaling.
# (5) after scaling will have multiple reflection files - these need to have
#     the unit cells "standardised" and then be merged again via CAD.
#     Could alternatively just keep them as separate reflection files, just
#     record the fact in the .xinfo output.
# 
# From a scala example (documented in Ph.D./Chapter 4)
# 
# run 1 batch N to M
# name run 1 project foo crystal bar dataset peak
# base dataset [define remote here] # defines what the dispersive differences
#                                   # are relative to in the analysis
#
# This means that the project, crystal, dataset information needs to come
# in, along with the sweeps (reflection files) and the epochs of data
# collection for the radiation damage analysis. Latter may be NULL, in which 
# case process the reflection files in alphabetical order.
# 
# Implementation
# --------------
# 
# Ok, in terms of the implementation this could be more complicated. This
# is not going to be particularly easy to implement by a single program
# wrapper, so perhaps I will have to actually implement CCP4Scaler, 
# XDSScaler &c., which will be a composite class which performs the operation,
# using wrapper classes for the different programs...
# 
# FIXED 02/NOV/06 need to move this over to the same framework as in 
#                 Integrater - that is, prepare_scale, do_scale both until
#                 happiness has arrived - this could be complicated but 
#                 is really the only way to structure it...
# 
#                 Will also allow for a certain amount of iteration, but 
#                 not repetition of e.g. sorting, reindexing (unless
#                 necessary.)
#
# FIXME 21/NOV/06 add information about spacegroups. This should perhaps
#                 come from an analysis of the systematic absences, but 
#                 may just be "all spacegroups in this point group."
#                 For instance, get_all_likely_spacegroups(),
#                 get_likely_spacegroup(), get_all_less_likely_spacegroups().
#                 Also want to be able to return some information about
#                 the resolution of the sample and also the rough B factor.
#                 Method names will need some thinking about! Also want
#                 the unit cell information.
# 
# FIXME 28/NOV/06 also need to plumb this back to the Indexer(s) so that 
#                 they can discuss what the correct lattice.
#
# FIXME 28/NOV/06 should use all of the data for all sweeps within one 
#                 crystal for deciding on the correct pointgroup (e.g.
#                 some kind of composite decision) - or - should at least
#                 verify that all solutions agree (raise an exception if
#                 not?)
#
# FIXME 07/FEB/07 need to be able to call scale() without checking status
#                 and also provide for a NULL Scaler implementation.
#                 This change could have a significant impact on the 
#                 workflow...
#
# FIXME 12/FEB/07 need to add format translation services, so in the event
#                 that an implementation only partially populates the
#                 reflection file dictionary the rest can be generated if
#                 they are asked for... this could be complex.
# 
# FIXME 28/JUN/07 need to be able to take in a reference reflection file
#                 in here too to provide the correct setting, spacegroup
#                 and FreeR column. c/f changes to XCrystal.
# 

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from lib.Guff import inherits_from

from Handlers.Streams import Chatter, Debug

# file conversion (and merging) jiffies

from Modules.Scalepack2Mtz import Scalepack2Mtz
from Modules.Mtz2Scalepack import Mtz2Scalepack

class Scaler:
    '''An interface to present scaling functionality in a similar way to the
    integrater interface.'''

    def __init__(self):
        # set up a framework for storing all of the input information...
        # this should really only consist of integraters...

        # key this by the epoch, if available, else will need to
        # do something different.
        self._scalr_integraters = { }

        # integraters have the following methods for pulling interesting
        # information out:
        #
        # get_integrater_project_info() - pname, xname, dname
        # get_integrater_epoch() - measurement of first frame

        self.scaler_reset()

        self._scalr_reference_reflection_file = None
        
        # places to hold the output

        # this should be a dictionary keyed by datset / format, or
        # format / dataset
        self._scalr_scaled_reflection_files = None

        # this needs to be a dictionary keyed by dataset etc, e.g.
        # key = pname, xname, dname
        self._scalr_statistics = None

        # and also the following keys:
        self._scalr_statistics_keys = [
            'High resolution limit', 'Low resolution limit',
            'Completeness', 'Multiplicity',
            'I/sigma', 'Rmerge',
            'Rmeas(I)', 'Rmeas(I+/-)',
            'Rpim(I)', 'Rpim(I+/-)',
            'Wilson B factor', 'Partial bias',
            'Anomalous completeness', 'Anomalous multiplicity',
            'Anomalous correlation', 'Anomalous slope',
            'Total observations', 'Total unique']
        
        # information for returning "interesting facts" about the data
        self._scalr_highest_resolution = 0.0
        self._scalr_cell = None
        self._scalr_likely_spacegroups = []
        self._scalr_unlikely_spacegroups = []

        # do we want anomalous pairs separating?
        self._scalr_anomalous = False

        # admin junk
        self._working_directory = os.getcwd()
        self._scalr_pname = None
        self._scalr_xname = None

        return

    def _scale_prepare(self):
        raise RuntimeError, 'overload me'

    def _scale(self):
        raise RuntimeError, 'overload me'

    def _scale_finish(self):
        pass

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def set_scaler_project_info(self, pname, xname):
        '''Set the project and crystal this scaler is working with.'''

        self._scalr_pname = pname
        self._scalr_xname = xname

        return

    def get_scaler_project_info(self):
        '''Get the scaler project and crystal.'''

        return self._scalr_pname, self._scalr_xname

    def set_scaler_reference_reflection_file(self, reference_reflection_file):
        self._scalr_reference_reflection_file = reference_reflection_file
        return

    def get_scaler_reference_reflection_file(self):
        return self._scalr_reference_reflection_file

    def set_scaler_prepare_done(self, done = True):
        self._scalr_prepare_done = done
        return
        
    def set_scaler_done(self, done = True):
        self._scalr_done = done
        return

    def set_scaler_finish_done(self, done = True):
        self._scalr_finish_done = done
        return

    def set_scaler_anomalous(self, anomalous):
        self._scalr_anomalous = anomalous
        return

    def get_scaler_anomalous(self):
        return self._scalr_anomalous

    def scaler_reset(self):

        Debug.write('Scaler reset')
        
        self._scalr_done = False
        self._scalr_prepare_done = False
        self._scalr_finish_done = False
        self._scalr_result = None
        return

    # getters of the status - note how the gets cascade to ensure that
    # everything is up-to-date...

    def get_scaler_prepare_done(self):

        # this should perhaps iterate over all of the integraters
        # as well??? FIXME need to make a proper decision about this...
        
        return self._scalr_prepare_done

    def get_scaler_done(self):

        if not self.get_scaler_prepare_done():
            Debug.write('Resetting Scaler done as prepare not done')
            self.set_scaler_done(False)
        
        return self._scalr_done

    def get_scaler_finish_done(self):

        if not self.get_scaler_done():
            Debug.write(
                'Resetting scaler finish done as scaling not done')
            self.set_scaler_finish_done(False)
        
        return self._scalr_finish_done

    def add_scaler_integrater(self, integrater):
        '''Add an integrater to this scaler, to provide the input.'''

        # check that this integrater inherits from the Integrater
        # interface, and also that all integraters come from the
        # same source, e.g. the same implementation of Integrater.

        # FIXME this needs doing

        # check that the lattice &c. matches any existing integraters
        # already in the system.

        # FIXME this needs doing

        # add this to the list.

        # FIXME 27/OCT/06 sometimes the epoch for all frames will be
        # zero - you have been warned!! perhaps in here there should be
        # something derived from the image name - this would mean that
        # then it is in alphabetical order, instead...

        epoch = integrater.get_integrater_epoch()

        # this is ok if you have SAD data - e.g. the epoch is not
        # important - so check also that there are other integraters
        # already stored...

        if epoch == 0 and self._scalr_integraters:
            raise RuntimeError, 'multi-sweep integrater has epoch 0'

        if epoch in self._scalr_integraters.keys():
            raise RuntimeError, 'integrater with epoch %d already exists' % \
                  epoch

        self._scalr_integraters[epoch] = integrater

        # reset the scaler.
        self.scaler_reset()

        return

    def scale(self):
        '''Actually perform the scaling - this is delegated to the
        implementation.'''
        
        if self._scalr_integraters == { }:
            raise RuntimeError, \
                  'no Integrater implementations assigned for scaling'

        # FIXME 02/NOV/06 move this into a "while" loop controlled by the
        # done flags, and also add a prepare step into the system as well,
        # to enable things like sorting and friends to be considered
        # separately to the actual scaling...

        # FIXME these should be reset by the input - calls to the scale
        # method should do nothing if the scaling has been done already

        # 07/FEB/07 no longer assume that the scaling needs to be repeated...
        # self._scalr_done = False
        # self._scalr_prepare_done = False

        while not self.get_scaler_finish_done():
            while not self.get_scaler_done():
                while not self.get_scaler_prepare_done():

                    Chatter.write('Preparing to do some scaling...')
                 
                    self._scalr_prepare_done = True
                    self._scale_prepare()

                Chatter.write('Doing some scaling...')
            
                self._scalr_done = True
                self._scalr_result = self._scale()
            
            Chatter.write('Finishing the scaling...')
            self._scalr_finish_done = True
            self._scale_finish()

        # FIXME this result payload probably shouldn't exist...
        return self._scalr_result

    def get_scaled_reflections(self, format):
        '''Get a specific format of scaled reflection files. This may
        trigger transmogrification of files.'''

        if not format in ['mtz', 'sca', 'sca_unmerged']:
            raise RuntimeError, 'format %s unknown' % format

        self.scale()
        
        if format in self._scalr_scaled_reflection_files.keys():
            return self._scalr_scaled_reflection_files[format]

        # specific code to handle generation cases

        if format == 'sca_unmerged':
            raise RuntimeError, 'cannot generate unmerged reflections'

        if format == 'mtz':
            # generate and return an mtz file - ideally this will be from
            # merged reflections, though unmerged will do - though this
            # will need the unit cell information etc. Aha! this is
            # available from this interface...

            cell = self.get_scaler_cell()
            spacegroup = self.get_scaler_likely_spacegroups()[0]

            wavelengths = self._scalr_scaled_reflection_files['sca'].keys()
            project, crystal = self.get_scaler_project_info()

            s2m = Scalepack2Mtz()

            for w in wavelengths:
                s2m.add_hklin(w, self._scalr_scaled_reflection_files[
                    'sca'][w])
            s2m.set_cell(cell)
            s2m.set_spacegroup(spacegroup)
            s2m.set_project_info(project, crystal)

            self._scalr_scaled_reflection_files['mtz'] = s2m.convert()
            return self._scalr_scaled_reflection_files['mtz']

        if format == 'sca':
            # generate merged scalepack format reflections from the mtz
            # format

            m2s = Mtz2Scalepack()

            m2s.set_hklin(self._scalr_scaled_reflection_files['mtz'])
            self._scalr_scaled_reflection_files['sca'] = m2s.convert()
            return self._scalr_scaled_reflection_files['sca']

        raise RuntimeError, 'cannot possibly reach this point'
                

    def get_scaled_merged_reflections(self):
        '''Return the reflection files and so on.'''

        self.scale()
        return self._scalr_scaled_reflection_files

    def get_scaler_statistics(self):
        '''Return the overall scaling statistics.'''

        self.scale()
        return self._scalr_statistics
    
    def get_scaler_cell(self):
        '''Return the final unit cell from scaling.'''

        self.scale()
        return self._scalr_cell

    def get_scaler_likely_spacegroups(self):
        '''Return a list of likely spacegroups - you should try using
        the first in this list first.'''

        self.scale()
        return self._scalr_likely_spacegroups

    def get_scaler_unlikely_spacegroups(self):
        '''Return a list of unlikely spacegroups - you should try using
        the likely ones first. These are spacegroups in the correct
        pointgroup but with systematic absences which dont match up.'''

        self.scale()
        return self._scalr_unlikely_spacegroups

    def get_scaler_highest_resolution(self):
        '''Get the highest resolution achieved by the crystal.'''

        self.scale()
        return self._scalr_highest_resolution


        
