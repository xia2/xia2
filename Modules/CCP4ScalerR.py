#!/usr/bin/env python
# CCP4ScalerR.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 21/SEP/06
# 
# An implementation of the Scaler interface using CCP4 programs.
# 
# FIXED 21/SEP/06 this needs to have a working directory property
#                 so we can specify where it is being run... 
#                 This should also be inherited by the "child" jobs...
# 
# FIXED 25/SEP/06 need to include pointgroup determination in the pipeline
#                 though this will begin to impact on the lattice management
#                 stuff in XCrystal. This has now been in for a while,
#                 but needs to be connected to the Indexer to ensure that
#                 an eliminated pointgroup is not selected.
# 
# ----- 27/SEP/06 need to define a reference wavelength for the anomalous
#                 dispersive differences. This is best assigned at this 
#                 level as the wavelength with the smallest |f'| + |f''|
#                 or something:
# 
#                 BASE keyword to scala - BASE [crystal xname] dataset dname
# 
#                 This defaults to the data set with the shortest wavelength.
#  
# FIXED 27/OCT/06 need to make sure that the pointless run in here does not
#                 select a symmetry for the crystal which has been eliminated
#                 already... this will be fixed as a part of FIXME 28/NOV/06
#                 below (pertaining to fedback.)
# 
# FIXME 31/OCT/06 need to make the scaling do the following:
#                 (1)  assert a sensible resolution limit.
#                 (2)  twiddle the sd parameters to get the flattest
#                      error curve possible.
#                 (3)  limit by batch in radiation damage terms - or -
#                 (3a) switch on zero-dose extrapolation.
#                 (4)  eliminate badly radiation damaged data in different
#                      sweeps.
#
# ----- 01/NOV/06 should probably sort together all data for a particular
#                 wavelength before running pointless - this will probably
#                 give better statistics from that program.
#  
# FIXED 03/NOV/06 need to merge the first sweep in whatever pointgroup we 
#                 think is correct, and then reindex the rest of this data
#                 using the first one as a reference, and then perform the 
#                 scaling based on this. TS02 breaks on the unit cell check
#                 at the CAD phase below.
#
# FIXED 03/NOV/06 should check that the reflection files have consistent
#                 unit cell parameters going in to scaling. c/f FIXME above.
#                 This is now handled.
# 
# FIXED 06/NOV/06 this is more complicated than I at first thought, since
#                 pointless will not reindex into the correct symmetry a 
#                 set which is indexed in a different pointgroup - this
#                 means for TS03 that the system barfs. The only way to
#                 fix this I can see is to move the reindexing step a little
#                 later, so that this works against post-pointlessed (thus,
#                 indexed in the "correct" pointgroup) data which can then
#                 be correctly re-set... shockingly this seems to work fine!
# 
# FIXED 06/NOV/06 need also to investigate the systematic absences and reset
#                 to a standard setting (pointless does this) if appropriate.
#                 If it's P43212 or P41212 then I need to decide what is 
#                 best to do... provide a list - this is in hand.
# 
# FIXED 15/NOV/06 need to add a FreeR column to the reflection file.
#
# FIXED 16/NOV/06 also need to run pointless on the final data sets to
#                 have a stab at the correct spacegroup, e.g. P212121.
#
# FIXME 20/NOV/06 do not want to go refining the standard error parameters
#                 in cases where there is radiation damage - this will cause
#                 nasty things to happen, since the spread really is larger
#                 than the errors. This is systematic! E.g. TS03.
# 
# ----- 28/NOV/06 implement 0-dose extrapolation if apropriate (i.e.
#                 multiplicity > say 6 and radiation damage detected)
#                 [(1) does not work with MAD
#                  (2) Phil E says no!]
#
# FIXME 28/NOV/06 implement feedback to the indexing from the pointgroup
#                 determination. See FIXME's in Scaler, Indexer, Integrater
#                 interface specifications.
#
# FIXED 30/NOV/06 need to limit the amount of data used to run pointless
#                 with - there should be no advantage in using more than
#                 180 degrees...
# 
# FIXED 04/DEC/06 move the working directory stuff to the interface definition.
#
# FIXME 05/DEC/06 need to make sure that there is no radiation damage before
#                 trying to optimise the error parameters. This includes
#                 between sweeps, and is a big and important thing! This could
#                 be done by looking at the overall Rmerge, or the highest
#                 resolution shell.
# 
# FIXED 02/DEC/08 need to make this more clever with the scaling model - this
#                 will mean testing it out... at the moment the Scala wrapper
#                 allows this by setting the secondary, cycles, tails and 
#                 b_factor can be set, using:
#
#                 scala.set_cycles(5)
#                 scala.set_scaling_parameters('rotation', 5, 4) - spacing, abs
#                 scala.set_bfactor(bfactor = True, brotation = 20.0)
#                 scala.set_tails(tails = False) - or True
# 
#                 This should not therefore be too hard to implement with the
#                 proper determination of a scaling model. Do I care about the
#                 convergence measurement? Should probably return this ...
#
#                 This will be implemented in a determine_best_scale_model
#                 method. This should work as follows:
#
#                 Test individual corrections. If any of them suck, don't use
#                 them in combinatorials otherwise give them a fair chance.
#                 Then use the simplest model which is as good as (i.e. within
#                 3% of, on average) the best model.

import os
import sys
import math
import copy
import shutil

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.Scaler import Scaler

from Wrappers.CCP4.CCP4Factory import CCP4Factory

from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Files import FileHandler
from Handlers.Citations import Citations
from Handlers.Flags import Flags        
from Handlers.Syminfo import Syminfo

# jiffys
from lib.Guff import is_mtz_file, nifty_power_of_ten, auto_logfiler
from lib.Guff import transpose_loggraph, nint
from lib.SymmetryLib import lattices_in_order

from CCP4ScalerHelpers import _resolution_estimate, \
     _prepare_pointless_hklin, _fraction_difference, \
     CCP4ScalerHelper

from CCP4InterRadiationDamageDetector import CCP4InterRadiationDamageDetector
from DoseAccumulate import accumulate

from AnalyseMyIntensities import AnalyseMyIntensities
from Experts.ResolutionExperts import determine_scaled_resolution

# See FIXME_X0001 below...
# from CCP4IntraRadiationDamageDetector import CCP4IntraRadiationDamageDetector

# newly implemented CCTBX powered functions to replace xia2 binaries
from Functions.add_dose_time_to_mtz import add_dose_time_to_mtz

class CCP4ScalerR(Scaler):
    '''An implementation of the Scaler interface using CCP4 programs.'''

    def __init__(self):
        Scaler.__init__(self)

        self._sweep_information = { }
        self._tmp_scaled_refl_files = { }
        self._wavelengths_in_order = []
        
        # hacky... this is to pass information from prepare to scale
        # and could probably be handled better (they used to be
        # all in just the scale() method)

        self._chef_analysis_groups = { }
        self._chef_analysis_times = { }
        self._chef_analysis_resolutions = { }

        self._resolution_limits = { }

        # flags to keep track of the corrections we will be applying

        self._scale_model_b = None
        self._scale_model_secondary = None
        self._scale_model_tails = None

        # useful handles...!

        self._prepared_reflections = None
        self._common_pname = None
        self._common_xname = None

        self._reference = None

        self._factory = CCP4Factory()
        self._helper = CCP4ScalerHelper()

        return

    # overloaded from the Scaler interface... to plumb in the factory
    
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        self._helper.set_working_directory(working_directory)        
        return

    # this is an overload from the factory - it returns Scala set up with
    # the desired corrections
    
    def _updated_scala(self):
        
        if not self._scalr_corrections:
            return self._factory.Scala()

        return self._factory.Scala(
            partiality_correction = self._scalr_correct_partiality,
            absorption_correction = self._scalr_correct_absorption,
            decay_correction = self._scalr_correct_decay)

    def _pointless_indexer_jiffy(self, hklin, indexer):
        return self._helper.pointless_indexer_jiffy(hklin, indexer)

    def _assess_scaling_model(self, tails, bfactor, secondary):
        
        epochs = sorted(self._sweep_information.keys())
        
        sc_tst = self._updated_scala()
        sc_tst.set_hklin(self._prepared_reflections)
        sc_tst.set_hklout('temp.mtz')
        
        sc_tst.set_tails(tails = tails)
        sc_tst.set_bfactor(bfactor = bfactor)

        if secondary:
            sc_tst.set_scaling_parameters(
                'rotation', secondary = Flags.get_scala_secondary())
        else:
            sc_tst.set_scaling_parameters('rotation', secondary = 0)

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            sc_tst.add_run(start, end, pname = input['pname'],
                           xname = input['xname'], dname = input['dname'],
                           exclude = False)
            
        if self.get_scaler_anomalous():
            sc_tst.set_anomalous()

        sc_tst.scale()

        data_tst = sc_tst.get_summary()

        # compute average Rmerge, number of cycles to converge - these are
        # what will form the basis of the comparison

        converge_tst = sc_tst.get_convergence()
        rmerges_tst = [data_tst[k]['Rmerge'][0] for k in data_tst]
        rmerge_tst = sum(rmerges_tst) / len(rmerges_tst)

        return rmerge_tst, converge_tst

    def _determine_best_scale_model(self):
        '''Determine the best set of corrections to apply to the data.'''

        # if we have already defined the best scaling model just return

        if self._scalr_corrections:
            return

        Debug.write('Optimising scaling corrections...')

        # central preparation stuff

        epochs = sorted(self._sweep_information.keys())

        # test corrections, compare Rmerge, accept if converge and helpful
        # shouldn't this be an eight-way comparison?

        partiality = True
        absorption = True
        decay = True

        rmerge_def, converge_def = self._assess_scaling_model(
            tails = False, bfactor = False, secondary = False)
                                                              
        rmerge_abs, converge_abs = self._assess_scaling_model(
            tails = False, bfactor = False, secondary = True)

        if ((rmerge_abs - rmerge_def) / rmerge_def) > 0.03:
            absorption = False
        if converge_abs - converge_def > 1.0:
            absorption = False

        # then test the partiality correction...

        rmerge_tails, converge_tails = self._assess_scaling_model(
            tails = True, bfactor = False, secondary = False)

        if ((rmerge_tails - rmerge_def) / rmerge_def) > 0.03:
            partiality = False
        if converge_tails - converge_def > 1.0:
            partiality = False

        # finally test the decay correction

        rmerge_decay, converge_decay  = self._assess_scaling_model(
            tails = False, bfactor = True, secondary = False)

        if ((rmerge_decay - rmerge_def) / rmerge_def) > 0.03:
            decay = False
        if converge_decay - converge_def > 1.0:
            decay = False

        # then summarise the choices...

        if absorption:
            Debug.write('Absorption correction: on')
        else:
            Debug.write('Absorption correction: off')

        if partiality:
            Debug.write('Partiality correction: on')
        else:
            Debug.write('Partiality correction: off')

        if decay:
            Debug.write('Decay correction: on')
        else:
            Debug.write('Decay correction: off')

        self._scalr_correct_absorption = absorption
        self._scalr_correct_partiality = partiality
        self._scalr_correct_decay = decay

        self._scalr_corrections = True

        # then add a brute-force analysis just to be sure... actually, this is
        # probably how the top level should be working anyhow?! #882

        if True:
            return

        results = { }

        for tails in True, False:
            for bfactor in True, False:
                for secondary in True, False:
                    rmerge, converge = self._assess_scaling_model(
                        tails = tails, bfactor = bfactor,
                        secondary = secondary)
                    results[(tails, bfactor, secondary)] = rmerge, converge

        for t, b, s in sorted(results):
            r, c = results[(t, b, s)]
            Debug.write('%s %s %s %.3f %.3f' % (t, b, s, r, c))

        return

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

        # I thought that this was all sorted?! FIXME #883

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
            resolution_used = self._sweep_information[epoch][
                'integrater'].get_integrater_high_resolution()

            # ok, in here decide the minimum distance from the beam centre to
            # the edge... which will depend on the size of the detector

            detector_width = header['size'][0] * header['pixel'][0] 
            detector_height = header['size'][1] * header['pixel'][1]

            # some debugging information to work out what is happening
            # for SFGH! /0 error...

            Debug.write('Detector dimensions: %d x %d' % tuple(header['size']))
            Debug.write('Pixel dimensions: %.5f %.5f' % tuple(header['pixel']))
            Debug.write('Beam centre: %.2f %.2f' % tuple(beam))
           
            radius = min([beam[0], detector_width - beam[0],
                          beam[1], detector_height - beam[1]])

            theta = 0.5 * math.atan(radius / distance)

            resolution_circle = wavelength / (2 * math.sin(theta))

            resolution = max(resolution_circle, resolution_used)

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
        '''Perform all of the preparation required to deliver the scaled
        data. This should sort together the reflection files, ensure that
        they are correctly indexed (via pointless) and generally tidy
        things up.'''

        # acknowledge all of the programs we are about to use...

        Citations.cite('pointless')
        Citations.cite('scala')
        Citations.cite('ccp4')

        # ---------- GATHER ----------

        self._sweep_information = { }

        Journal.block(
            'gathering', self.get_scaler_xcrystal().get_name(), 'CCP4',
            {'working directory':self.get_working_directory()})        

        # FIXME code review 4FEB10 - why is this not defined in terms of
        # another class? - these should be mediated by a new class
        # which could handle some of the book keeping which will follow.
        # Trac #884
        
        for epoch in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()
            sweep_name = intgr.get_integrater_sweep_name()
            self._sweep_information[epoch] = {
                'pname':pname,
                'xname':xname,
                'dname':dname,
                'batches':intgr.get_integrater_batches(),
                'integrater':intgr,
                'header':intgr.get_header(),
                'image_to_epoch':intgr.get_integrater_sweep(                
                ).get_image_to_epoch(),
                'image_to_dose':{},
                'batch_offset':0,
                'sweep_name':sweep_name
                }

            Journal.entry({'adding data from':'%s/%s/%s' % \
                           (xname, dname, sweep_name)})

        # gather data for all images which belonged to the parent
        # crystal - allowing for the fact that things could go wrong
        # e.g. epoch information not available, exposure times not in
        # headers etc...

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

            # FIXME shouldn't the journalling make some comment
            # here about whether this works or no? 4FEB10

        except RuntimeError, e:
            pass

        # next check through the reflection files that they are all MTZ
        # format - if not raise an exception.
        # FIXME this should include the conversion to MTZ.
        
        epochs = self._sweep_information.keys()

        for epoch in epochs:
            if not is_mtz_file(self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()):
                raise RuntimeError, \
                      'input file %s not MTZ format' % \
                      self._sweep_information[epoch][
                    'integrater'].get_integrater_reflections()

        # FIXME why is this global? 4FEB10 - in fact, why is this
        # test not performed in the scaler interface?

        self._common_pname = self._sweep_information[epochs[0]]['pname']
        self._common_xname = self._sweep_information[epochs[0]]['xname']

        # FIXME the checks in here need to be moved to an earlier
        # stage in the processing

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

        # ------------------------------------------------------------
        # FIXME ensure that the lattices are all the same - and if not
        # eliminate() them down until they are...
        # ------------------------------------------------------------

        need_to_return = False

        # is this correct or should it be run for all cases?
        # try for BA0296

        if len(self._sweep_information.keys()) > 1:

            lattices = []

            for epoch in self._sweep_information.keys():

                intgr = self._sweep_information[epoch]['integrater']
                hklin = intgr.get_integrater_reflections()
                indxr = intgr.get_integrater_indexer()

                # FIXME in here should check first if the pointgroup is
                # the one given by the user - if it is not available
                # despite being possible (i.e. pointless with give a
                # -ve Z score for a C2 case for an I222 lattice...)
                # it will be rejected perhaps... we don't want pointgroup.

                pointless_hklin = _prepare_pointless_hklin(
                    self.get_working_directory(),
                    hklin, self._sweep_information[epoch]['header'].get(
                    'phi_width', 0.0))
                
                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    pointless_hklin, indxr)

                lattice = Syminfo.get_lattice(pointgroup)

                if not lattice in lattices:
                    lattices.append(lattice)

                if ntr:

                    # FIXME bug # 3373 - if there is a need to reindex
                    # the lattice, I guess that the reindexing operator
                    # should not be conidered right? This is causing
                    # problems for TM0343_11636_2d where it seems
                    # quite capable of processing in C2221 and then
                    # reindexing to P21.

                    reindex_op = 'h,k,l'
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
                Chatter.write('Correct lattice asserted to be %s' % \
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
                        Chatter.write('Lattice %s ok for sweep %s' % \
                                      (correct_lattice, sname))
                    elif state == 'impossible':
                        raise RuntimeError, 'Lattice %s impossible for %s' \
                              % (correct_lattice, sname)
                    elif state == 'possible':
                        Chatter.write('Lattice %s assigned for sweep %s' % \
                                      (correct_lattice, sname))
                        need_to_return = True

        # if one or more of them was not in the lowest lattice,
        # need to return here to allow reprocessing

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        # need to merge the first reflection file in the "correct" pointgroup,
        # so that the others can be reindexed against this (if no reference)

        if self.get_scaler_reference_reflection_file():
            self._reference = self.get_scaler_reference_reflection_file()
            Chatter.write('Using HKLREF %s' % self._reference)
        elif Flags.get_reference_reflection_file():
            self._reference = Flags.get_reference_reflection_file()
            Chatter.write('Using HKLREF %s' % self._reference)
            
        if len(self._sweep_information.keys()) > 1 and \
               not self._reference:

            # ---------- PREPARE REFERENCE SET ----------
            
            # pointless it, sort it, quick scale it
            
            epochs = self._sweep_information.keys()
            epochs.sort()
            first = epochs[0]
            
            Debug.write('Preparing reference data set from first sweep')
            
            hklin = self._sweep_information[first][
                'integrater'].get_integrater_reflections()
            header = self._sweep_information[first]['header']
            
            # prepare pointless hklin makes something much smaller...
            
            pointless_hklin = _prepare_pointless_hklin(
                self.get_working_directory(),
                hklin, self._sweep_information[first]['header'].get(
                'phi_width', 0.0))
            
            pl = self._factory.Pointless()
            pl.set_hklin(pointless_hklin)
            pl.decide_pointgroup()

            # FIXME this does not appear to be really used...
            
            pointgroup = pl.get_pointgroup()
            reindex_op = pl.get_reindex_operator()
            
            integrater = self._sweep_information[first]['integrater']
            indexer = integrater.get_integrater_indexer()
            
            # FIXME in here may be getting the reference reflection file
            # from an external source, in which case I will want to do
            # something cunning in here...
            
            if indexer:

                # this should explode if the pointgroup is incompatible
                # with the lattice, right? through eliminate if the
                # lattice is user-assigned
                
                pointgroup, reindex_op, ntr = \
                            self._pointless_indexer_jiffy(
                    pointless_hklin, indexer)

                if ntr:
                    
                    # FIXME bug # 3373
                    
                    reindex_op = 'h,k,l'
                    
                    integrater.set_integrater_reindex_operator(
                        reindex_op, compose = False)
                    
                    need_to_return = True

            # FIXME_ABQ
            # compare pointgroup to the one which was given by the user,
            # forcing it to be so if necessary?

            Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            # OK, let's see what we can see. 

            if self._scalr_input_pointgroup:
                Debug.write('Using input pointgroup: %s' % \
                              self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup

            integrater.set_integrater_reindex_operator(reindex_op)
            integrater.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup))
            
            hklin = integrater.get_integrater_reflections()
            hklout = os.path.join(
                self.get_working_directory(),
                '%s_ref_srt.mtz' % os.path.split(hklin)[-1][:-4])
            
            # we will want to delete this one exit
            FileHandler.record_temporary_file(hklout)
            
            s = self._factory.Sortmtz()
            s.set_hklout(hklout)
            s.add_hklin(hklin)
            s.sort()
            
            # now quickly merge the reflections
            
            hklin = hklout
            self._reference = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('_ref_srt.mtz',
                                                 '_ref.mtz'))
            
            # need to remember this hklout - it will be the reference
            # reflection file for all of the reindexing below...
            
            Debug.write('Quickly scaling reference data set: %s' % \
                          os.path.split(hklin)[-1])
            Debug.write('to give indexing standard')
            
            qsc = self._updated_scala()
            qsc.set_hklin(hklin)
            qsc.set_hklout(self._reference)
            qsc.quick_scale()
            
            FileHandler.record_temporary_file(qsc.get_hklout())
            
        # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------

        # all should share the same pointgroup
        
        overall_pointgroup = None

        need_to_return = False
        
        for epoch in self._sweep_information.keys():
            
            hklin = self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()

            pointless_hklin = _prepare_pointless_hklin(
                self.get_working_directory(),
                hklin, self._sweep_information[epoch]['header'].get(
                'phi_width', 0.0))
            
            pl = self._factory.Pointless()
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))
            pl.set_hklin(pointless_hklin)

            # FIXME why am I doing this here above then again below?
            # surely this above is only worth doing if not indexer?
            # also prepare_pointless_hklin should be employed below.

            # we will want to delete this one exit
            FileHandler.record_temporary_file(hklout)

            pl.decide_pointgroup()

            # get the correct pointgroup etc.
            pointgroup = pl.get_pointgroup()
            reindex_op = pl.get_reindex_operator()

            # check this against the records in the indexer

            integrater = self._sweep_information[epoch]['integrater']
            indexer = integrater.get_integrater_indexer()

            # flag to record whether I need to do some rerunning
            rerun_pointless = False
            
            if indexer:

                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    pointless_hklin, indexer)

                if ntr:
                    
                    # FIXME bug # 3373
                    
                    reindex_op = 'h,k,l'
                    integrater.set_integrater_reindex_operator(
                        reindex_op, compose = False)

                    need_to_return = True

            # FIXME_ABQ
            # compare pointgroup to the one which was given by the user,
            # forcing it to be so if necessary?

            # OK, let's see what we can see. 

            if self._scalr_input_pointgroup:
                Debug.write('Using input pointgroup: %s' % \
                            self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup

            if not overall_pointgroup:
                overall_pointgroup = pointgroup
            if overall_pointgroup != pointgroup:
                raise RuntimeError, 'non uniform pointgroups'
            
            Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            integrater.set_integrater_reindex_operator(reindex_op)
            integrater.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup))
            
        # if the pointgroup comparison above results in a need to
        # re-reduce the data then allow for this...

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        if self._reference:

            # run an MTZDUMP on self._reference to get the cell parameters
            # and lattice (pointgroup)

            md = self._factory.Mtzdump()
            md.set_hklin(self._reference)
            md.dump()

            # check that HKLREF is merged... and that it contains only one
            # dataset

            if md.get_batches():
                raise RuntimeError, 'reference reflection file %s unmerged' % \
                      self._reference

            datasets = md.get_datasets()

            # ok I should really allow multiple data sets in here,
            # just take the measurements from the first... also need to
            # find a sensible column to use too...

            if len(datasets) > 1 and False:
                raise RuntimeError, 'more than one dataset in %s' % \
                      self._reference
            
            # then get the unit cell, lattice etc.

            reference_lattice = Syminfo.get_lattice(md.get_spacegroup())
            reference_cell = md.get_dataset_info(datasets[0])['cell']
            
            # then compute the pointgroup from this...

            # ---------- REINDEX TO CORRECT (REFERENCE) SETTING ----------
            
            for epoch in self._sweep_information.keys():
                pl = self._factory.Pointless()
                hklin = self._sweep_information[epoch][
                    'integrater'].get_integrater_reflections()

                pl.set_hklin(_prepare_pointless_hklin(
                    self.get_working_directory(),
                    hklin, self._sweep_information[epoch]['header'].get(
                    'phi_width', 0.0)))

                hklout = os.path.join(
                    self.get_working_directory(),
                    '%s_rdx2.mtz' % os.path.split(hklin)[-1][:-4])

                # we will want to delete this one exit
                FileHandler.record_temporary_file(hklout)

                # now set the initial reflection set as a reference...
            
                pl.set_hklref(self._reference)

                # write a pointless log file...
                pl.decide_pointgroup()

                Debug.write('Reindexing analysis of %s' % pl.get_hklin())
                
                # FIXED here - do I need to contemplate reindexing
                # the reflections? if not, don't bother - could be an
                # expensive waste of time for large reflection files
                # (think Ed Mitchell data...) - delegated to the Integrater
                # to manage...
                
                # get the correct pointgroup etc - though the pointgroup
                # should not be used and should the same as is already set...
                # right??
                pointgroup = pl.get_pointgroup()
                reindex_op = pl.get_reindex_operator()
                
                Debug.write('Operator: %s' % reindex_op)

                # apply this...

                integrater = self._sweep_information[epoch]['integrater']
                
                integrater.set_integrater_reindex_operator(reindex_op)
                integrater.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))

                # FIXME in here want to check that the unit cell comes out
                # isomorphous... that is, check that the pointgroup and
                # unit cell are about the same as what came out from the
                # MTZDUMP above.

                md = self._factory.Mtzdump()
                md.set_hklin(integrater.get_integrater_reflections())
                md.dump()

                datasets = md.get_datasets()
                
                if len(datasets) > 1:
                    raise RuntimeError, 'more than one dataset in %s' % \
                          integrater.get_integrater_reflections()
            
                # then get the unit cell, lattice etc.
                
                lattice = Syminfo.get_lattice(md.get_spacegroup())
                cell = md.get_dataset_info(datasets[0])['cell']

                if lattice != reference_lattice:
                    raise RuntimeError, 'lattices differ in %s and %s' % \
                          (self._reference,
                           integrater.get_integrater_reflections())

                # check that the cell is isomorphous - that is, it
                # differs by < 10% from the reference one

                for j in range(6):
                    if math.fabs((cell[j] - reference_cell[j]) /
                                 reference_cell[j]) > 0.1:
                        raise RuntimeError, \
                              'unit cell parameters differ in %s and %s' % \
                              (self._reference,
                               integrater.get_integrater_reflections())

                # ok if we get to here then we are fairly happy
                
        # ---------- SORT TOGETHER DATA ----------
            
        max_batches = 0
        
        for epoch in self._sweep_information.keys():

            # keep a count of the maximum number of batches in a block -
            # this will be used to make rebatch work below.

            hklin = self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()

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

        Debug.write('Biggest sweep has %d batches' % max_batches)
        max_batches = nifty_power_of_ten(max_batches)
    
        # then rebatch the files, to make sure that the batch numbers are
        # in the same order as the epochs of data collection.

        epochs = self._sweep_information.keys()
        epochs.sort()

        counter = 0

        for epoch in epochs:
            rb = self._factory.Rebatch()

            hklin = self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()

            pname = self._sweep_information[epoch]['pname']
            xname = self._sweep_information[epoch]['xname']
            dname = self._sweep_information[epoch]['dname']

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_%s_%d.mtz' % \
                                  (pname, xname, dname, counter))

            FileHandler.record_temporary_file(hklout)

            # record this for future reference - will be needed in the
            # radiation damage analysis...
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

        # now output a doser input file - just for kicks ;o)

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

        Debug.write('Wrote DOSER information to %s' % \
                    os.path.join(self.get_working_directory(), 'doser.in'))

        s = self._factory.Sortmtz()

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted.mtz' % \
                              (self._common_pname, self._common_xname))

        
        s.set_hklout(hklout)

        for epoch in epochs:
            s.add_hklin(self._sweep_information[epoch]['hklin'])

        s.sort()

        # verify that the measurements are in the correct setting
        # choice for the spacegroup

        hklin = hklout
        hklout = hklin.replace('sorted.mtz', 'temp.mtz')

        if not self.get_scaler_reference_reflection_file():

            p = self._factory.Pointless()

            FileHandler.record_log_file('%s %s pointless' % \
                                        (self._common_pname,
                                         self._common_xname),
                                        p.get_log_file())

            if len(self._sweep_information.keys()) > 1:
                p.set_hklin(hklin)
            else:
                # permit the use of pointless preparation...
                epoch = self._sweep_information.keys()[0]
                p.set_hklin(_prepare_pointless_hklin(
                    self.get_working_directory(),
                    hklin, self._sweep_information[epoch]['header'].get(
                    'phi_width', 0.0)))

            if self._scalr_input_spacegroup:
                Debug.write('Assigning user input spacegroup: %s' % \
                            self._scalr_input_spacegroup)

                p.decide_spacegroup()
                spacegroup = p.get_spacegroup()
                reindex_operator = p.get_spacegroup_reindex_operator()

                Debug.write('Pointless thought %s (reindex as %s)' % \
                            (spacegroup, reindex_operator))

                spacegroup = self._scalr_input_spacegroup
                reindex_operator = 'h,k,l'

            else:
                p.decide_spacegroup()
                spacegroup = p.get_spacegroup()
                reindex_operator = p.get_spacegroup_reindex_operator()

                Debug.write('Pointless thought %s (reindex as %s)' % \
                            (spacegroup, reindex_operator))
                            
            if self._scalr_input_spacegroup:
                self._scalr_likely_spacegroups = [self._scalr_input_spacegroup]
            else:
                self._scalr_likely_spacegroups = p.get_likely_spacegroups()

            Chatter.write('Likely spacegroups:')
            for spag in self._scalr_likely_spacegroups:
                Chatter.write('%s' % spag)

            Chatter.write(
                'Reindexing to first spacegroup setting: %s (%s)' % \
                (spacegroup, reindex_operator))

        else:

            md = self._factory.Mtzdump()
            md.set_hklin(self.get_scaler_reference_reflection_file())
            md.dump()

            spacegroup = md.get_spacegroup()
            reindex_operator = 'h,k,l'

            self._scalr_likely_spacegroups = [spacegroup]

            Debug.write('Assigning spacegroup %s from reference' % \
                        spacegroup)

        # then run reindex to set the correct spacegroup
        
        ri = self._factory.Reindex()
        ri.set_hklin(hklin)
        ri.set_hklout(hklout)
        ri.set_spacegroup(spacegroup)
        ri.set_operator(reindex_operator)
        ri.reindex()
        
        # we will want to delete this one exit
        FileHandler.record_temporary_file(hklout)
        
        # then resort the reflections (one last time!)

        s = self._factory.Sortmtz()

        temp = hklin
        hklin = hklout
        hklout = temp

        s.add_hklin(hklin)
        s.set_hklout(hklout)

        s.sort()

        # done preparing!

        self._prepared_reflections = s.get_hklout()

        self._resolution_limits = { }

        return

    def _refine_sd_parameters_remerge(self, scales_file,
                                      sdadd_f, sdb_f,
                                      sdadd_p, sdb_p):
        '''Actually compute the RMS deviation from scatter / sigma = 1.0
        from the scales.'''
        
        epochs = self._sweep_information.keys()
        epochs.sort()

        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        sc.add_sd_correction('full', 2.0, sdadd_f, sdb_f)
        sc.add_sd_correction('partial', 2.0, sdadd_p, sdb_p)
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(), 'temp.mtz'))

        # FIXME this needs to be set only is we have f', f'' values
        # for the wavelength

        # bug # 2326

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.scale()
        loggraph = sc.parse_ccp4_loggraph()

        standard_deviation_info = { }

        for key in loggraph.keys():
            if 'standard deviation v. Intensity' in key:
                dataset = key.split(',')[-1].strip()
                standard_deviation_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # compute an RMS sigma...

        score_full = 0.0
        ref_count_full = 0

        score_partial = 0.0
        ref_count_partial = 0

        for dataset in standard_deviation_info.keys():
            info = standard_deviation_info[dataset]

            # need to consider partials separately to fulls in assigning
            # the error correction parameters

            for j in range(len(info['1_Range'])):

                # the format of the output changed with versions
                # 3.3.x I think - cope with this here...
                # bug # 2714
                
                n_full = int(info['5_Number'][j])
                I_full = float(info['4_Irms'][j])
                if n_full > 0 and info['7_SigmaFull'][j] != '-':
                    s_full = float(info['7_SigmaFull'][j])
                else:
                    s_full = 0.0

                if info.has_key('9_Number'):

                    n_partial = int(info['9_Number'][j])
                    I_partial = float(info['8_Irms'][j])
                    s_partial = float(info['11_SigmaPartial'][j])

                else:

                    n_partial = int(info['12_Number'][j])
                    I_partial = float(info['11_Irms'][j])
                    s_partial = float(info['14_SigmaPartial'][j])                
                n_tot = n_full + n_partial

                # trap case where we have no reflections in a higher
                # intensity bin (one may ask why they are being printed
                # by Scala, then?)

                if n_tot:
                    i_tot = ((n_full * I_full) +
                             (n_partial * I_partial)) / n_tot
                    s_tot = ((n_full * s_full) +
                             (n_partial * s_partial)) / n_tot
                else:
                    i_tot = 0.0
                    s_tot = 1.0

                # trying to minimise difference between this and 1.0!
                
                s_full -= 1.0
                s_partial -= 1.0

                score_full += s_full * s_full * n_full
                ref_count_full += n_full

                score_partial += s_partial * s_partial * n_partial
                ref_count_partial += n_partial

            # compute the scores...

            if ref_count_full > 0:
                score_full /= ref_count_full

            if ref_count_partial > 0:
                score_partial /= ref_count_partial

        return math.sqrt(score_full), \
               math.sqrt(score_partial)

    def _refine_sd_parameters(self, scales_file):
        '''To some repeated merging (it is assumed that the data have
        already ben scaled) to determine appropriate values of
        sd_add, sd_fac, sd_b for fulls, partials. FIXME at some point
        this should probably be for each run as well...'''

        best_sdadd_full = 0.0
        best_sdadd_partial = 0.0
        best_sdb_full = 0.0
        best_sdb_partial = 0.0

        max_sdb_full = 20.0
        max_sdb_partial = 20.0
        step_sdb_full = 2.0

        max_sdadd_full = 0.1
        max_sdadd_partial = 0.1

        step_sdadd_full = 0.01
        step_sdadd_partial = 0.01

        sdadd_full = 0.0
        sdadd_partial = 0.0
        sdb_full = 0.0
        sdb_partial = 0.0

        best_rms_full = 1.0e9
        best_rms_partial = 1.0e9

        # compute sd_add first, then sdb, then sdadd

        while sdadd_full < max_sdadd_full:
            
            sdadd_partial = sdadd_full

            rms_full, rms_partial = self._refine_sd_parameters_remerge(
                scales_file, sdadd_full, sdb_full, sdadd_partial, sdb_partial)

            Debug.write('Tested SdAdd %4.2f: %4.2f %4.2f' % \
                        (sdadd_full, rms_full, rms_partial))

            if rms_full < best_rms_full:
                best_sdadd_full = sdadd_full
                best_rms_full = rms_full

            if rms_partial < best_rms_partial:
                best_sdadd_partial = sdadd_partial
                best_rms_partial = rms_partial

            if rms_full > best_rms_full and rms_partial > best_rms_partial:
                break

            sdadd_full += step_sdadd_full

        best_rms_full = 1.0e9
        best_rms_partial = 1.0e9

        # then compute sdb ...

        while sdb_full < max_sdb_full:

            sdb_partial = sdb_full

            rms_full, rms_partial = self._refine_sd_parameters_remerge(
                scales_file, best_sdadd_full, sdb_full,
                best_sdadd_partial, sdb_partial)

            Debug.write('Tested SdB %4.1f: %4.2f %4.2f' % \
                        (sdb_full, rms_full, rms_partial))

            if rms_full < best_rms_full:
                best_sdb_full = sdb_full
                best_rms_full = rms_full

            if rms_partial < best_rms_partial:
                best_sdb_partial = sdb_partial
                best_rms_partial = rms_partial

            if rms_full > best_rms_full and rms_partial > best_rms_partial:
                break

            sdb_full += step_sdb_full

        sdadd_full = 0.0
        best_rms_full = 1.0e9
        best_rms_partial = 1.0e9
        
        while sdadd_full < max_sdadd_full:
            
            sdadd_partial = sdadd_full

            rms_full, rms_partial = self._refine_sd_parameters_remerge(
                scales_file, sdadd_full, best_sdb_full,
                sdadd_partial, best_sdb_partial)

            Debug.write('Tested SdAdd %4.2f: %4.2f %4.2f' % \
                        (sdadd_full, rms_full, rms_partial))

            if rms_full < best_rms_full:
                best_sdadd_full = sdadd_full
                best_rms_full = rms_full

            if rms_partial < best_rms_partial:
                best_sdadd_partial = sdadd_partial
                best_rms_partial = rms_partial

            if rms_full > best_rms_full and rms_partial > best_rms_partial:
                break

            sdadd_full += step_sdadd_full

        Chatter.write('Optimised SD corrections (A, B) found to be:')
        Chatter.write('Full:       %4.2f   %4.1f' %
                      (best_sdadd_full, best_sdb_full))
        Chatter.write('Partial:    %4.2f   %4.1f' %
                      (best_sdadd_partial, best_sdb_partial))


        return best_sdadd_full, best_sdb_full, \
               best_sdadd_partial, best_sdb_partial

    def _scale(self):
        '''Perform all of the operations required to deliver the scaled
        data.'''

        epochs = self._sweep_information.keys()
        epochs.sort()

        if Flags.get_smart_scaling():
            self._determine_best_scale_model()

        if self._scalr_corrections:
            Journal.block(
                'scaling', self.get_scaler_xcrystal().get_name(), 'CCP4',
                {'scaling model':'automatic',
                 'absorption':self._scalr_correct_absorption,
                 'tails':self._scalr_correct_partiality,
                 'decay':self._scalr_correct_decay
                 })

        else:
            Journal.block(
                'scaling', self.get_scaler_xcrystal().get_name(), 'CCP4',
                {'scaling model':'default'})
        
        if Flags.get_chef():
            self._sweep_information_to_chef()
            self._decide_chef_cutoff_epochs()
            
        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)

        scales_file = '%s.scales' % self._common_xname

        sc.set_new_scales_file(scales_file)

        user_resolution_limits = { }

        for epoch in epochs:

            input = self._sweep_information[epoch]

            start, end = (min(input['batches']), max(input['batches']))

            if input['dname'] in self._resolution_limits:
                resolution = self._resolution_limits[input['dname']]
                sc.add_run(start, end, pname = input['pname'],
                           xname = input['xname'],
                           dname = input['dname'],
                           exclude = False,
                           resolution = resolution)
            else:
                sc.add_run(start, end, pname = input['pname'],
                           xname = input['xname'],
                           dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        # FIXME this needs to be set only is we have f', f'' values
        # for the wavelength
        
        # bug # 2326
        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.scale()

        # then gather up all of the resulting reflection files
        # and convert them into the required formats (.sca, .mtz.)

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()
        
        resolution_info = { }

        # this returns a dictionary of files that I will use to calculate
        # the resolution limits...
        
        reflection_files = sc.get_scaled_reflection_files()

        for key in loggraph.keys():
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

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
            
            resolution = determine_scaled_resolution(
                reflection_files[dataset], 
                Flags.get_i_over_sigma_limit())[1]

            if not dataset in self._resolution_limits:
                self._resolution_limits[dataset] = resolution
                self.set_scaler_done(False)

            if resolution < highest_resolution:
                highest_resolution = resolution

            Chatter.write('Resolution limit for %s: %5.2f' % \
                          (dataset, self._resolution_limits[dataset]))

        self._scalr_highest_resolution = highest_resolution

        Debug.write('Scaler highest resolution set to %5.2f' % \
                    highest_resolution)
        
        if not self.get_scaler_done():
            Debug.write('Returning as scaling not finished...')
            return

        batch_info = { }
        
        for key in loggraph.keys():
            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                batch_info[dataset] = transpose_loggraph(
                    loggraph[key])

        average_completeness = 0.0

        for k in data.keys():
            average_completeness += data[k]['Completeness'][0]
        average_completeness /= len(data.keys())

        if Flags.get_quick():
            Debug.write('Quick, so not optimising error parameters')
            sdadd_full = 0.02
            sdb_full = 0.0
            sdadd_partial = 0.02
            sdb_partial = 0.0

        elif average_completeness < 50.0:
            Debug.write('Incomplete data, so not refining error parameters')
            sdadd_full = 0.02
            sdb_full = 0.0
            sdadd_partial = 0.02
            sdb_partial = 0.0

        else:

            Debug.write('Optimising error parameters')
            
            sdadd_full, sdb_full, sdadd_partial, sdb_partial = \
                        self._refine_sd_parameters(scales_file)

            try:
                os.remove(os.path.join(self.get_working_directory(),
                                       scales_file))
            except:
                Debug.write('Error removing %s' % scales_file)

        sc = self._updated_scala()

        FileHandler.record_log_file('%s %s scala' % (self._common_pname,
                                                     self._common_xname),
                                    sc.get_log_file())

        sc.set_resolution(self._scalr_highest_resolution)

        sc.set_hklin(self._prepared_reflections)
        
        scales_file = '%s_final.scales' % self._common_xname

        sc.set_new_scales_file(scales_file)

        sc.add_sd_correction('full', 2.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 2.0, sdadd_partial, sdb_partial)

        open(os.path.join(
            self.get_working_directory(),
            'sweep_info.xia'), 'w').write(str(self._sweep_information))
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            run_resolution_limit = self._resolution_limits[input['dname']]

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit)

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.scale()

        Debug.write('Convergence at: %.1f cycles' % sc.get_convergence())

        for dataset in resolution_info.keys():
            if False:
                print dataset
                determine_scaled_resolution(
                    reflection_files[dataset], 3.0)[1]

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()

        standard_deviation_info = { }

        for key in loggraph.keys():
            if 'standard deviation v. Intensity' in key:
                dataset = key.split(',')[-1].strip()
                standard_deviation_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # write this in an interesting way...

        for dataset in standard_deviation_info.keys():
            info = standard_deviation_info[dataset]

            # need to consider partials separately to fulls in assigning
            # the error correction parameters
            
            for j in range(len(info['1_Range'])):            

                n_full = int(info['5_Number'][j])
                I_full = float(info['4_Irms'][j])
                if n_full > 0 and info['7_SigmaFull'][j] != '-':
                    s_full = float(info['7_SigmaFull'][j])
                else:
                    s_full = 0.0
                
                if info.has_key('9_Number'):
                
                    n_part = int(info['9_Number'][j])
                    I_part = float(info['8_Irms'][j])
                    s_part = float(info['11_SigmaPartial'][j])
                    
                else:
                    
                    n_part = int(info['12_Number'][j])
                    I_part = float(info['11_Irms'][j])
                    s_part = float(info['14_SigmaPartial'][j])
                
                n_tot = n_full + n_part

                i_tot = ((n_full * I_full) + (n_part * I_part)) / n_tot
                s_tot = ((n_full * s_full) + (n_part * s_part)) / n_tot

        resolution_info = { }

        for key in loggraph.keys():
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

        batch_info = { }
        
        for key in loggraph.keys():
            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                batch_info[dataset] = transpose_loggraph(
                    loggraph[key])

        sd_factors = sc.get_sd_factors()

        Debug.write('Standard deviation factors')

        for run in sorted(sd_factors.keys()):
            record = [run] + list(sd_factors[run])
            Debug.write('Run %d: %.3f %.3f %.3f %.3f %.3f %.3f' % \
                        tuple(record))

        # finally put all of the results "somewhere useful"
        
        self._scalr_statistics = data

        self._tmp_scaled_refl_files = copy.deepcopy(
            sc.get_scaled_reflection_files())

        self._scalr_scaled_reflection_files = { }
        self._scalr_scaled_reflection_files['sca'] = { }
        
        for key in self._tmp_scaled_refl_files:
            file = self._tmp_scaled_refl_files[key]
            scaout = '%s.sca' % file[:-4]
            
            m2v = self._factory.Mtz2various()
            m2v.set_hklin(file)
            m2v.set_hklout(scaout)
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][key] = scaout

            FileHandler.record_data_file(scaout)

        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        sc.add_sd_correction('full', 2.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 2.0, sdadd_partial, sdb_partial)

        self._wavelengths_in_order = []
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            run_resolution_limit = self._resolution_limits[input['dname']]

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit)
            if not input['dname'] in self._wavelengths_in_order:
                self._wavelengths_in_order.append(input['dname'])
            
        sc.set_hklout(os.path.join(self.get_working_directory(), 'temp.mtz'))
        sc.set_scalepack(os.path.join(self.get_working_directory(),
                                      '%s_%s_unmerged.sca' % \
                                      (self._common_pname,
                                       self._common_xname)))

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.scale()

        self._scalr_scaled_reflection_files['sca_unmerged'] = { }
        for key in self._tmp_scaled_refl_files:
            file = self._tmp_scaled_refl_files[key]
            scalepack = os.path.join(os.path.split(file)[0],
                                     os.path.split(file)[1].replace(
                '_scaled', '_unmerged').replace('.mtz', '.sca'))
            self._scalr_scaled_reflection_files['sca_unmerged'][
                key] = scalepack
            FileHandler.record_data_file(scalepack)

        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        self._wavelengths_in_order = []
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            run_resolution_limit = self._resolution_limits[input['dname']]

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit)
            if not input['dname'] in self._wavelengths_in_order:
                self._wavelengths_in_order.append(input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_chef.mtz' % \
                                   (self._common_pname,
                                    self._common_xname)))
        
        sc.set_chef_unmerged(True)

        sc.add_sd_correction('full', 2.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 2.0, sdadd_partial, sdb_partial)

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.scale()

        reflection_files = sc.get_scaled_reflection_files()

        # perpare the dose profiles (again) - N.B. now don't need to do
        # this as the actual command reads the doser.in file - should
        # remove this from the API for Doser then really. N.B. do use
        # the doses though...

        doses = { }

        for epoch in self._sweep_information.keys():
            i2d = self._sweep_information[epoch]['image_to_dose']
            i2e = self._sweep_information[epoch]['image_to_epoch']
            offset = self._sweep_information[epoch]['batch_offset']
            images = sorted(i2d.keys())
            for i in images:
                batch = i + offset
                doses[batch] = i2d[i]

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
                hklin = reflection_files[wave]
                rb = self._factory.Rebatch()
                rb.set_hklin(hklin)
                rb.set_hklout(hklout)
                rb.limit_batches(start, end)

                if not wave in bits:
                    bits[wave] = [hklout_all]
                bits[wave].append(hklout)
                FileHandler.record_temporary_file(hklout)
                # FileHandler.record_temporary_file(hklout_all)
                
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

        # FIXME ALSO need to copy the harvest information in this cycle
        # as this is where we get the right harvest files for each
        # wavelength...

        # finally repeat the merging again (!) but keeping the
        # wavelengths separate to generate the statistics on a
        # per-wavelength basis - note that we do not want the
        # reflection files here... bug# 2229

        for key in self._scalr_statistics:
            pname, xname, dname = key

            # we need to copy the harvest file we are generating from this
            # to allow storage of proper stats...

            harvest_copy = os.path.join(os.environ['HARVESTHOME'],
                                        'DepositFiles', pname,
                                        '%s.scala' % dname)

            sc = self._updated_scala()
            sc.set_hklin(self._prepared_reflections)
            sc.set_scales_file(scales_file)

            sc.add_sd_correction('full', 2.0, sdadd_full, sdb_full)
            sc.add_sd_correction('partial', 2.0, sdadd_partial, sdb_partial)
        
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
                
            # sc.set_tails()
            sc.scale()
            stats = sc.get_summary()

            # this should just work ... by magic!
            self._scalr_statistics[key] = stats[key]

            # now copy the harvest file

            shutil.copyfile(harvest_copy, '%s.keep' % harvest_copy)

            Debug.write('Copying %s to %s' % \
                        (harvest_copy, '%s.keep' % harvest_copy))

        # end bug # 2229 stuff

        # now move the .keep harvest files back

        for key in self._scalr_statistics:
            pname, xname, dname = key

            harvest_copy = os.path.join(os.environ['HARVESTHOME'],
                                        'DepositFiles', pname,
                                        '%s.scala' % dname)

            shutil.move('%s.keep' % harvest_copy, harvest_copy)
            Debug.write('Moving %s to %s' % \
                        ('%s.keep' % harvest_copy, harvest_copy))
            
        return

    def _scale_finish_ami(self):
        '''Finish off the scaling, this time using AMI.'''

        ami = AnalyseMyIntensities()
        ami.set_working_directory(self.get_working_directory())

        for wavelength in self._wavelengths_in_order:
            hklin = self._tmp_scaled_refl_files[wavelength]
            ami.add_hklin(hklin)

        if self.get_scaler_anomalous():
            ami.set_anomalous(True)

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_free.mtz' % (self._common_pname,
                                                  self._common_xname))

        ami.set_hklout(hklout)

        ami.analyse_input_hklin()
        ami.merge_analyse()

        # get the results out...

        truncate_statistics = ami.get_truncate_statistics()

        for k in truncate_statistics.keys():
            j, project_info = k
            self._scalr_statistics[project_info][
                'Wilson B factor'] = truncate_statistics[k]['Wilson B factor']

        FileHandler.record_data_file(hklout)

        return

    def _scale_finish(self):
        '''Finish off the scaling... This needs to be replaced with a
        call to AMI.'''

        # convert I's to F's in Truncate

        if not Flags.get_small_molecule():

            for key in self._tmp_scaled_refl_files.keys():
                file = self._tmp_scaled_refl_files[key]
                t = self._factory.Truncate()
                t.set_hklin(file)
                
                # bug # 2326
                if self.get_scaler_anomalous():
                    t.set_anomalous(True)
                else:
                    t.set_anomalous(False)

                # this is tricksy - need to really just replace the last
                # instance of this string FIXME 27/OCT/06

                FileHandler.record_log_file('%s %s %s truncate' % \
                                            (self._common_pname,
                                             self._common_xname,
                                             key),
                                            t.get_log_file())

                hklout = ''
                for path in os.path.split(file)[:-1]:
                    hklout = os.path.join(hklout, path)
                hklout = os.path.join(hklout, os.path.split(file)[-1].replace(
                    '_scaled', '_truncated'))

                FileHandler.record_temporary_file(hklout)

                t.set_hklout(hklout)
                t.truncate()

                b_factor = t.get_b_factor()

                # look for the second moment information...
                moments = t.get_moments()

                # record the b factor somewhere (hopefully) useful...

                self._scalr_statistics[
                    (self._common_pname, self._common_xname, key)
                    ]['Wilson B factor'] = [b_factor]

                # replace old with the new version which has F's in it 
                self._tmp_scaled_refl_files[key] = hklout

                # record the separated reflection file too
                # 01MAR07 no longer have this
                # self._scalr_scaled_reflection_files['mtz'][key] = hklout

        # standardise the unit cells and relabel each of the columns in
        # each reflection file appending the DNAME to the column name

        # compute a standard unit cell here - this should be equal to
        # an average of the unit cells in each of the reflection files,
        # weighted according to (1) the number of reflections and
        # perhaps (2) the epoch order of that data set...

        # FIXME 08/DEC/06 in some cases e.g. when you have a wider range
        # of wavelengths the criterion in here is rather strict - that is,
        # the unit cell parameters could vary by more if you have a factor
        # of say 2 between different wavelengths.

        average_cell_a = 0.0
        average_cell_b = 0.0
        average_cell_c = 0.0
        average_cell_alpha = 0.0
        average_cell_beta = 0.0
        average_cell_gamma = 0.0

        average_cell_nref = 0

        # in here I want to go through and dump out all of the information
        # first and then go through again and compute the average unit
        # cell values and so on, because then I can take into account the
        # spread of wavelength values. See bug # 1757.

        ami = AnalyseMyIntensities()
        ami.set_working_directory(self.get_working_directory())

        average_unit_cell, ignore_sg = ami.compute_average_cell(
            [self._tmp_scaled_refl_files[key] for key in
             self._tmp_scaled_refl_files.keys()])

        Chatter.write('Computed average unit cell (will use in all files)')
        Chatter.write('%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                      average_unit_cell)

        self._scalr_cell = average_unit_cell

        for key in self._tmp_scaled_refl_files.keys():
            file = self._tmp_scaled_refl_files[key]
            
            hklout = '%s_cad.mtz' % file[:-4]
            FileHandler.record_temporary_file(hklout)

            c = self._factory.Cad()
            c.add_hklin(file)
            c.set_new_suffix(key)
            c.set_new_cell(average_unit_cell)
            c.set_hklout(hklout)
            c.update()
            
            self._tmp_scaled_refl_files[key] = hklout

        # merge all columns into a single uber-reflection-file
        # FIXME this is only worth doing if there are more
        # than one scaled reflection file...

        if len(self._tmp_scaled_refl_files.keys()) > 1:

            # FIXME these need to be added in in epoch
            # order (to make the radiation damage analysis
            # meaningful...)

            c = self._factory.Cad()
            for key in self._tmp_scaled_refl_files.keys():
                file = self._tmp_scaled_refl_files[key]
                c.add_hklin(file)
        
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_merged.mtz' % (self._common_pname,
                                                        self._common_xname))

            Debug.write('Merging all data sets to %s' % hklout)

            c.set_hklout(hklout)
            c.merge()
            
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
        # file with the free column added. FIXME this may need to be
        # copied from a user-supplied reference reflection file...

        # ok, this is now being fixed! if Flags.get_freer_file() is not None
        # then go for it!

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

        if not Flags.get_small_molecule():
        
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

            # next have a look for radiation damage...
            # if more than one wavelength
            
            if len(self._tmp_scaled_refl_files.keys()) > 1:
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
                Chatter.banner('Local Scaling %s' % self._common_xname)
                for s in status:
                    Chatter.write('%s %s' % s)
                Chatter.banner('')       

        return
    
