#!/usr/bin/env python
# XDSScaler.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 2nd January 2007
#
# This will provide the Scaler interface using XDS, pointless & CCP4 programs.
# This will run XSCALE, and feed back to the XDSIntegrater and also run a
# few other jiffys.
#
# Process (based on CCP4 Scaler)
# 
# _scale_prepare:
# 
# gather sweep information
# [check integraters are xds]
# check sweep information
# generate reference set: pointless -> sort -> quick scale
# reindex all data to reference: pointless -> eliminate lattices-> pointless
# verify pointgroups
# ?return if lattice in integration too high?
# reindex, rebatch
# sort
# pointless (spacegroup)
#
# _scale:
# 
# decide resolution limits / wavelength
# ?return to integration?
# refine parameters of scaling
# record best resolution limit
# do scaling
# truncate
# standardise unit cell
# update all reflection files
# cad together 
# add freer flags
# 
# In XDS terms this will be a little different. CORRECT provides GXPARM.XDS
# which could be recycled. A pointgroup determination routine will be needed.
# XDS reindexing needs to be sussed, as well as getting comparative R factors
# - how easy is this?

import os
import sys
import math
import shutil
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.Scaler import Scaler

# other tools that this will need
from Modules.Scaler.XDSScalerHelpers import XDSScalerHelper

# program wrappers that we will need

from Wrappers.XDS.XScaleR import XScaleR as _XScale
from Wrappers.XDS.Cellparm import Cellparm as _Cellparm
from Modules.TTT import ttt

from Wrappers.CCP4.CCP4Factory import CCP4Factory

# random odds and sods - the resolution estimate should be somewhere better
from lib.bits import auto_logfiler, transpose_loggraph, is_mtz_file
from lib.bits import nifty_power_of_ten
from lib.SymmetryLib import lattices_in_order
from Handlers.Citations import Citations
from Handlers.Syminfo import Syminfo
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Files import FileHandler
from Experts.SymmetryExpert import r_to_rt, rt_to_r, compose_symops
from Experts.SymmetryExpert import symop_to_mat, compose_matrices_r

# stuff I have nicked from the CCP4 Scaler implementation
from CCP4ScalerHelpers import _resolution_estimate
from Modules.CCP4InterRadiationDamageDetector import \
     CCP4InterRadiationDamageDetector
from Experts.ResolutionExperts import determine_scaled_resolution
from Modules.DoseAccumulate import accumulate

# new resolution limit code
from Toolkit.Merger import merger

# newly implemented CCTBX powered functions to replace xia2 binaries
from Modules.Scaler.add_dose_time_to_mtz import add_dose_time_to_mtz
from Modules.Scaler.compute_average_unit_cell import compute_average_unit_cell

class XDSScalerR(Scaler):
    '''An implementation of the xia2 Scaler interface implemented with
    xds and xscale, possibly with some help from a couple of CCP4
    programs like pointless and combat.'''

    def __init__(self):
        Scaler.__init__(self)

        self._sweep_information = { }

        self._common_pname = None
        self._common_xname = None

        self._reference = None

        # spacegroup and unit cell information - these will be
        # derived from an average of all of the sweeps which are
        # passed in
        
        self._spacegroup = None
        self._factory = CCP4Factory()

        # junk which may prove to be useful...
        self._reindexed_cell = None

        self._chef_analysis_groups = { }
        self._chef_analysis_times = { }
        self._chef_analysis_resolutions = { }

        self._resolution_limits = { }
        self._user_resolution_limits = { }

        # scaling correction choices - may be set one on the command line...

        if Flags.get_scale_model():
            self._scalr_correct_absorption = Flags.get_scale_model_absorption()
            self._scalr_correct_modulation = Flags.get_scale_model_modulation()
            self._scalr_correct_decay = Flags.get_scale_model_decay()
            
            self._scalr_corrections = True

        else:

            self._scalr_correct_decay = True
            self._scalr_correct_modulation = True
            self._scalr_correct_absorption = True
            self._scalr_corrections = True

        return    

    # This is overloaded from the Scaler interface...
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        return

    # program factory - this will provide configured wrappers
    # for the programs we need...

    def XScale(self):
        '''Create a Xscale wrapper from _Xscale - set the working directory
        and log file stuff as a part of this...'''

        # N.B. in here if the best scaling model has been applied, need
        # to apply it as part of the constructor, else just give back the
        # default "apply all corrections" XSCALE...
        
        xscale = _XScale()

        if self._scalr_corrections:
            xscale.set_correct_decay(self._scalr_correct_decay)
            xscale.set_correct_absorption(self._scalr_correct_absorption)
            xscale.set_correct_modulation(self._scalr_correct_modulation)
            
        xscale.set_working_directory(self.get_working_directory())
        auto_logfiler(xscale)
        return xscale

    def Cellparm(self):
        '''Create a Cellparm wrapper from _Cellparm - set the working directory
        and log file stuff as a part of this...'''
        cellparm = _Cellparm()
        cellparm.set_working_directory(self.get_working_directory())
        auto_logfiler(cellparm)
        return cellparm

    def _pointless_indexer_jiffy(self, hklin, indexer):
        '''A jiffy to centralise the interactions between pointless
        (in the blue corner) and the Indexer, in the red corner.'''

        # check to see if HKLIN is MTZ format, and if not, render it
        # so! no need - now pointless will accept input in XDS format.

        need_to_return = False

        pointless = self._factory.Pointless()

        if is_mtz_file(hklin):
            pointless.set_hklin(hklin)
        else:
            pointless.set_xdsin(hklin)
            
        pointless.decide_pointgroup()
        
        if indexer:
            rerun_pointless = False

            possible = pointless.get_possible_lattices()

            correct_lattice = None

            Debug.write('Possible lattices (pointless):')
            lattices = ''
            for lattice in possible:
                lattices += '%s ' % lattice
            Debug.write(lattices)

            for lattice in possible:
                state = indexer.set_indexer_asserted_lattice(lattice)
                if state == 'correct':
                            
                    Debug.write(
                        'Agreed lattice %s' % lattice)
                    correct_lattice = lattice
                    
                    break
                
                elif state == 'impossible':
                    Debug.write(
                        'Rejected lattice %s' % lattice)
                    
                    rerun_pointless = True
                    
                    continue
                
                elif state == 'possible':
                    Debug.write(
                        'Accepted lattice %s ...' % lattice)
                    Debug.write(
                        '... will reprocess accordingly')
                    
                    need_to_return = True
                    
                    correct_lattice = lattice
                    
                    break

            if correct_lattice == None:
                # this is an odd turn of events which may have been brought
                # about by the user assigning a lower spacegroup than is
                # true, which will give it a negative Z score but it may
                # stull be "true".

                correct_lattice = indexer.get_indexer_lattice()
                rerun_pointless = True
                    
                Debug.write(
                    'No solution found: assuming lattice from indexer')
                
            if rerun_pointless:
                pointless.set_correct_lattice(correct_lattice)
                pointless.decide_pointgroup()

        Debug.write('Pointless analysis of %s' % pointless.get_hklin())

        pointgroup = pointless.get_pointgroup()
        reindex_op = pointless.get_reindex_operator()
        
        Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

        return pointgroup, reindex_op, need_to_return

    def _decide_chef_cutoff_epochs(self):
        '''Analyse the mode of data collection and set a list of points
        during data collection (as epochs) where it would be sensible to
        consider cutting off the data collection. Criteria: difference
        measurements made in wedges should be paired, whole wedges only.'''

        # N.B. for SAD data or native, any image can be the last...

        dnames = []

        for epoch in sorted(self._scalr_integraters):
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()
            if not dname in dnames:
                dnames.append(dname)

        # first ask if more than one wavelength was measured

        if len(dnames) > 1:
            # we have MAD data, or more than one logical wavelength anyway
            # i.e. SIRAS or RIP
            multi = True
        else:
            # all of the data belongs to a single logical data set
            multi = False
                
        # next ask "are the data measured in wedges" (i.e. individual sweeps)
        # for this use the batch number vs. epoch table - if the batch numbers
        # increase monotonically, then wedges were not used in the data
        # collection

        epoch_to_batch = { }
        for epoch in sorted(self._scalr_integraters):
            intgr = self._scalr_integraters[epoch]
            image_to_epoch = intgr.get_integrater_sweep(
                ).get_image_to_epoch()
            offset = self._sweep_information[epoch]['batch_offset']
            for i in image_to_epoch:
                epoch_to_batch[image_to_epoch[i]] = offset + i
        
        monotonic = True

        b0 = epoch_to_batch[sorted(epoch_to_batch)[0]]

        for e in sorted(epoch_to_batch)[1:]:
            b = epoch_to_batch[e]
            if b > b0:
                b0 = b
                continue
            if b < b0:
                # we have out-of-order batches
                monotonic = False

        # print out a digest of this...

        Debug.write('Wedges: %s  Multiwavelength: %s' % (not monotonic, multi))

        # then "chunkify" - if multi is false and wedges is false, then this
        # will simply return / set a list of all epochs. If multi and not
        # wedges, then consider the end of every wavelength. Elsewise need to
        # divide up the data into the wedges, which would be the points
        # at which the monotonicness is broken above. 

        # and finally group the results - how to pass this back (as a list of
        # integrated doses I guess is the only way to go...?) - Since these
        # will be the measurements read from the Chef plots then this should
        # be ok. N.B. when the analysis is performed I will need to look
        # also at the estimation of the "sigma" for the decision about a
        # substantial change...

        # Ergo will need a hash table of epoch_to_dose...

        return

    def _sweep_information_to_chef(self):
        '''Analyse the sweep_information data structure to work out which
        measurements should be compared in chef. This will then print out
        an opinion of what should be compared by sweep epoch / image name.'''
        
        dose_rates = []
        wavelengths = []
        groups = { }
        batch_groups = { }
        resolutions = { }

        # FIXME need to estimate the inscribed circle resolution from the
        # image header information - the lowest for each group will be used
        # for the analysis... Actually - this will be the lowest resolution
        # of all of the integrater resolutions *and* all of the inscribed
        # circle resolutions...

        for epoch in sorted(self._sweep_information):
            header = self._sweep_information[epoch]['header']
            batches = self._sweep_information[epoch]['batches']
            dr = header['exposure_time'] / header['phi_width']
            wave = self._sweep_information[epoch]['dname']
            template = self._sweep_information[epoch][
                'integrater'].get_template()

            # FIXME should these not really just be inherited / propogated
            # through the FrameProcessor interface? Trac #255.
            
            indxr = self._sweep_information[epoch][
                'integrater'].get_integrater_indexer()
            beam = indxr.get_indexer_beam()
            distance = indxr.get_indexer_distance()
            wavelength = self._sweep_information[epoch][
                'integrater'].get_wavelength()

            # ok, in here decide the minimum distance from the beam centre to
            # the edge... which will depend on the size of the detector

            detector_width = header['size'][0] * header['pixel'][0] 
            detector_height = header['size'][1] * header['pixel'][1]
           
            radius = min([beam[0], detector_width - beam[0],
                          beam[1], detector_height - beam[1]])

            theta = 0.5 * math.atan(radius / distance)

            resolution = wavelength / (2 * math.sin(theta))

            if not wave in wavelengths:
                wavelengths.append(wave)

            # cluster on power of sqrt(two), perhaps? also need to get the
            # batch ranges which they will end up as so that I can fetch
            # out the reflections I want from the scaled MTZ files.
            # When it comes to doing this it will also need to know where
            # those reflections may be found... - this is in sweep_information
            # [epoch]['batches'] so should be pretty handy to get to in here.

            found = False
        
            for rate in dose_rates:
                r = rate[1]
                if dr / r > math.sqrt(0.5) and dr / r < math.sqrt(2.0):
                    # copy this for grouping
                    found = True
                    if (wave, rate[0]) in groups:
                        groups[(wave, rate[0])].append((epoch, template))
                        batch_groups[(wave, rate[0])].append(batches)
                        if rate[0] in resolutions:
                            resolutions[rate[0]] = max(resolutions[rate[0]],
                                                       resolution)
                        else:
                            resolutions[rate[0]] = resolution
                            
                                              
                    else:
                        groups[(wave, rate[0])] = [(epoch, template)]
                        batch_groups[(wave, rate[0])] = [batches]
                        if rate[0] in resolutions:
                            resolutions[rate[0]] = max(resolutions[rate[0]],
                                                       resolution)
                        else:
                            resolutions[rate[0]] = resolution

            if not found:
                rate = (len(dose_rates), dr)
                dose_rates.append(rate)
                groups[(wave, rate[0])] = [(epoch, template)]
                batch_groups[(wave, rate[0])] = [batches]

                if rate[0] in resolutions:
                    resolutions[rate[0]] = max(resolutions[rate[0]],
                                               resolution)
                else:
                    resolutions[rate[0]] = resolution
                        
        # now work through the groups and print out the results, as well
        # as storing them for future reference...

        self._chef_analysis_groups = { }
        self._chef_analysis_times = { }
        self._chef_analysis_resolutions = { }

        for rate in dose_rates:
            self._chef_analysis_groups[rate[0]] = []
            self._chef_analysis_times[rate[0]] = rate[1]
            Debug.write('Dose group %d (%s s)' % rate)
            Debug.write('Resolution limit: %.2f' % resolutions[rate[0]])
            self._chef_analysis_resolutions[rate[0]] = resolutions[rate[0]]
            for wave in wavelengths:
                if (wave, rate[0]) in groups:
                    for j in range(len(groups[(wave, rate[0])])):
                        et = groups[(wave, rate[0])][j]
                        batches = batch_groups[(wave, rate[0])][j]
                        self._chef_analysis_groups[rate[0]].append(
                            (wave, et[1], batches[0], batches[1]))
                        Debug.write('%d %s %s (%d to %d)' % \
                                    (et[0], wave, et[1],
                                     batches[0], batches[1]))

        return

    def _scale_prepare(self):
        '''Prepare the data for scaling - this will reindex it the
        reflections to the correct pointgroup and setting, for instance,
        and move the reflection files to the scale directory.'''

        Citations.cite('xds')
        Citations.cite('ccp4')
        Citations.cite('scala')
        Citations.cite('pointless')

        # GATHER phase - get the reflection files together... note that
        # it is not necessary in here to keep the batch information as we
        # don't wish to rebatch the reflections prior to scaling.
        # FIXME need to think about what I will do about the radiation
        # damage analysis in here...
        
        self._sweep_information = { }

        # FIXME in here I want to record the batch number to
        # epoch mapping as per the CCP4 Scaler implementation.

        Journal.block(
            'gathering', self.get_scaler_xcrystal().get_name(), 'XDS',
            {'working directory':self.get_working_directory()})

        for epoch in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()
            sweep_name = intgr.get_integrater_sweep_name()
            self._sweep_information[epoch] = {
                'pname':pname,
                'xname':xname,
                'dname':dname,
                'integrater':intgr,
                'prepared_reflections':None,
                'scaled_reflections':None,
                'header':intgr.get_header(),
                'batches':intgr.get_integrater_batches(),
                'image_to_epoch':intgr.get_integrater_sweep(                
                ).get_image_to_epoch(),
                'image_to_dose':{},
                'batch_offset':0,
                'sweep_name':sweep_name
                }

            Journal.entry({'adding data from':'%s/%s/%s' % \
                           (xname, dname, sweep_name)})
            
            # what are these used for?
            # pname / xname / dname - dataset identifiers
            # image to epoch / batch offset / batches - for RD analysis

            Debug.write('For EPOCH %s have:' % str(epoch))
            Debug.write('ID = %s/%s/%s' % (pname, xname, dname))
            Debug.write('SWEEP = %s' % intgr.get_integrater_sweep_name())

        try:
            all_images = self.get_scaler_xcrystal().get_all_image_names()
            dose_information, dose_factor = accumulate(all_images)

            self._chef_dose_factor = dose_factor

            # next copy this into the sweep information

            for epoch in self._sweep_information.keys():
                for i in self._sweep_information[epoch][
                    'image_to_epoch'].keys():
                    e = self._sweep_information[epoch][
                        'image_to_epoch'][i]
                    d = dose_information[e]
                    self._sweep_information[epoch][
                        'image_to_dose'][i] = d

        except RuntimeError, e:
            pass

        # next work through all of the reflection files and make sure that
        # they are XDS_ASCII format...

        epochs = self._sweep_information.keys()
        epochs.sort()

        self._first_epoch = min(epochs)

        for epoch in epochs:
            # check that this is XDS_ASCII format...
            # self._sweep_information[epoch][
            # 'integrater'].get_integrater_reflections()
            pass

        self._common_pname = self._sweep_information[epochs[0]]['pname']
        self._common_xname = self._sweep_information[epochs[0]]['xname']
        
        for epoch in epochs:
            pname = self._sweep_information[epoch]['pname']
            if self._common_pname != pname:
                raise RuntimeError, 'all data must have a common project name'
            xname = self._sweep_information[epoch]['xname']
            if self._common_xname != xname:
                raise RuntimeError, \
                      'all data for scaling must come from one crystal'

        # record the project and crystal in the scaler interface - for
        # future reference

        self._scalr_pname = self._common_pname
        self._scalr_xname = self._common_xname

        # if there is more than one sweep then compare the lattices
        # and eliminate all but the lowest symmetry examples if
        # there are more than one...

        # -------------------------------------------------
        # Ensure that the integration lattices are the same
        # -------------------------------------------------
        
        need_to_return = False

        # is this correct or should it be run for all cases?
        # try for BA0296

        if len(self._sweep_information.keys()) > 1:

            lattices = []

            for epoch in self._sweep_information.keys():

                intgr = self._sweep_information[epoch]['integrater']
                hklin = intgr.get_integrater_reflections()
                indxr = intgr.get_integrater_indexer()

                if self._scalr_input_pointgroup:
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = 'h,k,l'
                    ntr = False

                else:

                    pointgroup, reindex_op, ntr = \
                                self._pointless_indexer_jiffy(hklin, indxr)
                    
                lattice = Syminfo.get_lattice(pointgroup)
                    
                if not lattice in lattices:
                    lattices.append(lattice)

                if ntr:

                    # if we need to return, we should logically reset
                    # any reindexing operator right? right here all
                    # we are talking about is the correctness of
                    # individual pointgroups?? Bug # 3373

                    reindex_op = 'h,k,l'
                    # actually, should this not be done "by magic"
                    # when a new pointgroup is assigned in the
                    # pointless indexer jiffy above?!
                    
                    intgr.set_integrater_reindex_operator(
                        reindex_op, compose = False)
                
                    need_to_return = True
            
            # bug # 2433 - need to ensure that all of the lattice
            # conclusions were the same...
            
            if len(lattices) > 1:
                ordered_lattices = []
                for l in lattices_in_order():
                    if l in lattices:
                        ordered_lattices.append(l)

                correct_lattice = ordered_lattices[0]
                Debug.write('Correct lattice asserted to be %s' % \
                            correct_lattice)

                # transfer this information back to the indexers
                for epoch in self._sweep_information.keys():
                    integrater = self._sweep_information[
                        epoch]['integrater']
                    indexer = integrater.get_integrater_indexer()
                    sname = integrater.get_integrater_sweep_name()

                    if not indexer:
                        continue
                    
                    state = indexer.set_indexer_asserted_lattice(
                        correct_lattice)
                    if state == 'correct':
                        Debug.write('Lattice %s ok for sweep %s' % \
                                    (correct_lattice, sname))
                    elif state == 'impossible':
                        raise RuntimeError, 'Lattice %s impossible for %s' % \
                              (correct_lattice, sname)
                    elif state == 'possible':
                        Debug.write('Lattice %s assigned for sweep %s' % \
                                    (correct_lattice, sname))
                        need_to_return = True

        # if one or more of them was not in the lowest lattice,
        # need to return here to allow reprocessing

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        # next if there is more than one sweep then generate
        # a merged reference reflection file to check that the
        # setting for all reflection files is the same...

        # if we get to here then all data was processed with the same
        # lattice

        # ----------------------------------------------------------
        # next ensure that all sweeps are set in the correct setting
        # ----------------------------------------------------------

        if self.get_scaler_reference_reflection_file():
            self._reference = self.get_scaler_reference_reflection_file()
            Debug.write('Using HKLREF %s' % self._reference)

            md = self._factory.Mtzdump()
            md.set_hklin(self.get_scaler_reference_reflection_file())
            md.dump()

            self._spacegroup = Syminfo.spacegroup_name_to_number(
                md.get_spacegroup())

            Debug.write('Spacegroup %d' % self._spacegroup)

        elif Flags.get_reference_reflection_file():
            self._reference = Flags.get_reference_reflection_file()
            
            Debug.write('Using HKLREF %s' % self._reference)

            md = self._factory.Mtzdump()
            md.set_hklin(Flags.get_reference_reflection_file())
            md.dump()

            self._spacegroup = Syminfo.spacegroup_name_to_number(
                md.get_spacegroup())

            Debug.write('Spacegroup %d' % self._spacegroup)

        if len(self._sweep_information.keys()) > 1 and \
               not self._reference:
            # need to generate a reference reflection file - generate this
            # from the reflections in self._first_epoch

            intgr = self._sweep_information[self._first_epoch]['integrater']

            hklin = intgr.get_integrater_reflections()
            indxr = intgr.get_integrater_indexer()

            if self._scalr_input_pointgroup:
                Debug.write('Using input pointgroup: %s' % \
                            self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup
                ntr = False
                reindex_op = 'h,k,l'

            else:
                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, indxr)
        
            reference_reindex_op = intgr.get_integrater_reindex_operator()
            
            if ntr:

                # Bug # 3373
                
                intgr.set_integrater_reindex_operator(
                    reindex_op, compose = False)
                reindex_op = 'h,k,l'                
                need_to_return = True

            self._spacegroup = Syminfo.spacegroup_name_to_number(pointgroup)
            
            # next pass this reindexing operator back to the source
            # of the reflections

            intgr.set_integrater_reindex_operator(reindex_op)
            intgr.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup)) 
           
            hklin = intgr.get_integrater_reflections()
 
            hklout = os.path.join(self.get_working_directory(),
                                  'xds-pointgroup-reference-unsorted.mtz')
            FileHandler.record_temporary_file(hklout)

            # now use pointless to handle this conversion

            pointless = self._factory.Pointless()
            pointless.set_xdsin(hklin)
            pointless.set_hklout(hklout)
            pointless.xds_to_mtz()

            self._reference = hklout

        if self._reference:

            for epoch in self._sweep_information.keys():

                intgr = self._sweep_information[epoch]['integrater']
                hklin = intgr.get_integrater_reflections()
                indxr = intgr.get_integrater_indexer()

                # in here need to consider what to do if the user has
                # assigned the pointgroup on the command line ...

                if not self._scalr_input_pointgroup:
                    pointgroup, reindex_op, ntr = \
                                self._pointless_indexer_jiffy(hklin, indxr)
                    
                    if ntr:

                        # Bug # 3373

                        Debug.write('Reindex to standard (PIJ): %s' % \
                                    reindex_op)

                        intgr.set_integrater_reindex_operator(
                            reindex_op, compose = False)
                        reindex_op = 'h,k,l'                
                        need_to_return = True

                else:
                        
                    # 27/FEB/08 to support user assignment of pointgroups
                    
                    Debug.write('Using input pointgroup: %s' % \
                                self._scalr_input_pointgroup)
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = 'h,k,l'
                    
                intgr.set_integrater_reindex_operator(reindex_op)
                intgr.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))
                
                # convert the XDS_ASCII for this sweep to mtz - on the next
                # get this should be in the correct setting...

                hklin = intgr.get_integrater_reflections()
                hklout = os.path.join(self.get_working_directory(),
                                      'xds-pointgroup-unsorted.mtz')
                FileHandler.record_temporary_file(hklout)

                # now use pointless to make this conversion

                # try with no conversion?!

                pointless = self._factory.Pointless()
                pointless.set_xdsin(hklin)
                pointless.set_hklout(hklout)
                pointless.xds_to_mtz()
                
                pointless = self._factory.Pointless()
                pointless.set_hklin(hklout)
                pointless.set_hklref(self._reference)
                pointless.decide_pointgroup()

                pointgroup = pointless.get_pointgroup()
                reindex_op = pointless.get_reindex_operator()

                # for debugging print out the reindexing operations and
                # what have you...

                Debug.write('Reindex to standard: %s' % reindex_op)

                # this should send back enough information that this
                # is in the correct pointgroup (from the call above) and
                # also in the correct setting, from the interaction
                # with the reference set... - though I guess that the
                # spacegroup number should not have changed, right?

                # set the reindex operation afterwards... though if the
                # spacegroup number is the same this should make no
                # difference, right?!

                intgr.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))
                intgr.set_integrater_reindex_operator(reindex_op)

                # and copy the reflection file to the local directory

                dname = self._sweep_information[epoch]['dname']
                sname = intgr.get_integrater_sweep_name()
                hklin = intgr.get_integrater_reflections()
                hklout = os.path.join(self.get_working_directory(),
                                      '%s_%s.HKL' % (dname, sname))

                Debug.write('Copying %s to %s' % (hklin, hklout))
                shutil.copyfile(hklin, hklout)
                
                # record just the local file name...
                self._sweep_information[epoch][
                    'prepared_reflections'] = os.path.split(hklout)[-1]

        else:
            # convert the XDS_ASCII for this sweep to mtz

            epoch = self._first_epoch
            intgr = self._sweep_information[epoch]['integrater']
            indxr = intgr.get_integrater_indexer()
            sname = intgr.get_integrater_sweep_name()

            hklout = os.path.join(self.get_working_directory(),
                                  '%s-combat.mtz' % sname)
            FileHandler.record_temporary_file(hklout)
            
            pointless = self._factory.Pointless()
            pointless.set_xdsin(intgr.get_integrater_reflections())
            pointless.set_hklout(hklout)
            pointless.xds_to_mtz()
            
            # run it through pointless interacting with the
            # Indexer which belongs to this sweep

            hklin = hklout 

            if self._scalr_input_pointgroup:
                Debug.write('Using input pointgroup: %s' % \
                            self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup
                ntr = False
                reindex_op = 'h,k,l'

            else:
                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, indxr)

            if ntr:

                # if we need to return, we should logically reset
                # any reindexing operator right? right here all
                # we are talking about is the correctness of
                # individual pointgroups?? Bug # 3373
                
                reindex_op = 'h,k,l'
                intgr.set_integrater_reindex_operator(
                    reindex_op, compose = False)
                
                need_to_return = True

            self._spacegroup = Syminfo.spacegroup_name_to_number(pointgroup)
            
            # next pass this reindexing operator back to the source
            # of the reflections

            intgr.set_integrater_reindex_operator(reindex_op)
            intgr.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup))
            
            hklin = intgr.get_integrater_reflections()
            dname = self._sweep_information[epoch]['dname']
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s.HKL' % (dname, sname))

            # and copy the reflection file to the local
            # directory

            Debug.write('Copying %s to %s' % (hklin, hklout))
            shutil.copyfile(hklin, hklout)

            # record just the local file name...
            self._sweep_information[epoch][
                'prepared_reflections'] = os.path.split(hklout)[-1]

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        # finally work through all of the reflection files we have
        # been given and compute the correct spacegroup and an
        # average unit cell...

        unit_cell_list = []

        for epoch in self._sweep_information.keys():
            integrater = self._sweep_information[epoch]['integrater']
            cell = integrater.get_integrater_cell()
            n_ref = integrater.get_integrater_n_ref()
            
            Debug.write('Cell for %s: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                        (integrater.get_integrater_sweep_name(),
                         cell[0], cell[1], cell[2],
                         cell[3], cell[4], cell[5]))
            Debug.write('=> %d reflections' % n_ref)

            unit_cell_list.append((cell, n_ref))
            
        self._scalr_cell = compute_average_unit_cell(unit_cell_list)

        self._resolution_limits = { }
        
        Debug.write('Determined unit cell: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                    tuple(self._scalr_cell))

        if os.path.exists(os.path.join(
            self.get_working_directory(),
            'REMOVE.HKL')):
            os.remove(os.path.join(
                self.get_working_directory(),
                'REMOVE.HKL'))
            
            Debug.write('Deleting REMOVE.HKL at end of scale prepare.')

        return

    def _scale(self):
        '''Actually scale all of the data together.'''

        Journal.block(
            'scaling', self.get_scaler_xcrystal().get_name(), 'XSCALE',
            {'scaling model':'default (all)'})
            
        epochs = self._sweep_information.keys()
        epochs.sort()

        xscale = self.XScale()

        xscale.set_spacegroup_number(self._spacegroup)
        xscale.set_cell(self._scalr_cell)

        Debug.write('Set CELL: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                    tuple(self._scalr_cell))
        Debug.write('Set SPACEGROUP_NUMBER: %d' % \
                    self._spacegroup)

        Debug.write('Gathering measurements for scaling')

        for epoch in epochs:

            # get the prepared reflections
            reflections = self._sweep_information[epoch][
                'prepared_reflections']
            
            # and the get wavelength that this belongs to
            dname = self._sweep_information[epoch]['dname']

            # and the resolution range for the reflections
            intgr = self._sweep_information[epoch]['integrater']
            Debug.write('Epoch: %d' % epoch)
            Debug.write('HKL: %s (%s)' % (reflections, dname))

            resolution_low = intgr.get_integrater_low_resolution()
            resolution_high = self._resolution_limits.get(dname, 0.0)

            resolution = (resolution_high, resolution_low)

            xscale.add_reflection_file(reflections, dname, resolution)

        # set the global properties of the sample
        xscale.set_crystal(self._scalr_xname)
        xscale.set_anomalous(self._scalr_anomalous)

        if Flags.get_zero_dose():
            Debug.write('Switching on zero-dose extrapolation')
            xscale.set_zero_dose()

        # do the scaling keeping the reflections unmerged

        xscale.run()

        scale_factor = xscale.get_scale_factor()

        Debug.write('XSCALE scale factor found to be: %e' % scale_factor)

        # record the log file 

        pname = self._scalr_pname
        xname = self._scalr_xname

        FileHandler.record_log_file('%s %s XSCALE' % \
                                    (pname, xname),
                                    os.path.join(self.get_working_directory(),
                                                 'XSCALE.LP'))

        # check for outlier reflections and if a number are found
        # then iterate (that is, rerun XSCALE, rejecting these outliers)

        if not Flags.get_quick() and Flags.get_remove():
            if len(xscale.get_remove()) > 0:

                xscale_remove = xscale.get_remove()
                current_remove = []
                final_remove = []
                
                # first ensure that there are no duplicate entries...
                if os.path.exists(os.path.join(
                    self.get_working_directory(),
                    'REMOVE.HKL')):
                    for line in open(os.path.join(
                        self.get_working_directory(),
                        'REMOVE.HKL'), 'r').readlines():
                        h, k, l = map(int, line.split()[:3])
                        z = float(line.split()[3])
                        
                        if not (h, k, l, z) in current_remove:
                            current_remove.append((h, k, l, z))

                    for c in xscale_remove:
                        if c in current_remove:
                            continue
                        final_remove.append(c)

                    Debug.write(
                        '%d alien reflections are already removed' % \
                        (len(xscale_remove) - len(final_remove)))
                    
                else:
                    # we want to remove all of the new dodgy reflections
                    final_remove = xscale_remove
                    
                remove_hkl = open(os.path.join(
                    self.get_working_directory(),
                    'REMOVE.HKL'), 'w')

                z_min = Flags.get_z_min()
                rejected = 0

                # write in the old reflections
                for remove in current_remove:
                    z = remove[3]
                    if z >= z_min:
                        remove_hkl.write('%d %d %d %f\n' % remove)
                    else:
                        rejected += 1
                Debug.write('Wrote %d old reflections to REMOVE.HKL' % \
                            (len(current_remove) - rejected))
                Debug.write('Rejected %d as z < %f' % \
                            (rejected, z_min))

                # and the new reflections
                rejected = 0
                used = 0
                for remove in final_remove:
                    z = remove[3]
                    if z >= z_min:
                        used += 1
                        remove_hkl.write('%d %d %d %f\n' % remove)
                    else:
                        rejected += 1
                Debug.write('Wrote %d new reflections to REMOVE.HKL' % \
                            (len(final_remove) - rejected))
                Debug.write('Rejected %d as z < %f' % \
                            (rejected, z_min))

                remove_hkl.close()
                
                # we want to rerun the finishing step so...
                # unless we have added no new reflections
                if used:                
                    self.set_scaler_done(False)

        if not self.get_scaler_done():
            Chatter.write('Excluding outlier reflections Z > %.2f' %
                          Flags.get_z_min())

            if Flags.get_egg():
                for record in ttt():
                    Chatter.write(record)
            return

        # now get the reflection files out and merge them with scala

        # in here I need to unpack and copy the reflection files to separate
        # out the reflections from each sweep. This will mean that I can
        # get the original batch numbers (well nearly) from COMBAT which
        # *therefore* means that I can reorder the Rmerge values from
        # scala in order of collected batch, as per the analysis in
        # CCP4 Scaler and in the intra radiation damage analysis. However,
        # this will mean that I have to add in some additional batch
        # information to ensure that the scaling works correctly, and probably
        # add in the wavelength information as well...

        # bug # 2461

        output_files = xscale.get_output_reflection_files()
        wavelength_names = output_files.keys()

        # these are per wavelength - also allow for user defined resolution
        # limits a la bug # 3183.

        user_resolution_limits = { }

        for epoch in self._sweep_information.keys():
            
            input = self._sweep_information[epoch]

            intgr = input['integrater']

            if intgr.get_integrater_user_resolution():
                dmin = intgr.get_integrater_high_resolution()
                
                if not user_resolution_limits.has_key(input['dname']):
                    user_resolution_limits[input['dname']] = dmin
                    self._resolution_limits[input['dname']] = dmin
                    self._user_resolution_limits[dname] = True
                elif dmin < user_resolution_limits[input['dname']]:
                    user_resolution_limits[input['dname']] = dmin
                    self._resolution_limits[input['dname']] = dmin

        self._tmp_scaled_refl_files = { }

        self._scalr_statistics = { }

        # FIXED in here I need to get the spacegroup and reindexing
        # operator to put the reflections in the standard setting from
        # all reflections merged together rather than from each
        # wavelength separately. I will therefore need to include the
        # rebatch-and-sort-together shuffle from CCP4 scaler
        # implementation.

        max_batches = 0
        mtz_dict = { } 

        # FIXME in here want to make use of the helper to ensure that the
        # pname xname dname stuff is added and also reshuffle the data
        # into epoch order (which may be fiddly) then merge thus
        # for radiation damage analysis...

        # create the mapping table from reflection file name (the end
        # thereof) to pane/xname/dname.

        project_info = { }
        for epoch in self._sweep_information.keys():
            pname = self._common_pname
            xname = self._common_xname
            dname = self._sweep_information[epoch]['dname']
            reflections = os.path.split(
                self._sweep_information[epoch]['prepared_reflections'])[-1]
            project_info[reflections] = (pname, xname, dname)

        # note in here - combat may use different scale factors for each
        # data set, but the merging by scala will have scales constant
        # which will assign a different constant scale factor for each
        # run, which should correct for any differences in factor introduced
        # here...
            
        for epoch in self._sweep_information.keys():
            self._sweep_information[epoch]['scaled_reflections'] = None

        for wavelength in wavelength_names:
            hklin = output_files[wavelength]

            xsh = XDSScalerHelper()
            xsh.set_working_directory(self.get_working_directory())

            ref = xsh.split_and_convert_xscale_output(
                hklin, 'SCALED_', project_info, 1.0 / scale_factor)

            # this loop is working through the reflection files we
            # have, then looking for the epoch it belongs to (hash
            # table would be better...) then assigning the scaled
            # reflection file appropriately...

            for hklout in ref.keys():
                for epoch in self._sweep_information.keys():
                    if os.path.split(self._sweep_information[epoch][
                        'prepared_reflections'])[-1] == \
                        os.path.split(hklout)[-1]:
                        if self._sweep_information[epoch][
                            'scaled_reflections'] != None:
                            raise RuntimeError, 'duplicate entries'
                        self._sweep_information[epoch][
                            'scaled_reflections'] = ref[hklout]
                     
        # now I have a list of reflection files in MTZ format linked
        # to the original reflection files from the integrater - which
        # means I can do the rebatch shuffle prior to merging in Scala.
        
        # have defined a new method in the scala wrapper called "multi_merge"
        # to enable this.

        # prior to these calculations, let's do some thinking about
        # resolution limits...

        for epoch in self._sweep_information.keys():
            hklin = self._sweep_information[epoch]['scaled_reflections']
            dname = self._sweep_information[epoch]['dname']
            sname = self._sweep_information[epoch]['sweep_name']

            # figure resolutions as: max(r_comp, r_rm, r_uis, r_mis)
            # where these come from the calculations below. Then, for a given
            # wavelength, pick the highest resolution limit.
            
            log_completeness = os.path.join(self.get_working_directory(),
                                      '%s-completeness.log' % sname)

            if os.path.exists(log_completeness):
                log_completeness = None
            
            log_rmerge = os.path.join(self.get_working_directory(),
                                      '%s-rmerge.log' % sname)

            if os.path.exists(log_rmerge):
                log_rmerge = None

            log_isigma = os.path.join(self.get_working_directory(),
                                      '%s-isigma.log' % sname)

            if os.path.exists(log_isigma):
                log_isigma = None
            
            log_misigma = os.path.join(self.get_working_directory(),
                                      '%s-misigma.log' % sname)

            if os.path.exists(log_misigma):
                log_misigma = None
            
            m = merger(hklin)

            hkl_copy = os.path.join(self.get_working_directory(),
                                    'R_%s' % os.path.split(hklin)[-1])

            if not os.path.exists(hkl_copy):
                shutil.copyfile(hklin, hkl_copy)

            # let's properly listen to the user's resolution limit needs...

            if self._user_resolution_limits.get(dname, False):
                resolution = self._resolution_limits[dname]

            else:
                if Flags.get_small_molecule():
                    m.calculate_resolution_ranges(nbins = 10)
                else:
                    m.calculate_resolution_ranges(nbins = 100)

                r_comp = m.resolution_completeness(log = log_completeness)
                r_rm = m.resolution_rmerge(log = log_rmerge)
                r_uis = m.resolution_unmerged_isigma(log = log_isigma)
                r_mis = m.resolution_merged_isigma(log = log_misigma)
                
                resolution = max([r_comp, r_rm, r_uis, r_mis])

            Chatter.write('Resolution for sweep %s: %.2f' % \
                          (sname, resolution))

            # N.B. below should really reset so that the scaling is re-run
            # to the assigned limit... also note that if the resolution limit
            # is user assigned need to use it verbatim.

            if not dname in self._resolution_limits:
                self._resolution_limits[dname] = resolution
                self.set_scaler_done(False)                
            else:
                if resolution < self._resolution_limits[dname]:
                    self._resolution_limits[dname] = resolution
                    self.set_scaler_done(False)


        if not self.get_scaler_done():
            Debug.write('Returning as scaling not finished...')
            return

        # first the rebatch / sortmtz shuffle
        
        max_batches = 0
        
        for epoch in self._sweep_information.keys():

            # keep a count of the maximum number of batches in a block -
            # this will be used to make rebatch work below.

            hklin = self._sweep_information[epoch]['scaled_reflections']

            md = self._factory.Mtzdump()
            md.set_hklin(hklin)
            md.dump()

            if self._sweep_information[epoch]['batches'] == [0, 0]:
                # get them from the mtz dump output
                
                Chatter.write('Getting batches from %s' % hklin)
                batches = md.get_batches()
                self._sweep_information[epoch]['batches'] = [min(batches),
                                                             max(batches)]
                Chatter.write('=> %d to %d' % (min(batches),
                                               max(batches)))

            # FIXME here check that this matches up with the input,
            # if we have both sources of batch information

            batches = self._sweep_information[epoch]['batches']
            if 1 + max(batches) - min(batches) > max_batches:
                max_batches = max(batches) - min(batches) + 1
            
            # FIXME assert that there will only be one dataset in this
            # reflection file

            datasets = md.get_datasets()

            Debug.write('In reflection file %s found:' % hklin)
            for d in datasets:
                Debug.write('... %s' % d)
            
            dataset_info = md.get_dataset_info(datasets[0])

            # FIXME should also confirm the batch numbers from this
            # reflection file...

            # now make the comparison - FIXME this needs to be implemented
            # FIXME also - if the pname, xname, dname is not defined by
            # this time, make a note of this so that it can be included
            # at a later stage.

        Debug.write('Biggest sweep has %d batches' % max_batches)
        max_batches = nifty_power_of_ten(max_batches)
    
        # then rebatch the files, to make sure that the batch numbers are
        # in the same order as the epochs of data collection.

        epochs = self._sweep_information.keys()
        epochs.sort()

        # need to check that the batches are all sensible numbers
        # so run rebatch on them! note here that we will need new
        # MTZ files to store the output...

        counter = 0

        Journal.block(
            'merging', self.get_scaler_xcrystal().get_name(), 'CCP4', {})

        for epoch in epochs:
            rb = self._factory.Rebatch()

            hklin = self._sweep_information[epoch]['scaled_reflections']

            pname = self._sweep_information[epoch]['pname']
            xname = self._sweep_information[epoch]['xname']
            dname = self._sweep_information[epoch]['dname']

            sweep_name = self._sweep_information[epoch]['sweep_name']

            Journal.entry({'adding data from':'%s/%s/%s' % \
                           (xname, dname, sweep_name)})

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_%s_%d.mtz' % \
                                  (pname, xname, dname, counter))

            # we will want to delete this one exit
            FileHandler.record_temporary_file(hklout)

            # record this for future reference - will be needed in the
            # radiation damage analysis...

            # hack - reset this as it gets in a muddle...
            intgr = self._sweep_information[epoch]['integrater']
            self._sweep_information[epoch][
                'batches'] = intgr.get_integrater_batches()
            
            first_batch = min(self._sweep_information[epoch]['batches'])
            self._sweep_information[epoch][
                'batch_offset'] = counter * max_batches - first_batch + 1

            rb.set_hklin(hklin)
            rb.set_first_batch(counter * max_batches + 1)
            rb.set_hklout(hklout)

            new_batches = rb.rebatch()

            # update the "input information"

            self._sweep_information[epoch]['hklin'] = hklout
            self._sweep_information[epoch]['batches'] = new_batches

            # update the counter & recycle

            counter += 1

        # now parse the structure of the data to write out how they should
        # be examined by chef... N.B. this was moved from the top of this
        # method see trac #200.

        if Flags.get_chef():
            self._sweep_information_to_chef()
            self._decide_chef_cutoff_epochs()

        # then sort the files together, making sure that the resulting
        # reflection file looks right.

        s = self._factory.Sortmtz()

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted.mtz' % \
                              (self._common_pname, self._common_xname))
        
        s.set_hklout(hklout)

        for epoch in epochs:
            s.add_hklin(self._sweep_information[epoch]['hklin'])

        s.sort(vrset = -99999999.0)

        self._prepared_reflections = hklout

        # if we have a reference reflection file then use this for all
        # of the spacegroup information (remember that we have
        # reindexed already) else inspect the absences...

        # figure out the correct reindexing operator using this reflection
        # file

        if self.get_scaler_reference_reflection_file():
            md = self._factory.Mtzdump()
            md.set_hklin(self.get_scaler_reference_reflection_file())
            md.dump()

            spacegroups = [md.get_spacegroup()]
            reindex_operator = 'h,k,l'

        else:            

            pointless = self._factory.Pointless()
            pointless.set_hklin(hklout)
            pointless.decide_spacegroup()

            FileHandler.record_log_file('%s %s pointless' % \
                                        (self._common_pname,
                                         self._common_xname),
                                        pointless.get_log_file())

            # get one spacegroup and so on which will be used for
            # all of the reflection files...
            
            spacegroups = pointless.get_likely_spacegroups()
            reindex_operator = pointless.get_spacegroup_reindex_operator()

            if self._scalr_input_spacegroup:
                Debug.write('Assigning user input spacegroup: %s' % \
                            self._scalr_input_spacegroup)
                spacegroups = [self._scalr_input_spacegroup]
                reindex_operator = 'h,k,l'

        # save these for later - we will reindex the merged
        # data after scaling - the first of these will be used
        # as correct so spacegroup assignment should just work...

        self._scalr_likely_spacegroups = spacegroups
        spacegroup = self._scalr_likely_spacegroups[0]
        
        self._scalr_reindex_operator = reindex_operator

        Chatter.write('Likely spacegroups:')
        for spag in self._scalr_likely_spacegroups:
            Chatter.write('%s' % spag)

        Chatter.write(
            'Reindexing to first spacegroup setting: %s (%s)' % \
            (spacegroup, reindex_operator))

        # FIXME don't save this for later - apply it now, should be
        # safe as the measurements should now be on a sensible scale...

        Debug.write('Reindexing the data before merging now...')

        hklin = self._prepared_reflections
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_reindex.mtz' % \
                              (self._common_pname, self._common_xname))

        FileHandler.record_temporary_file(hklout)
        
        ri = self._factory.Reindex()
        ri.set_hklin(hklin)
        ri.set_hklout(hklout)
        ri.set_spacegroup(spacegroup)
        ri.set_operator(reindex_operator)
        ri.reindex()

        # then sort the bloody file again!

        hklin = hklout
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted.mtz' % \
                              (self._common_pname, self._common_xname))

        s = self._factory.Sortmtz()        
        s.set_hklin(hklin)
        s.set_hklout(hklout)
 
        s.sort(vrset = -99999999.0)

        self._prepared_reflections = hklout

        # N.B. for the chef output will also need to reindex the sorted
        # input files to the sorting step above, so that they can be
        # analysed with chef. N.B. this may also involve sorting together
        # the sweeps afterwards (hell, why not merge it into a single step?)
        # of the sweeps which (i) belong to the same wavelength and (ii)
        # are comparable in terms of exposure time per degree and distance.

        # ok, in here want to:
        #
        #  - chop out the batches which belong to different chef analysis
        #    groups
        #  - sort together comparison groups (i.e. inverse-beam pairs)
        #  - add the DOSE information using doser and @doser.in
        #  - run the chef analysis
        #  - mark the chef log files for saving in the LogFiles directory

        doses = { }

        for epoch in self._sweep_information.keys():
            i2d = self._sweep_information[epoch]['image_to_dose']
            i2e = self._sweep_information[epoch]['image_to_epoch']
            offset = self._sweep_information[epoch]['batch_offset']
            images = sorted(i2d.keys())
            for i in images:
                batch = i + offset
                doses[batch] = i2d[i]

        # now output a doser input file - just for kicks ;o) - at this point
        # the offsets should be known so this should be ok - where this was
        # before the batch offsets were not known...

        fout = open(os.path.join(self.get_working_directory(),
                                 'doser.in'), 'w')

        for epoch in self._sweep_information.keys():
            i2d = self._sweep_information[epoch]['image_to_dose']
            i2e = self._sweep_information[epoch]['image_to_epoch']
            offset = self._sweep_information[epoch]['batch_offset']
            images = i2d.keys()
            images.sort()
            for i in images:
                fout.write('batch %d dose %f time %f\n' % \
                           (i + offset, i2d[i], i2e[i]))

        fout.close()

        # the maximum dose should be one image higher than the "real"
        # maximum dose to give a little breathing room - this is achieved
        # by incrementing this by one image worth of dose...

        all_doses = sorted([doses[b] for b in doses])
        dose_max = all_doses[-1] + (all_doses[-1] - all_doses[-2])

        # now perform the chef analysis for each dose rate group - this
        # can harmlessly include the running of doser on each little bit

        for group in sorted(self._chef_analysis_groups):
            # for each wavelength in this analysis group, get the batch
            # ranges wanted for the comparison, chop them out of the
            # given reflection file in the dictionary above, then
            # sort them back together to e.g. chef_group_%s_WAVE.mtz
            # keeping a track of this of course

            resolution = self._chef_analysis_resolutions[group]

            Debug.write('Preparing chef analysis group %d' % group)
            Debug.write('N.B. to resolution %.2f' % resolution)

            bits = { }

            for wtse in self._chef_analysis_groups[group]:
                wave, template, start, end = wtse
                hklout = os.path.join(self.get_working_directory(),
                                      'chef_%d_%s_%d_%d.mtz' % \
                                      (group, wave, start, end))
                hklout_all = os.path.join(self.get_working_directory(),
                                          'chef_%d_%s.mtz' % \
                                          (group, wave))

                # All of the data is in the one MTZ file as it has not
                # yet been separated into wavelengths by Scala
                
                hklin = self._prepared_reflections
                rb = self._factory.Rebatch()
                rb.set_hklin(hklin)
                rb.set_hklout(hklout)
                rb.limit_batches(start, end)

                if not wave in bits:
                    bits[wave] = [hklout_all]
                    
                bits[wave].append(hklout)
                FileHandler.record_temporary_file(hklout)
                FileHandler.record_temporary_file(hklout_all)

            # now sort these together
            for wave in bits:
                s = self._factory.Sortmtz()
                s.set_hklout(bits[wave][0])
                for hklin in bits[wave][1:]:
                    s.add_hklin(hklin)
                s.sort()

            # now add the doser information to all of these sorted files
            # and record these as input files to chef... 

            chef_hklins = []
            
            for wave in bits:
                hklin = bits[wave][0]
                hklout = '%s_dose.mtz' % hklin[:-4]

                add_dose_time_to_mtz(hklin = hklin, hklout = hklout,
                                     doses = doses)

                chef_hklins.append(hklout)

            # then run chef with this - no analysis as yet, but to record
            # the log file to chef_groupN_analysis or something and be
            # sure that it finds it's way to the LogFiles directory.
            
            # then feed the results to chef

            chef = self._factory.Chef()

            chef.set_title('%s Group %d' % (self._common_xname, group + 1))

            dose_step = self._chef_analysis_times[group] / \
                        self._chef_dose_factor
            anomalous = self.get_scaler_anomalous()

            for hklin in chef_hklins:
                chef.add_hklin(hklin)

            chef.set_anomalous(anomalous)
            chef.set_resolution(resolution)

            # work around a possible failure to read the dose profiles
            # correctly

            if min(all_doses) < max(all_doses):
                chef.set_width(dose_step)
                chef.set_max(dose_max)
                chef.set_labin('DOSE')
            else:
                chef.set_labin('BATCH')
            
            chef.run()

            FileHandler.record_log_file(
                '%s chef %d' % (self._common_xname, group + 1),
                chef.get_log_file())
        
        # this is #181 so figure this out first...

        # record the updated cell parameters...
        # they should be the same in all files so... aah - if I set
        # this in here it may break the scaling if the data are also
        # reindexed! :o(
        Debug.write(
            'Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f' % \
            tuple(ri.get_cell()))
        self._reindexed_cell = tuple(ri.get_cell())

        # Debug.write('Reindex operator: %s' % reindex_operator)
        # Debug.write('Will save this for later')

        # FIXME in here want to use REINDEX on the output of COMBAT
        # to get the setting right - in which case I will be able to
        # write out unmerged reflection files later on...

        sc = self._factory.Scala()
        sc.set_hklin(self._prepared_reflections)

        scales_file = '%s.scales' % self._common_xname
        sc.set_new_scales_file(scales_file)        

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       name = input['sweep_name'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.multi_merge()

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()
        
        resolution_info = { }

        for key in loggraph.keys():
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # next compute resolution limits for each dataset.

        # self._resolution_limits = { }

        reflection_files = sc.get_scaled_reflection_files()

        highest_resolution = 100.0

        # check in here that there is actually some data to scale..!

        if len(resolution_info.keys()) == 0:
            raise RuntimeError, 'no resolution info'

        for dataset in resolution_info.keys():

            if dataset in user_resolution_limits:
                resolution = user_resolution_limits[dataset]
                self._resolution_limits[dataset] = resolution
                if resolution < highest_resolution:
                    highest_resolution = resolution
                Chatter.write('Resolution limit for %s: %5.2f' % \
                              (dataset, resolution))
                continue

            if not dataset in self._resolution_limits:
                raise RuntimeError, 'resolution calculation already failed?'

            if False:
                resolution = determine_scaled_resolution(
                    reflection_files[dataset],
                    Flags.get_i_over_sigma_limit())[1]
                
                self._resolution_limits[dataset] = resolution

            resolution = self._resolution_limits[dataset]
            if resolution < highest_resolution:
                highest_resolution = resolution

            Chatter.write('Resolution limit for %s: %5.2f' % \
                          (dataset, self._resolution_limits[dataset]))

        self._scalr_highest_resolution = highest_resolution

        Debug.write('Scaler highest resolution set to %5.2f' % \
                      highest_resolution)

        # Ok, now we have the resolution limit stuff, need to work through
        # all of the integraters which belong to this set and if the
        # resolution defined for a given dataset is found to be lower
        # than the high resolution limit of the integrater, then reset
        # that limit, assert that the scaling and preparation is needed and
        # at the end return.

        best_resolution = 100.0

        for epoch in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()

            # check the resolution limit for this integrater
            dmin = intgr.get_integrater_high_resolution()

            Debug.write('Integrater (%s) resolution limit: %.2f' % \
                        (dname, dmin))

            if self._resolution_limits[dname] < best_resolution:
                best_resolution = self._resolution_limits[dname]

        # if we need to redo the scaling, return to allow this to happen

        if not self.get_scaler_done():
            Debug.write('Returning as scaling not finished...')
            return

        batch_info = { }
        
        for key in loggraph.keys():
            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                batch_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # perform some analysis of these results

        average_completeness = 0.0

        for k in data.keys():
            average_completeness += data[k]['Completeness'][0]
        average_completeness /= len(data.keys())

        sdadd_full = 0.0
        sdb_full = 0.0

        # ---------- FINAL SCALING ----------

        # assert the resolution limits in the integraters - beware, this
        # means that the reflection files will probably have to be
        # regenerated (integration restarted!) and so we will have to
        # build in some "fudge factor" to ensure we don't get stuck in a
        # tight loop - initially just rerun the scaling with all of the
        # "right" parameters...
        
        scales_file = '%s_final.scales' % self._common_xname

        sc = self._factory.Scala()

        FileHandler.record_log_file('%s %s scala' % (self._common_pname,
                                                     self._common_xname),
                                    sc.get_log_file())

        sc.set_resolution(best_resolution)
        sc.set_hklin(self._prepared_reflections)
        sc.set_new_scales_file(scales_file)

        # this is now handled more elegantly by the Scala wrapper
        
        if sdadd_full == 0.0 and sdb_full == 0.0:
            pass
        else:
            sc.add_sd_correction('both', 1.0, sdadd_full, sdb_full)

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            run_resolution_limit = self._resolution_limits[input['dname']]

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit,
                       name = input['sweep_name'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.multi_merge()

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()

        # look for the standard deviation graphs - see FIXME 31/OCT/06

        standard_deviation_info = { }

        for key in loggraph.keys():
            if 'standard deviation v. Intensity' in key:
                dataset = key.split(',')[-1].strip()
                standard_deviation_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # write this in an interesting way...

        for dataset in standard_deviation_info.keys():
            info = standard_deviation_info[dataset]

            Debug.write('Standard errors for %s' % dataset)

            for j in range(len(info['1_Range'])):
                n_full = int(info['5_Number'][j])
                I_full = float(info['4_Irms'][j])
                
                if info['7_SigmaFull'][j] == '-':
                    s_full = 0.0
                else:
                    s_full = float(info['7_SigmaFull'][j])

                i_tot = I_full
                s_tot = s_full

                Debug.write('%.1f %d %.2f' % (I_full, n_full, s_full))

        # look also for a sensible resolution limit for this data set -
        # that is, the place where I/sigma is about two for the highest
        # resolution data set - this should be a multiple of 0.05 A just
        # to keep the output tidy...

        resolution_info = { }

        for key in loggraph.keys():
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # and also radiation damage stuff...

        batch_info = { }
        
        for key in loggraph.keys():
            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                batch_info[dataset] = transpose_loggraph(
                    loggraph[key])


        # finally put all of the results "somewhere useful"
        
        self._scalr_statistics = data

        # FIXED this is not correct for multi-wavelength data...
        # it should be now!

        self._tmp_scaled_refl_files = copy.deepcopy(
            sc.get_scaled_reflection_files())

        self._scalr_scaled_reflection_files = { }
        
        # compute a "standard unit cell" - FIXME perhaps - looks like
        # sortmtz will already assign somehow a standard unit cell -
        # interesting!

        # convert reflection files to .sca format - use mtz2various for this

        self._scalr_scaled_reflection_files['sca'] = { }

        # this is confusing as it implicitly iterates over the keys of the
        # dictionary
        
        for key in self._tmp_scaled_refl_files:
            file = self._tmp_scaled_refl_files[key]
            scaout = '%s.sca' % file[:-4]

            m2v = self._factory.Mtz2various()
            m2v.set_hklin(file)
            m2v.set_hklout(scaout)
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][key] = scaout

            FileHandler.record_data_file(scaout)

        # finally repeat the merging again (!) but keeping the
        # wavelengths separate to generate the statistics on a
        # per-wavelength basis - note that we do not want the
        # reflection files here... bug# 2229

        for key in self._scalr_statistics:
            pname, xname, dname = key

            sc = self._factory.Scala()
            sc.set_hklin(self._prepared_reflections)
            sc.set_scales_file(scales_file)
            sc.add_sd_correction('both', 1.0, sdadd_full, sdb_full)
        
            for epoch in epochs:
                input = self._sweep_information[epoch]
                start, end = (min(input['batches']), max(input['batches']))
                if dname == input['dname']:
                    sc.add_run(start, end, pname = input['pname'],
                               xname = input['xname'],
                               dname = input['dname'],
                               exclude = False)
                else:
                    sc.add_run(start, end, pname = input['pname'],
                               xname = input['xname'],
                               dname = input['dname'],
                               exclude = True)                    

                # set the resolution limit to what we decided above...
                # by the time we get this far this should have been what
                # was used...
                sc.set_resolution(self._resolution_limits[dname])

            sc.set_hklout(os.path.join(self.get_working_directory(),
                                           'temp.mtz'))
                
            if self.get_scaler_anomalous():
                sc.set_anomalous()
                
            sc.multi_merge()
            stats = sc.get_summary()

            # this should just work ... by magic!
            self._scalr_statistics[key] = stats[key]

        self._scalr_highest_resolution = best_resolution

        # also output the unmerged scalepack format files...

        sc = self._factory.Scala()
        sc.set_resolution(best_resolution)
        sc.set_hklin(self._prepared_reflections)
        sc.set_scalepack(os.path.join(self.get_working_directory(),
                                      '%s_%s_unmerged.sca' % \
                                      (self._common_pname,
                                       self._common_xname)))

        # this is now handled more elegantly by the Scala wrapper
        
        if sdadd_full == 0.0 and sdb_full == 0.0:
            pass
        else:
            sc.add_sd_correction('both', 1.0, sdadd_full, sdb_full)

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            run_resolution_limit = self._resolution_limits[input['dname']]

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit,
                       name = input['sweep_name'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_temp.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.multi_merge()

        # mark the temp files for deletion... etc.

        self._scalr_scaled_reflection_files['sca_unmerged'] = { }

        for dataset in sc.get_scaled_reflection_files().keys():
            hklout = sc.get_scaled_reflection_files()[dataset]
            FileHandler.record_temporary_file(hklout)
            
            # then mark the scalepack files for copying...

            scalepack = os.path.join(os.path.split(hklout)[0],
                                     os.path.split(hklout)[1].replace(
                '_temp', '_unmerged').replace('.mtz', '.sca'))
            self._scalr_scaled_reflection_files['sca_unmerged'][
                dataset] = scalepack
            FileHandler.record_data_file(scalepack)
                           
        return

    def _scale_finish(self):
        
        # next transform to F's from I's etc.

        if len(self._tmp_scaled_refl_files.keys()) == 0:
            raise RuntimeError, 'no reflection files stored'

        if not Flags.get_small_molecule():

            for wavelength in self._tmp_scaled_refl_files.keys():

                hklin = self._tmp_scaled_refl_files[wavelength]

                truncate = self._factory.Truncate()
                truncate.set_hklin(hklin)

                if self.get_scaler_anomalous():
                    truncate.set_anomalous(True)
                else:
                    truncate.set_anomalous(False)
                
                FileHandler.record_log_file('%s %s %s truncate' % \
                                            (self._common_pname,
                                             self._common_xname,
                                             wavelength),
                                            truncate.get_log_file())
                
                hklout = os.path.join(self.get_working_directory(),
                                      '%s_truncated.mtz' % wavelength)

                truncate.set_hklout(hklout)
                truncate.truncate()

                Debug.write('%d absent reflections in %s removed' % \
                            (truncate.get_nabsent(), wavelength))

                b_factor = truncate.get_b_factor()

                # record the b factor somewhere (hopefully) useful...

                self._scalr_statistics[
                    (self._common_pname, self._common_xname, wavelength)
                    ]['Wilson B factor'] = [b_factor]
            
                # look for the second moment information...
                moments = truncate.get_moments()
                # for j in range(len(moments['MomentZ2'])):
                # pass

                # and record the reflection file..
                self._tmp_scaled_refl_files[wavelength] = hklout

        # copy across the reindexed unit cell - messy is this correct?
        # #1330.

        self._scalr_cell = self._reindexed_cell
            
        # and cad together into a single data set - recalling that we already
        # have a standard unit cell... and remembering where the files go...

        # self._scalr_scaled_reflection_files = { }

        if len(self._tmp_scaled_refl_files.keys()) > 1:

            # for each reflection file I need to (1) ensure that the
            # spacegroup is uniformly set and (2) ensure that
            # the column names are appropriately relabelled.

            reflection_files = { }

            for wavelength in self._tmp_scaled_refl_files.keys():
                cad = self._factory.Cad()
                cad.add_hklin(self._tmp_scaled_refl_files[wavelength])
                cad.set_hklout(os.path.join(
                    self.get_working_directory(),
                    'cad-tmp-%s.mtz' % wavelength))
                cad.set_new_suffix(wavelength)
                cad.update()

                reflection_files[wavelength] = cad.get_hklout()
                FileHandler.record_temporary_file(cad.get_hklout())
                
            # now merge the reflection files together...
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_merged.mtz' % (self._common_pname,
                                                        self._common_xname))
            FileHandler.record_temporary_file(hklout)

            Debug.write('Merging all data sets to %s' % hklout)

            cad = self._factory.Cad()
            for wavelength in reflection_files.keys():
                cad.add_hklin(reflection_files[wavelength])
            cad.set_hklout(hklout)
            cad.merge()
            
            self._scalr_scaled_reflection_files['mtz_merged'] = hklout

        else:

            # we don't need to explicitly merge it, since that's just
            # silly ;o)

            # however this doesn't allow for the renaming below in the free
            # flag adding step! Doh!
            
            self._scalr_scaled_reflection_files[
                'mtz_merged'] = self._tmp_scaled_refl_files[
                self._tmp_scaled_refl_files.keys()[0]]

        # finally add a FreeR column, and record the new merged reflection
        # file with the free column added.

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_free_temp.mtz' % (self._common_pname,
                                                       self._common_xname))

        FileHandler.record_temporary_file(hklout)
        
        if self.get_scaler_freer_file():
            # e.g. via .xinfo file
            
            freein = self.get_scaler_freer_file()
        
            Debug.write('Copying FreeR_flag from %s' % freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
            c.set_hklout(hklout)
            c.copyfree()

        elif Flags.get_freer_file():
            # e.g. via -freer_file command line argument

            freein = Flags.get_freer_file()

            Debug.write('Copying FreeR_flag from %s' % freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
            c.set_hklout(hklout)
            c.copyfree()

        else:

            # default fraction of 0.05
            free_fraction = 0.05
            
            if Flags.get_free_fraction():
                free_fraction = Flags.get_free_fraction()
            elif Flags.get_free_total():
                ntot = Flags.get_free_total()
                
                # need to get a fraction, so...
                mtzdump = self._factory.Mtzdump()
                mtzdump.set_hklin(hklin)
                mtzdump.dump()
                nref = mtzdump.get_reflections()
                free_fraction = float(ntot) / float(nref)
                
            f = self._factory.Freerflag()
            f.set_free_fraction(free_fraction)
            f.set_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
            f.set_hklout(hklout)
            f.add_free_flag()

        # then check that this set are complete

        hklin = hklout
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_free.mtz' % (self._common_pname,
                                                  self._common_xname))

        # default fraction of 0.05
        free_fraction = 0.05

        if Flags.get_free_fraction():
            free_fraction = Flags.get_free_fraction()
        elif Flags.get_free_total():
            ntot = Flags.get_free_total()

            # need to get a fraction, so...
            mtzdump = self._factory.Mtzdump()
            mtzdump.set_hklin(hklin)
            mtzdump.dump()
            nref = mtzdump.get_reflections()
            free_fraction = float(ntot) / float(nref)

        f = self._factory.Freerflag()
        f.set_free_fraction(free_fraction)
        f.set_hklin(hklin)
        f.set_hklout(hklout)
        f.complete_free_flag()

        # remove 'mtz_merged' from the dictionary - this is made
        # redundant by the merged free...
        del self._scalr_scaled_reflection_files['mtz_merged']

        # changed from mtz_merged_free to plain ol' mtz
        self._scalr_scaled_reflection_files['mtz'] = hklout

        # record this for future reference
        FileHandler.record_data_file(hklout)

        # have a look for twinning ...
        sfc = self._factory.Sfcheck()
        sfc.set_hklin(hklout)
        sfc.analyse()
        twinning_score = sfc.get_twinning()

        Chatter.write('Overall twinning score: %4.2f' % twinning_score)
        if twinning_score > 1.9:
            Chatter.write('Your data do not appear to be twinned')
        elif twinning_score < 1.6:
            Chatter.write('Your data appear to be twinned')
        else:
            Chatter.write('Ambiguous score (1.6 < score < 1.9)')

        # next have a look for radiation damage... if more than one wavelength

        if len(self._tmp_scaled_refl_files.keys()) > 1 and \
               not Flags.get_small_molecule():
            crd = CCP4InterRadiationDamageDetector()

            crd.set_working_directory(self.get_working_directory())

            crd.set_hklin(hklout)

            if self.get_scaler_anomalous():
                crd.set_anomalous(True)
            
            hklout = os.path.join(self.get_working_directory(), 'temp.mtz')
            FileHandler.record_temporary_file(hklout)
            
            crd.set_hklout(hklout)

            status = crd.detect()
            
            Chatter.write('')
            # Chatter.write('Inter-wavelength B and R-factor analysis:')
            Chatter.banner('Local Scaling %s' % self._common_xname)
            for s in status:
                Chatter.write('%s %s' % s)
            # Chatter.write('')
            Chatter.banner('')

        return

