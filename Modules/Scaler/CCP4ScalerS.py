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
from lib.bits import is_mtz_file, nifty_power_of_ten, auto_logfiler
from lib.bits import transpose_loggraph, nint
from lib.SymmetryLib import lattices_in_order

from CCP4ScalerHelpers import _resolution_estimate, \
     _prepare_pointless_hklin, _fraction_difference, \
     CCP4ScalerHelper

from Modules.CCP4InterRadiationDamageDetector import \
     CCP4InterRadiationDamageDetector
from Modules.DoseAccumulate import accumulate

from Modules.AnalyseMyIntensities import AnalyseMyIntensities
from Experts.ResolutionExperts import determine_scaled_resolution
from Toolkit.Merger import merger

# newly implemented CCTBX powered functions to replace xia2 binaries
from Modules.Scaler.add_dose_time_to_mtz import add_dose_time_to_mtz

class CCP4ScalerS(Scaler):
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
        '''Generate a correctly configured Scala...'''

        scala = None
        
        if not self._scalr_corrections:
            scala = self._factory.Scala()
        else:

            scala =  self._factory.Scala(
                partiality_correction = self._scalr_correct_partiality,
                absorption_correction = self._scalr_correct_absorption,
                decay_correction = self._scalr_correct_decay)

        scala.set_sd_parameters_auto()

        if Flags.get_microcrystal():

            # fiddly little data sets - allow more rapid scaling...
            
            scala.set_scaling_parameters('rotation', 2.0)
            if self._scalr_correct_decay:
                scala.set_bfactor(bfactor = True, brotation = 2.0)
        
        return scala

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
                           exclude = False, name = input['sweep_name'])
            
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

        # or see if we set one on the command line...

        if Flags.get_scale_model():
            self._scalr_correct_absorption = Flags.get_scale_model_absorption()
            self._scalr_correct_partiality = Flags.get_scale_model_partiality()
            self._scalr_correct_decay = Flags.get_scale_model_decay()
            
            self._scalr_corrections = True

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

        return

    def _determine_best_scale_model_8way(self):
        '''Determine the best set of corrections to apply to the data,
        testing all eight permutations.'''

        # if we have already defined the best scaling model just return

        if self._scalr_corrections:
            return

        # or see if we set one on the command line...

        if Flags.get_scale_model():
            self._scalr_correct_absorption = Flags.get_scale_model_absorption()
            self._scalr_correct_partiality = Flags.get_scale_model_partiality()
            self._scalr_correct_decay = Flags.get_scale_model_decay()
            
            self._scalr_corrections = True

            return

        Debug.write('Optimising scaling corrections...')

        # central preparation stuff

        epochs = sorted(self._sweep_information.keys())

        rmerge_def, converge_def = self._assess_scaling_model(
            tails = False, bfactor = False, secondary = False)
                                                              
        results = { }

        consider = []

        # don't rerun False, False, False...
        
        for partiality in True, False:
            for decay in True, False:
                for absorption in True, False:
                    if partiality or decay or absorption:
                        r, c = self._assess_scaling_model(
                            tails = partiality, bfactor = decay,
                            secondary = absorption)
                    else:
                        r, c = rmerge_def, converge_def
                        
                    results[(partiality, decay, absorption)] = r, c
                    if c - converge_def < 1.0:
                        consider.append(
                            (r, partiality, decay, absorption))

        consider.sort()
        rmerge, partiality, decay, absorption = consider[0]
        
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

        for epoch in sorted(self._sweep_information):
            header = self._sweep_information[epoch]['header']
            batches = self._sweep_information[epoch]['batches']
            dr = header['exposure_time'] / header['phi_width']
            wave = self._sweep_information[epoch]['dname']
            template = self._sweep_information[epoch][
                'integrater'].get_template()

            indxr = self._sweep_information[epoch][
                'integrater'].get_integrater_indexer()
            beam = indxr.get_indexer_beam()
            distance = indxr.get_indexer_distance()
            wavelength = self._sweep_information[epoch][
                'integrater'].get_wavelength()
            resolution_used = self._sweep_information[epoch][
                'integrater'].get_integrater_high_resolution()

            detector_width = header['size'][0] * header['pixel'][0] 
            detector_height = header['size'][1] * header['pixel'][1]

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

        except RuntimeError, e:

            Debug.write('Gathering information failed: %s' % str(e))
            
        epochs = self._sweep_information.keys()

        for epoch in epochs:
            if not is_mtz_file(self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()):
                raise RuntimeError, \
                      'input file %s not MTZ format' % \
                      self._sweep_information[epoch][
                    'integrater'].get_integrater_reflections()

        self._scalr_pname = self._sweep_information[epochs[0]]['pname']
        self._scalr_xname = self._sweep_information[epochs[0]]['xname']

        for epoch in epochs:
            pname = self._sweep_information[epoch]['pname']
            if self._scalr_pname != pname:
                raise RuntimeError, 'all data must have a common project name'
            xname = self._sweep_information[epoch]['xname']
            if self._scalr_xname != xname:
                raise RuntimeError, \
                      'all data for scaling must come from one crystal'

        # verify that the lattices are consistent, calling eliminate if
        # they are not N.B. there could be corner cases here

        need_to_return = False

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
                
                    pointless_hklin = _prepare_pointless_hklin(
                        self.get_working_directory(),
                        hklin, self._sweep_information[epoch]['header'].get(
                        'phi_width', 0.0))
                    
                    pointgroup, reindex_op, ntr = \
                                self._pointless_indexer_jiffy(
                        pointless_hklin, indxr)

                lattice = Syminfo.get_lattice(pointgroup)

                if not lattice in lattices:
                    lattices.append(lattice)

                if ntr:

                    reindex_op = 'h,k,l'
                    intgr.set_integrater_reindex_operator(
                        reindex_op, compose = False)
                    
                    need_to_return = True
            
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
            
            if indexer and not self._scalr_input_pointgroup:

                pointgroup, reindex_op, ntr = \
                            self._pointless_indexer_jiffy(
                    pointless_hklin, indexer)

                if ntr:
                    
                    reindex_op = 'h,k,l'
                    
                    integrater.set_integrater_reindex_operator(
                        reindex_op, compose = False)
                    
                    need_to_return = True

            else:
                pointgroup = self._scalr_input_pointgroup
                reindex_op = 'h,k,l'                

            Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            if self._scalr_input_pointgroup:
                Debug.write('Using input pointgroup: %s' % \
                              self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup

            integrater.set_integrater_reindex_operator(reindex_op)
            integrater.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup))
            
            self._reference = integrater.get_integrater_reflections()
            
        # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------

        # all should share the same pointgroup
        
        overall_pointgroup = None

        need_to_return = False
        
        for epoch in self._sweep_information.keys():
            
            hklin = self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))
            FileHandler.record_temporary_file(hklout)

            integrater = self._sweep_information[epoch]['integrater']
            indexer = integrater.get_integrater_indexer()

            if self._scalr_input_pointgroup:
                pointgroup = self._scalr_input_pointgroup
                reindex_op = 'h,k,l'

            else:

                pointless_hklin = _prepare_pointless_hklin(
                    self.get_working_directory(),
                    hklin, self._sweep_information[epoch]['header'].get(
                    'phi_width', 0.0))
            
                pl = self._factory.Pointless()
                pl.set_hklin(pointless_hklin)
                pl.decide_pointgroup()

                # get the correct pointgroup etc.
                pointgroup = pl.get_pointgroup()
                reindex_op = pl.get_reindex_operator()

                # flag to record whether I need to do some rerunning
                rerun_pointless = False
                
                if indexer:
                    
                    pointgroup, reindex_op, ntr = \
                                self._pointless_indexer_jiffy(
                        pointless_hklin, indexer)
                    
                    if ntr:
                        
                        reindex_op = 'h,k,l'
                        integrater.set_integrater_reindex_operator(
                            reindex_op, compose = False)
                        
                        need_to_return = True

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
            
        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        if self._reference:

            md = self._factory.Mtzdump()
            md.set_hklin(self._reference)
            md.dump()

            if md.get_batches() and False:
                raise RuntimeError, 'reference reflection file %s unmerged' % \
                      self._reference

            datasets = md.get_datasets()

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

                pointgroup = pl.get_pointgroup()
                reindex_op = pl.get_reindex_operator()
                
                Debug.write('Operator: %s' % reindex_op)

                # apply this...

                integrater = self._sweep_information[epoch]['integrater']
                
                integrater.set_integrater_reindex_operator(reindex_op)
                integrater.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))

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

                for j in range(6):
                    if math.fabs((cell[j] - reference_cell[j]) /
                                 reference_cell[j]) > 0.1:
                        raise RuntimeError, \
                              'unit cell parameters differ in %s and %s' % \
                              (self._reference,
                               integrater.get_integrater_reflections())

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

            batches = self._sweep_information[epoch]['batches']
            if 1 + max(batches) - min(batches) > max_batches:
                max_batches = max(batches) - min(batches) + 1
            
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
                              (self._scalr_pname, self._scalr_xname))

        
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
                                        (self._scalr_pname,
                                         self._scalr_xname),
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

    def _scale(self):
        '''Perform all of the operations required to deliver the scaled
        data.'''

        epochs = self._sweep_information.keys()
        epochs.sort()

        if Flags.get_smart_scaling():
            if Flags.get_8way():
                self._determine_best_scale_model_8way()
            else:
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

        # first scale the data and output unmerged, to decide the
        # most sensible resolution limits - at the moment this works
        # through the "chef" interface
            
        sc = self._updated_scala()
        sc.set_hklin(self._prepared_reflections)

        sc.set_chef_unmerged(True)

        scales_file = '%s.scales' % self._scalr_xname

        sc.set_new_scales_file(scales_file)

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

            if input['dname'] in self._resolution_limits:
                resolution = self._resolution_limits[input['dname']]
                sc.add_run(start, end, pname = input['pname'],
                           xname = input['xname'],
                           dname = input['dname'],
                           exclude = False,
                           resolution = resolution,
                           name = input['sweep_name'])
            else:
                sc.add_run(start, end, pname = input['pname'],
                           xname = input['xname'],
                           dname = input['dname'],
                           name = input['sweep_name'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled_test.mtz' % \
                                   (self._scalr_pname, self._scalr_xname)))
        
        if self.get_scaler_anomalous():
            sc.set_anomalous()

        # ok in tricky mode may want to be able to remove a run / sweep from
        # the scaling - this will be caused by a bad batch error (or perhaps
        # a negative scale) - will need to identify the sweep, then remove
        # it...

        if Flags.get_failover():

            try:
                sc.scale()
            except RuntimeError, e:

                es = str(e)

                if 'bad batch' in es or \
                       'negative scales run' in es or \
                       'no observations' in es:
                    
                    # first ID the sweep from the batch no

                    batch = int(es.split()[-1])
                    epoch = self._identify_sweep_epoch(batch)
                    sweep = self._scalr_integraters[
                        epoch].get_integrater_sweep()

                    # then remove it from my parent xcrystal

                    self.get_scaler_xcrystal().remove_sweep(sweep)

                    # then remove it from the scaler list of intergraters
                    # - this should really be a scaler interface method

                    del(self._scalr_integraters[epoch])

                    # then tell the user what is happening

                    Chatter.write(
                        'Sweep %s gave negative scales - removing' % \
                        sweep.get_name())
                              
                    # then reset the prepare, do, finish flags

                    self.set_scaler_prepare_done(False)
                    self.set_scaler_done(False)
                    self.set_scaler_finish_done(False)
                    
                    # and return
                    
                    return

                else:
                    
                    raise e


        else:
            sc.scale()

        # then gather up all of the resulting reflection files
        # and convert them into the required formats (.sca, .mtz.)

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()
        
        resolution_info = { }

        # this returns a dictionary of files that I will use to calculate
        # the resolution limits... N.B. these are now unmerged reflection
        # files to allow more clever calculations

        reflection_files = sc.get_scaled_reflection_files()

        for dataset in reflection_files:
            FileHandler.record_temporary_file(reflection_files[dataset])

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

            log_completeness = os.path.join(self.get_working_directory(),
                                      '%s-completeness.log' % dataset)

            if os.path.exists(log_completeness):
                log_completeness = None
            
            log_rmerge = os.path.join(self.get_working_directory(),
                                      '%s-rmerge.log' % dataset)

            if os.path.exists(log_rmerge):
                log_rmerge = None

            log_isigma = os.path.join(self.get_working_directory(),
                                      '%s-isigma.log' % dataset)

            if os.path.exists(log_isigma):
                log_isigma = None
            
            log_misigma = os.path.join(self.get_working_directory(),
                                      '%s-misigma.log' % dataset)

            if os.path.exists(log_misigma):
                log_misigma = None

            m = merger(reflection_files[dataset])

            m.calculate_resolution_ranges(nbins = 100)

            r_comp = m.resolution_completeness(log = log_completeness)
            r_rm = m.resolution_rmerge(log = log_rmerge)
            r_uis = m.resolution_unmerged_isigma(log = log_isigma)
            r_mis = m.resolution_merged_isigma(log = log_misigma)

            resolution = max([r_comp, r_rm, r_uis, r_mis])

            Debug.write('Resolution for sweep %s: %.2f' % \
                        (dataset, resolution))
                        
            # the old version of this code...

            if False:
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

        sc = self._updated_scala()

        FileHandler.record_log_file('%s %s scala' % (self._scalr_pname,
                                                     self._scalr_xname),
                                    sc.get_log_file())

        highest_resolution = 100.0

        sc.set_hklin(self._prepared_reflections)
        
        scales_file = '%s_final.scales' % self._scalr_xname

        sc.set_new_scales_file(scales_file)

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            run_resolution_limit = self._resolution_limits[input['dname']]

            if run_resolution_limit < highest_resolution:
                highest_resolution = run_resolution_limit

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit,
                       name = input['sweep_name'])

        sc.set_resolution(highest_resolution)

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._scalr_pname, self._scalr_xname)))
        
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

        self._wavelengths_in_order = []
        
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
            
            if not input['dname'] in self._wavelengths_in_order:
                self._wavelengths_in_order.append(input['dname'])
            
        sc.set_hklout(os.path.join(self.get_working_directory(), 'temp.mtz'))
        sc.set_scalepack(os.path.join(self.get_working_directory(),
                                      '%s_%s_unmerged.sca' % \
                                      (self._scalr_pname,
                                       self._scalr_xname)))

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
                       resolution = run_resolution_limit,
                       name = input['sweep_name'])
            
            if not input['dname'] in self._wavelengths_in_order:
                self._wavelengths_in_order.append(input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_chef.mtz' % \
                                   (self._scalr_pname,
                                    self._scalr_xname)))
        
        sc.set_chef_unmerged(True)

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

        all_doses = sorted([doses[b] for b in doses])
        dose_max = all_doses[-1] + (all_doses[-1] - all_doses[-2])

        for group in sorted(self._chef_analysis_groups):

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

            chef = self._factory.Chef()

            chef.set_title('%s Group %d' % (self._scalr_xname, group + 1))

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
                '%s chef %d' % (self._scalr_xname, group + 1),
                chef.get_log_file())

        for key in self._scalr_statistics:
            pname, xname, dname = key

            harvest_copy = os.path.join(os.environ['HARVESTHOME'],
                                        'DepositFiles', pname,
                                        '%s.scala' % dname)

            sc = self._updated_scala()
            sc.set_hklin(self._prepared_reflections)
            sc.set_scales_file(scales_file)

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

                sc.set_resolution(self._resolution_limits[dname])

            sc.set_hklout(os.path.join(self.get_working_directory(),
                                           'temp.mtz'))
                
            if self.get_scaler_anomalous():
                sc.set_anomalous()
                
            sc.scale()
            stats = sc.get_summary()

            self._scalr_statistics[key] = stats[key]

            shutil.copyfile(harvest_copy, '%s.keep' % harvest_copy)

            Debug.write('Copying %s to %s' % \
                        (harvest_copy, '%s.keep' % harvest_copy))

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
                              '%s_%s_free.mtz' % (self._scalr_pname,
                                                  self._scalr_xname))

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
                                            (self._scalr_pname,
                                             self._scalr_xname,
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

                Debug.write('%d absent reflections in %s removed' % \
                            (t.get_nabsent(), key))

                b_factor = t.get_b_factor()

                # look for the second moment information...
                moments = t.get_moments()

                # record the b factor somewhere (hopefully) useful...

                self._scalr_statistics[
                    (self._scalr_pname, self._scalr_xname, key)
                    ]['Wilson B factor'] = [b_factor]

                self._tmp_scaled_refl_files[key] = hklout

        average_cell_a = 0.0
        average_cell_b = 0.0
        average_cell_c = 0.0
        average_cell_alpha = 0.0
        average_cell_beta = 0.0
        average_cell_gamma = 0.0

        average_cell_nref = 0

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

        if len(self._tmp_scaled_refl_files.keys()) > 1:
            c = self._factory.Cad()
            for key in self._tmp_scaled_refl_files.keys():
                file = self._tmp_scaled_refl_files[key]
                c.add_hklin(file)
        
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_merged.mtz' % (self._scalr_pname,
                                                        self._scalr_xname))

            Debug.write('Merging all data sets to %s' % hklout)

            c.set_hklout(hklout)
            c.merge()
            
            self._scalr_scaled_reflection_files['mtz_merged'] = hklout

        else:

            self._scalr_scaled_reflection_files[
                'mtz_merged'] = self._tmp_scaled_refl_files[
                self._tmp_scaled_refl_files.keys()[0]]

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_free_temp.mtz' % (self._scalr_pname,
                                                       self._scalr_xname))

        FileHandler.record_temporary_file(hklout)

        if self.get_scaler_freer_file():
            
            freein = self.get_scaler_freer_file()
        
            Debug.write('Copying FreeR_flag from %s' % freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
            c.set_hklout(hklout)
            c.copyfree()

        elif Flags.get_freer_file():
            
            freein = Flags.get_freer_file()

            Debug.write('Copying FreeR_flag from %s' % freein)

            c = self._factory.Cad()
            c.set_freein(freein)
            c.add_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
            c.set_hklout(hklout)
            c.copyfree()

        else:

            free_fraction = 0.05
            
            if Flags.get_free_fraction():
                free_fraction = Flags.get_free_fraction()
            elif Flags.get_free_total():
                ntot = Flags.get_free_total()
                
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

        hklin = hklout
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_free.mtz' % (self._scalr_pname,
                                                  self._scalr_xname))

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

        del self._scalr_scaled_reflection_files['mtz_merged']

        self._scalr_scaled_reflection_files['mtz'] = hklout

        FileHandler.record_data_file(hklout)

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
                Chatter.banner('Local Scaling %s' % self._scalr_xname)
                for s in status:
                    Chatter.write('%s %s' % s)
                Chatter.banner('')       

        return
    
    def _identify_sweep_epoch(self, batch):
        '''Identify the sweep epoch a given batch came from - N.B.
        this assumes that the data are rebatched, will raise an exception if
        more than one candidate is present.'''

        epochs = []

        for epoch in self._sweep_information:

            if batch in self._sweep_information[epoch]['batches']:
                epochs.append(epoch)

        if not epochs:
            raise RuntimeError, 'batch %d not found' % batch

        if len(epochs) > 1:
            raise RuntimeError, 'batch %d found in multiple sweeps' % batch
        
        return epochs[0]

    
