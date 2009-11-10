#!/usr/bin/env python
# CCP4ScalerImplementation.py
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
# FIXME 02/DEC/08 need to make this more clever with the scaling model - this
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

from CCP4ScalerImplementationHelpers import _resolution_estimate, \
     _prepare_pointless_hklin, _fraction_difference, \
     CCP4ScalerImplementationHelper

from CCP4InterRadiationDamageDetector import CCP4InterRadiationDamageDetector
from DoseAccumulate import accumulate

from AnalyseMyIntensities import AnalyseMyIntensities
from Experts.ResolutionExperts import determine_scaled_resolution

# See FIXME_X0001 below...
# from CCP4IntraRadiationDamageDetector import CCP4IntraRadiationDamageDetector

# newly implemented CCTBX powered functions to replace xia2 binaries
from Functions.add_dose_time_to_mtz import add_dose_time_to_mtz

class CCP4Scaler(Scaler):
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

        # ok, in here need to keep track of the best scaling model to use
        # when I come to make that decision - FIXME... ok - it looks like
        # I can code this up in a proper component fashion as the Scala
        # wrapper provides a decent interface. If all three of the following
        # are None then this has not been set, else we have already defined
        # a scaling model so we can crack on and use it. Assert: the
        # scaling model applies only to actually scaling the data. Assert:
        # we will be using smoothed rotation scaling over 5 degree intervals.
        # Assert: the predicted number of cycles is not overly important.

        self._scale_model_b = None
        self._scale_model_secondary = None
        self._scale_model_tails = None

        self._prepared_reflections = None
        self._common_pname = None
        self._common_xname = None

        self._reference = None

        self._factory = CCP4Factory()
        self._helper = CCP4ScalerImplementationHelper()

        return

    # This is overloaded from the Scaler interface...
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        self._helper.set_working_directory(working_directory)        
        return

    # this is an overload from the factory

    def _updated_scala(self):
        
        if not self._scalr_corrections:
            # Debug.write('Scala factory: default scala')
            return self._factory.Scala()

        # Debug.write('Scala factory: modified scala')
        # Debug.write('Partiality %s Absorption %s Decay %s' % \
        # (self._scalr_correct_partiality,
        # self._scalr_correct_absorption,
        # self._scalr_correct_decay))
        
        return self._factory.Scala(
            partiality_correction = self._scalr_correct_partiality,
            absorption_correction = self._scalr_correct_absorption,
            decay_correction = self._scalr_correct_decay)

    def _pointless_indexer_jiffy(self, hklin, indexer):
        return self._helper.pointless_indexer_jiffy(hklin, indexer)

    def _assess_scaling_model(self, tails, bfactor, secondary):
        # finally test the decay correction
        
        epochs = sorted(self._sweep_information.keys())
        
        sc_tst = self._updated_scala()
        sc_tst.set_hklin(self._prepared_reflections)
        sc_tst.set_hklout('temp.mtz')
        
        sc_tst.set_tails(tails = tails)
        sc_tst.set_bfactor(bfactor = bfactor)

        if secondary:
            sc_tst.set_scaling_parameters('rotation', secondary = 6)
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

        # this will test out the individual corrections and compare the
        # results (average Rmerge, convergence rate) with the option of
        # just running a very simple scaling (scales rotation spacing 5)
        # to see if they justify their existence. By default the corrections
        # are "on"...

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

        # full fat, with and without tails correction (ff, fft)

        play = False
        if play:

            rmerge_ff, converge_ff = self._assess_scaling_model(
                tails = False, bfactor = True, secondary = True)
            rmerge_fft, converge_fft = self._assess_scaling_model(
                tails = True, bfactor = True, secondary = True)

            Debug.write(
                'Scaling optimisation: simpl tails absor decay  all  all+t')
            Debug.write(
                'Residuals:            %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f' % \
                (rmerge_def, rmerge_tails, rmerge_abs, rmerge_decay,
                 rmerge_ff, rmerge_fft))
            Debug.write(
                'Convergence:          %5.3f %5.3f %5.3f %5.3f %5.3f %5.3f' % \
                (converge_def, converge_tails, converge_abs, converge_decay,
                 converge_ff, converge_fft))

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

        # then add a brute-force analysis just to be sure...

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

        # first gather reflection files - seeing as we go along if any
        # of them need transforming to MTZ format, e.g. from d*TREK
        # format. N.B. this will also require adding the project,
        # crystal, dataset name from the parent integrater.

        # FIXED 30/OCT/06 in here need to check that the input batches
        # are not 0,0 - because if they are I will need to do some
        # MTZ dumping... see a little further down!

        self._sweep_information = { }

        # FIXME 2/APR/07 added epoch to this... for radiation damage
        # analysis - though this could be NULL...

        # changes 18/DEC/07 adding dose information to this as well,
        # based on image header parsing in DoseAccumulator, which will
        # hopefully operate from cached values. This will be needed
        # later on in the "doser" wrapper to add this information to
        # unmerged MTZ files from Scala.

        Journal.block(
            'gathering', self.get_scaler_xcrystal().get_name(), 'CCP4',
            {'working directory':self.get_working_directory()})        

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

                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, indxr)

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

        # FIXME 06/NOV/06 and before, need to merge the first reflection
        # file in the "correct" pointgroup, so that the others can be
        # reindexed against this - this will ensure consistent indexing
        # in the TS02 case where the unit cell parameters are a bit fiddly.

        # FIXME 02/AUG/07 if we have a reference reflection file
        # passed in explicitly then this will have to behave differently.

        if self.get_scaler_reference_reflection_file():
            self._reference = self.get_scaler_reference_reflection_file()
            Chatter.write('Using HKLREF %s' % self._reference)
        elif Flags.get_reference_reflection_file():
            self._reference = Flags.get_reference_reflection_file()
            Chatter.write('Using HKLREF %s' % self._reference)
            
        if len(self._sweep_information.keys()) > 1 and \
               not self._reference:

            # record this as the reference set, feed this to all subsequent
            # pointless runs through HKLREF (FIXED this needs to be added to
            # the pointless interface - set_hklref()!) 

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
            
            # we will want to delete this one exit
            FileHandler.record_temporary_file(qsc.get_hklout())
            
            # for the moment ignore all of the scaling statistics and whatnot!

            # then check that the unit cells &c. in these reflection files
            # correspond to those rescribed in the indexers belonging to the
            # parent integraters.
            
            # at this stage (see FIXED from 25/SEP/06) I need to run pointless
            # to assess the likely pointgroup. This, unfortunately, will need
            # to tie into the .xinfo hierarchy, as the crystal lattice
            # management takes place in there...
            # also need to make sure that the results from each sweep match
            # up...

            # FIXED 27/OCT/06 need a hook in here to the integrater->indexer
            # to inspect the lattices which have ben contemplated (read tested)
            # because it is quite possible that pointless will come up with
            # a solution which has already been eliminated in the data
            # reduction (e.g. TS01 native being reindexed to I222.)

            # FIXED 06/NOV/06 first run through this with the reference ignored
            # to get the reflections reindexed into the correct pointgroup

        # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------

        # all should share the same pointgroup
        
        overall_pointgroup = None

        need_to_return = False
        
        for epoch in self._sweep_information.keys():
            
            # in this loop need to include feedback to the indexing
            # to ensure that the solutions selected are tractable -
            # note that this will require linking back to the integraters
            # so that the next call to get_integrated_reflections()
            # may trigger reintegration... This is now handled by
            # adding a pointer to the Integrater into the sweep_information
            # which can then be used to pass around this information.
            
            pl = self._factory.Pointless()
            hklin = self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))
            pl.set_hklin(_prepare_pointless_hklin(
                self.get_working_directory(),
                hklin, self._sweep_information[epoch]['header'].get(
                'phi_width', 0.0)))

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
                    hklin, indexer)

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

        # FIXED 06/NOV/06 need to run this again - this time with the
        # reference file... messy but perhaps effective? modded 2/AUG/07
        # if we have a reference from either outside or from the first
        # sweep we need to perform the reindex shuffle.

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
                hklout = os.path.join(
                    self.get_working_directory(),
                    '%s_rdx2.mtz' % os.path.split(hklin)[-1][:-4])
                pl.set_hklin(_prepare_pointless_hklin(
                    self.get_working_directory(),
                    hklin, self._sweep_information[epoch]['header'].get(
                    'phi_width', 0.0)))

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

            # we will want to delete this one exit
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

        # then sort the files together, making sure that the resulting
        # reflection file looks right.

        s = self._factory.Sortmtz()

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted.mtz' % \
                              (self._common_pname, self._common_xname))

        
        s.set_hklout(hklout)

        # we will want to delete this one exit - actually in this case
        # we don't really as it is helpful to keep this for
        # repeating the scaling...
        # FileHandler.record_temporary_file(hklout)

        for epoch in epochs:
            s.add_hklin(self._sweep_information[epoch]['hklin'])

        s.sort()

        # FIXED 16/NOV/06 perhaps in here I should consider running
        # pointless again, this time to decide the correct spacegroup
        # and setting - this should then reset to the correct indexing
        # and reassign the spacegroup (or it's enantiomorph.) I think
        # that this is now done.

        # note well that this is going to use the current pointgroup so
        # any reindexing is to get into the standard setting for the
        # spacegroup

        hklin = hklout
        hklout = hklin.replace('sorted.mtz', 'temp.mtz')

        # FIXME in here need to check to see if we have a reference
        # reflection file - if we do then we will have already
        # reset the reflections to the correct setting so we don't
        # need to do anything here but apply the spacegroup.

        # note here I am not abbreviating the reflection file as I
        # don't know whether this is a great idea...?  30/NOV/06

        # if it's a huge SAD data set then do it! else don't...

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
                Dwbug.write('Assigning user input spacegroup: %s' % \
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
                
            # Write this spacegroup information back to the storage areas
            # in the Scaler interface to allow them to be obtained by the
            # calling entity. Note well that I also want to write in
            # here the spacegroup enantiomorphs.
            
            # FIXED 21/NOV/06 need now to get this from the pointless
            # output...
            
            if self._scalr_input_spacegroup:
                self._scalr_likely_spacegroups = [self._scalr_input_spacegroup]
            else:
                self._scalr_likely_spacegroups = p.get_likely_spacegroups()

            # these are generated by the get_likely_spacegroups so we don't
            # need to be worrying about this - 

            # also need in here to generate cases like I222/I212121, I23, I213,
            # as likely cases - however they are probably included in the
            # likely list...

            # and it turns out that this is not really a problem so can just
            # 'ignore' it -
            
            # then consider all other spacegroups for this pointgroup (at least
            # the ones in "legal" settings) which are not already in the
            # likely list - these will be considered as the unlikely ones.
            
            Chatter.write('Likely spacegroups:')
            for spag in self._scalr_likely_spacegroups:
                Chatter.write('%s' % spag)

            Chatter.write(
                'Reindexing to first spacegroup setting: %s (%s)' % \
                (spacegroup, reindex_operator))

        else:

            # copy the spacegroup from hklref and use this - and set the
            # reindex operator to 'h,k,l', as we should be reindexed
            # correctly already.

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
        # sc.set_tails()
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

                # FIXED should this really measure the errors in terms
                # of total numbers of reflections, or just flatten the
                # graph???

                # FIXME still need to do this...
                # TEST! Solve the structures and work out what is better...

                # trying to minimise difference between this and 1.0!
                
                s_full -= 1.0
                s_partial -= 1.0

                # don't try uniform weighting...

                # if n_full > 0:
                # n_full = 1
                # if n_partial > 0:
                # n_partial = 1

                # end don't try uniform weighting...

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

        # FIXME 10/NOV/06 in here should I also be recording the
        # SdFac that Scala computes and recycling it? It may help
        # the parameter refinement some...

        # FIXME 11/AUG/08 the definition of SdB has now changed to
        # include Lorentz factors or something, so the values hard
        # coded for testing in here are no longer appropriate...

        # FIXME need an option somewhere to configure this...
        
        if False:
            return (0.0, 0.0, 0.0, 0.0)

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

        # compute sd_add first...

        # FIXME I need to assess whether this route is appropriate, or
        # whether I would be better off following some kind of mimisation
        # procedure...

        # perhaps the following would be more use:
        # 
        # refine SdB based on "flatness" of the curve - flatten it out
        # refine SdAdd afterwards to work on the gradient

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

            # check to see if we're going uphill again...
            # FIXME in here I have to allow for the scores being
            # exactly zero as an alternative - i.e. there are
            # no reflections which are full, for instance.

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

            # check to see if we're going uphill again...

            if rms_full > best_rms_full and rms_partial > best_rms_partial:
                break

            sdb_full += step_sdb_full

        # now we have good parameters for the SdB try rerefining the
        # SdAdd...

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

            # check to see if we're going uphill again...
            # FIXME in here I have to allow for the scores being
            # exactly zero as an alternative - i.e. there are
            # no reflections which are full, for instance.

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

        # then perform some scaling - including any parameter fiddling
        # which is required.
        
        epochs = self._sweep_information.keys()
        epochs.sort()

        # first decide on a scaling model... perhaps

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
        
        # now parse the structure of the data to write out how they should
        # be examined by chef...

        if Flags.get_chef():
            self._sweep_information_to_chef()
            self._decide_chef_cutoff_epochs()

        # FIXED in here I need to implement "proper" scaling...
        # this will need to do things like imposing a sensible
        # resolution limit on the data, deciding on the appropriate
        # scaling parameters. The former is best done by analysing
        # the "by resolution" output for each run, and then passing
        # this information back somewhere. The latter can be achieved
        # by a search using "onlymerge restore" type commands.

        # ---------- INITIAL SCALING ----------

        # perform the radiation damage analysis

        # only do this after 1/JUN deadline is reached - this should not
        # be a part of 0.2.5.x c/f bug # 2059. FIXME this will need
        # to be reinstated. FIXME_X0001

        # ird = CCP4IntraRadiationDamageDetector()
        # ird.set_working_directory(self.get_working_directory())
        # ird.set_hklin(self._prepared_reflections)
        # ird.set_sweep_information(self._sweep_information)
        # ird.analyse()

        # FIXME 10/APR/07 -
        # This should probably return a dictionary of new sweep information
        # blocks which should be considered in sequence and completely
        # reduced to provide *named* radiation damage treatment options -
        # alternative is always to reduce radiation damage wherever
        # possible...
        #
        # This will mean that the sweep information for each sample will
        # need to be duplicated for "include all data" and "manage radiation
        # damage" data if appropriate. This will be a huge loop here perhaps?
        # what about resolution limit changes, and so on??!

        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)

        # generate a name for the "scales" file - this will be used for
        # recycling the scaling parameters to compute appropriate
        # sd correction parameters
        
        # scales_file = os.path.join(self.get_working_directory(),
        # '%s.scales' % self._common_xname)

        scales_file = '%s.scales' % self._common_xname

        sc.set_new_scales_file(scales_file)

        # this will require first sorting out the batches/runs, then
        # deciding what the "standard" wavelength/dataset is, then
        # combining everything appropriately...

        # while we are here (see bug # 3183) gather any user specified
        # resolution limits

        user_resolution_limits = { }

        for epoch in epochs:

            input = self._sweep_information[epoch]

            intgr = input['integrater']

            if intgr.get_integrater_user_resolution():
                dmin = intgr.get_integrater_high_resolution()
                
                if not user_resolution_limits.has_key(input['dname']):
                    user_resolution_limits[input['dname']] = dmin
                elif dmin < user_resolution_limits[input['dname']]:
                    user_resolution_limits[input['dname']] = dmin
                    
            start, end = (min(input['batches']), max(input['batches']))
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
        # sc.set_tails()

        sc.scale()

        # then gather up all of the resulting reflection files
        # and convert them into the required formats (.sca, .mtz.)

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()

        # parse the statistics from Scala - these are printed in the
        # loggraph output, and therefore need some transformation &
        # massaging to be useful.

        # look also for a sensible resolution limit for this data set -
        # that is, the place where I/sigma is about two for the highest
        # resolution data set - this should be a multiple of 0.05 A just
        # to keep the output tidy...

        # FIXME 08/NOV/06 asserting a resolution limit here will cause
        # the integration to be repeated. I want to assert a resolution
        # limit for each wavelength, rather than each sweep, since this
        # will get around the complication of merging multiple sweeps
        # together (I hope...)

        # FIXME further - if this process has already happened once the new
        # resolution limit should be within 0.1A of the current resolution
        # limit of the data - therefore ensure that if this is the case
        # the resolution limit is not reasserted.

        resolution_info = { }

        # this returns a dictionary of files that I will use to calculate
        # the resolution limits...
        
        reflection_files = sc.get_scaled_reflection_files()

        for key in loggraph.keys():
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # next compute resolution limits for each dataset.

        resolution_limits = { }

        highest_resolution = 100.0

        # check in here that there is actually some data to scale..!

        if len(resolution_info.keys()) == 0:
            raise RuntimeError, 'no resolution info'

        for dataset in resolution_info.keys():

            if user_resolution_limits.has_key(dataset):
                resolution = user_resolution_limits[dataset]
                resolution_limits[dataset] = resolution
                if resolution < highest_resolution:
                    highest_resolution = resolution
                Chatter.write('Resolution limit for %s: %5.2f' % \
                              (dataset, resolution))
                continue
            
            # transform this to a useful form... [(resol, i/sigma), (resol..)]
            resolution_points = []
            resol_ranges = resolution_info[dataset]['3_Dmin(A)']
            mn_i_sigma_values = resolution_info[dataset]['13_Mn(I/sd)']
            for i in range(len(resol_ranges)):
                dmin = float(resol_ranges[i])
                i_sigma = float(mn_i_sigma_values[i])
                resolution_points.append((dmin, i_sigma))

            old_way = False

            if old_way:
                resolution = _resolution_estimate(
                    resolution_points, Flags.get_i_over_sigma_limit())
            else:
                resolution = determine_scaled_resolution(
                    reflection_files[dataset], 3.0)[1]

            # FIXME in here want to look at the reflection file to
            # calculate the resolution limit, not the Scala log
            # file output... FIXME-DETERMINE-RESOLUTION

            # next compute "useful" versions of these resolution limits
            # want 0.05A steps - in here it would also be useful to
            # gather up an "average" best resolution and perhaps use this
            # where it seems appropriate e.g. TS03 INFL, LREM.

            resolution_limits[dataset] = resolution

            if resolution < highest_resolution:
                highest_resolution = resolution

            Chatter.write('Resolution limit for %s: %5.2f' % \
                          (dataset, resolution_limits[dataset]))

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

            # compare this against the resolution limit computed above
            if dmin == 0.0 and not Flags.get_quick():
                intgr.set_integrater_high_resolution(
                    resolution_limits[dname])

                # we need to rerun both the scaling and the preparation -
                # this may trigger reintegration as well...
                self.set_scaler_done(False)
                self.set_scaler_prepare_done(False)

            # note well that this spacing (0.075A) is designed to ensure that
            # integration shouldn't be repeated once it has been repeated
            # once...
            
            elif dmin > resolution_limits[dname] - 0.075:
                # no need to reprocess the data - this is near enough...
                # this should save us from the "infinate loop"
                pass

            elif Flags.get_quick():
                Debug.write('Quick, so not resetting resolution limits')

            elif intgr.get_integrater_user_resolution():
                Debug.write('Using user specified resolution limits')

            else:
                # ok it is worth rereducing the data
                intgr.set_integrater_high_resolution(
                    resolution_limits[dname])

                # we need to rerun both the scaling and the preparation -
                # this may trigger reintegration as well...
                self.set_scaler_done(False)
                self.set_scaler_prepare_done(False)

            if resolution_limits[dname] < best_resolution:
                best_resolution = resolution_limits[dname]

        # if we need to redo the scaling, return to allow this to happen

        if not self.get_scaler_done():
            Debug.write('Returning as scaling not finished...')
            return

        # and also radiation damage stuff...

        # FIXME 08/NOV/06 this needs to be fed back into the Integraters
        # as to the batches that they should integrate - and possibly even
        # have integraters eliminated from the input based on this
        # information (this will be a later development, see also the
        # scaling of multiple datasets below after CAD.)

        batch_info = { }
        
        for key in loggraph.keys():
            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                batch_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # perform some analysis of these results

        # bug 2040 - want to perhaps be quick? if so, do not bother
        # with this and instead just set these parameters to
        # the default values

        # data still contains the summary information - for bug # 2357
        # see if the completeness appears to be > 50 % overall and if
        # not, do not refine sd parameters...

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

            # ---------- SD CORRECTION PARAMETER LOOP ----------
            
            # first "fix" the sd add parameters to match up the sd curve from
            # the fulls and partials, and minimise RMS[N (scatter / sigma - 1)]
            
            Debug.write('Optimising error parameters')
            
            sdadd_full, sdb_full, sdadd_partial, sdb_partial = \
                        self._refine_sd_parameters(scales_file)

            # remove the old scales file
            try:
                os.remove(os.path.join(self.get_working_directory(),
                                       scales_file))
            except:
                Debug.write('Error removing %s' % scales_file)

        # then try tweaking the sdB parameter in a range say 0-20
        # starting at 0 and working until the RMS stops going down

        # ---------- FINAL SCALING ----------

        # assert the resolution limits in the integraters - beware, this
        # means that the reflection files will probably have to be
        # regenerated (integration restarted!) and so we will have to
        # build in some "fudge factor" to ensure we don't get stuck in a
        # tight loop - initially just rerun the scaling with all of the
        # "right" parameters...
        
        sc = self._updated_scala()

        FileHandler.record_log_file('%s %s scala' % (self._common_pname,
                                                     self._common_xname),
                                    sc.get_log_file())

        sc.set_resolution(best_resolution)

        sc.set_hklin(self._prepared_reflections)

        # scales_file = os.path.join(self.get_working_directory(),
        # '%s_final.scales' % self._common_xname)

        scales_file = '%s_final.scales' % self._common_xname

        sc.set_new_scales_file(scales_file)

        sc.add_sd_correction('full', 2.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 2.0, sdadd_partial, sdb_partial)

        # this will require first sorting out the batches/runs, then
        # deciding what the "standard" wavelength/dataset is, then
        # combining everything appropriately...

        # record this for ease of access in development - FIXME this
        # needs removing!
        open(os.path.join(
            self.get_working_directory(),
            'sweep_info.xia'), 'w').write(str(self._sweep_information))
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            # bug # 2040 - if going quickly then the resolution limits
            # won't have been set correctly in the reflection files...

            if Flags.get_quick():
                run_resolution_limit = resolution_limits[input['dname']]
            else:
                run_resolution_limit = 0.0

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit)

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        # FIXME this needs to be set only is we have f', f'' values
        # for the wavelength or multiple wavelengths...
        
        # bug # 2326
        if self.get_scaler_anomalous():
            sc.set_anomalous()
        # sc.set_tails()

        sc.scale()

        # print out the number of cycles needed for convergence in the
        # final run... for testing!

        Debug.write('Convergence at: %.1f cycles' % sc.get_convergence())

        # let's take a look at the resolutions once the error corrections
        # have been applied...
        
        for dataset in resolution_info.keys():
            if False:
                print dataset
                determine_scaled_resolution(
                    reflection_files[dataset], 3.0)[1]

        # then gather up all of the resulting reflection files
        # and convert them into the required formats (.sca, .mtz.)

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()

        # parse the statistics from Scala - these are printed in the
        # loggraph output, and therefore need some transformation &
        # massaging to be useful.

        # look for the B factor vs. batch / rotation range graphs for
        # radiation damage analysis...
        #
        # FIXME pull all of this out and move it to ccp4 intra radiation
        # damage module - though this will need to me moved earlier
        # and also look at R merges etc.

        FIXME_X0001 = False

        if FIXME_X0001:
            bfactor_info = { }

        for key in loggraph.keys():

            damaged = False
            damage_batch = 0
            
            if 'Scales v rotation range' in key and FIXME_X0001:
                # then this contains Bfactor information...
                # which we don't want to consider at the moment.
                dataset = key.split(',')[-1].strip()
                bfactor_info[dataset] = transpose_loggraph(
                    loggraph[key])

                # perform some analysis on this information -
                # this could be fiddly...
                # FIXME this needs to be moved to the CCP4
                # intra radiation damage analysis tool...
                # look at Bfactor and Rmerge.

                for j in range(len(bfactor_info[dataset]['1_N'])):
                    batch = int(bfactor_info[dataset]['4_Batch'][j])
                    bfactor = float(bfactor_info[dataset]['5_Bfactor'][j])

                    if bfactor < -10.0:
                        damaged = True
                        damage_batch = batch
                        break

                if damaged:
                    Chatter.write(
                        '%s appears to be radiation damaged (batch %d)' % \
                        (dataset, damage_batch))
                else:
                    Chatter.write(
                        '%s appears to be ok' % dataset)
                    
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


        # also look at the standard deviation factors which were used

        sd_factors = sc.get_sd_factors()

        Debug.write('Standard deviation factors')

        for run in sorted(sd_factors.keys()):
            record = [run] + list(sd_factors[run])
            Debug.write('Run %d: %.3f %.3f %.3f %.3f %.3f %.3f' % \
                        tuple(record))

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
            m2v = self._factory.Mtz2various()
            m2v.set_hklin(file)
            m2v.set_hklout('%s.sca' % file[:-4])
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][
                key] = '%s.sca' % file[:-4]

        # FIXED BUG 2146

        # in here rerun scala recycling the final scales and writing out
        # unmerged reflection files in scalepack format

        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        sc.add_sd_correction('full', 2.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 2.0, sdadd_partial, sdb_partial)

        self._wavelengths_in_order = []
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            if Flags.get_quick():
                run_resolution_limit = resolution_limits[input['dname']]
            else:
                run_resolution_limit = 0.0

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

        # bug # 2326
        if self.get_scaler_anomalous():
            sc.set_anomalous()
        # sc.set_tails()
        sc.scale()

        # this will delete the mtz files which have been made 
        # and record the unmerged scalepack files in the file dictionary
        # BUG FIXME this is only right for MAD data... but that should now
        # be fixed...

        self._scalr_scaled_reflection_files['sca_unmerged'] = { }
        for key in self._tmp_scaled_refl_files:
            file = self._tmp_scaled_refl_files[key]
            scalepack = os.path.join(os.path.split(file)[0],
                                     os.path.split(file)[1].replace(
                '_scaled', '_unmerged').replace('.mtz', '.sca'))
            self._scalr_scaled_reflection_files['sca_unmerged'][
                key] = scalepack
            FileHandler.record_data_file(scalepack)

        # FIXME moving marker - see FIXME below...

        # merge the data yet again, except this time don't merge (!)
        # just recycle the scales to produce output MTZ files with
        # sdcorrection = 1 0 noadjust for CHEF to much on...
        # c/f Bug # 2798

        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        self._wavelengths_in_order = []
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            if Flags.get_quick():
                run_resolution_limit = resolution_limits[input['dname']]
            else:
                run_resolution_limit = 0.0

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit)
            if not input['dname'] in self._wavelengths_in_order:
                self._wavelengths_in_order.append(input['dname'])

        # note well that this will produce multiple reflection files...
        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_chef.mtz' % \
                                   (self._common_pname,
                                    self._common_xname)))
        
        sc.set_chef_unmerged(True)

        sc.add_sd_correction('full', 2.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 2.0, sdadd_partial, sdb_partial)

        if self.get_scaler_anomalous():
            sc.set_anomalous()
            
        # sc.set_tails()
        sc.scale()

        # next get the files back in MTZ format... N.B. this is structured
        # as a dictionary {WAVE:MTZ}
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

                # no longer use the doser binary
                
                # d = self._factory.Doser()
                hklin = bits[wave][0]
                hklout = '%s_dose.mtz' % hklin[:-4]
                # d.set_hklin(hklin)
                # d.set_hklout(hklout)
                # d.set_doses(doses)
                # d.run()

                add_dose_time_to_mtz(hklin = hklin, hklout = hklout,
                                     doses = doses)

                chef_hklins.append(hklout)
                # FileHandler.record_temporary_file(hklout)

            # then run chef with this - no analysis as yet, but to record
            # the log file to chef_groupN_analysis or something and be
            # sure that it finds it's way to the LogFiles directory.
            
            # then feed the results to chef

            chef = self._factory.Chef()

            chef.set_title('Group %d' % group)

            dose_step = self._chef_analysis_times[group] / \
                        self._chef_dose_factor
            anomalous = self.get_scaler_anomalous()

            for hklin in chef_hklins:
                chef.add_hklin(hklin)

            chef.set_anomalous(anomalous)
            chef.set_resolution(resolution)
            chef.set_width(dose_step)
            chef.set_max(dose_max)
            chef.set_labin('DOSE')
            
            chef.run()

            FileHandler.record_log_file('chef group %d' % (group + 1),
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
                sc.set_resolution(resolution_limits[dname])

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
                # for j in range(len(moments['MomentZ2'])):
                # pass

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
                Chatter.write('Inter-wavelength B and R-factor analysis:')
                for s in status:
                    Chatter.write('%s %s' % s)
                Chatter.write('')
        

        return

    
