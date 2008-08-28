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
from Modules.XDSPointgroup import XDSPointgroup
from Modules.XDSScalerHelpers import XDSScalerHelper

# program wrappers that we will need

from Wrappers.XDS.XScale import XScale as _XScale
from Wrappers.XDS.Cellparm import Cellparm as _Cellparm

from Wrappers.CCP4.CCP4Factory import CCP4Factory

# random odds and sods - the resolution estimate should be somewhere better
from lib.Guff import auto_logfiler, transpose_loggraph, is_mtz_file
from lib.Guff import nifty_power_of_ten
from lib.SymmetryLib import lattices_in_order
from Handlers.Citations import Citations
from Handlers.Syminfo import Syminfo
from Handlers.Streams import Chatter, Debug
from Handlers.Flags import Flags
from Handlers.Files import FileHandler
from Experts.SymmetryExpert import r_to_rt, rt_to_r
from Experts.SymmetryExpert import symop_to_mat, compose_matrices_r

# stuff I have nicked from the CCP4 Scaler implementation
from CCP4ScalerImplementationHelpers import _resolution_estimate
from CCP4InterRadiationDamageDetector import CCP4InterRadiationDamageDetector

class XDSScaler(Scaler):
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
        xscale = _XScale()
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
        # so!

        need_to_return = False

        if False:

            if not is_mtz_file(hklin):
                
                hklout = os.path.join(self.get_working_directory(),
                                      'temp-combat.mtz')
                
                FileHandler.record_temporary_file(hklout)
                
                combat = self._factory.Combat()
                combat.set_hklin(hklin)
                combat.set_hklout(hklout)
                combat.run()
                
                hklin = hklout

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

            Chatter.write('Possible lattices (pointless):')
            lattices = ''
            for lattice in possible:
                lattices += '%s ' % lattice
            Chatter.write(lattices)

            for lattice in possible:
                state = indexer.set_indexer_asserted_lattice(lattice)
                if state == 'correct':
                            
                    Chatter.write(
                        'Agreed lattice %s' % lattice)
                    correct_lattice = lattice
                    
                    break
                
                elif state == 'impossible':
                    Chatter.write(
                        'Rejected lattice %s' % lattice)
                    
                    rerun_pointless = True
                    
                    continue
                
                elif state == 'possible':
                    Chatter.write(
                        'Accepted lattice %s ...' % lattice)
                    Chatter.write(
                        '... will reprocess accordingly')
                    
                    need_to_return = True
                    
                    correct_lattice = lattice
                    
                    break
                    
            if rerun_pointless:
                pointless.set_correct_lattice(correct_lattice)
                pointless.decide_pointgroup()

        Chatter.write('Pointless analysis of %s' % pointless.get_hklin())

        pointgroup = pointless.get_pointgroup()
        reindex_op = pointless.get_reindex_operator()
        
        Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

        return pointgroup, reindex_op, need_to_return


    def _refine_sd_parameters_remerge(self, scales_file, sdadd_f, sdb_f):
        '''Actually compute the RMS deviation from scatter / sigma = 1.0
        from unity.'''
        
        epochs = self._sweep_information.keys()
        epochs.sort()

        sc = self._factory.Scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        sc.add_sd_correction('both', 1.0, sdadd_f, sdb_f)
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(), 'temp.mtz'))

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.set_onlymerge()
        sc.multi_merge()
        
        loggraph = sc.parse_ccp4_loggraph()

        standard_deviation_info = { }

        # FIXME in here this will take account of all runs separately
        # and also the "all runs" collection as well - should I
        # just refine on the all-runs or is it better to exclude this?

        for key in loggraph.keys():
            if 'standard deviation v. Intensity' in key:
                dataset = key.split(',')[-1].strip()
                standard_deviation_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # compute an RMS sigma...

        score_full = 0.0
        ref_count_full = 0

        for dataset in standard_deviation_info.keys():
            info = standard_deviation_info[dataset]

            for j in range(len(info['1_Range'])):
                n_full = int(info['5_Number'][j])
                I_full = float(info['4_Irms'][j])
                s_full = float(info['7_SigmaFull'][j])

                n_tot = n_full

                # trap case where we have no reflections in a higher
                # intensity bin (one may ask why they are being printed
                # by Scala, then?)

                if n_tot:
                    i_tot = I_full
                    s_tot = s_full
                else:
                    i_tot = 0.0
                    s_tot = 1.0

                s_full -= 1.0

                score_full += s_full * s_full * n_full
                ref_count_full += n_full

            # compute the scores...

            if ref_count_full > 0:
                score_full /= ref_count_full

        return math.sqrt(score_full)

    def _refine_sd_parameters(self, scales_file):
        '''To some repeated merging (it is assumed that the data have
        already ben scaled) to determine appropriate values of
        sd_add, sd_fac, sd_b for fulls only. FIXME at some point
        this should probably be for each run as well...'''

        if False:
            return (0.0, 0.0, 0.0, 0.0)

        # note to self - the sdB is scaled as the square-root of
        # intensity, so in this situation needs to be massively
        # larger to be useful (perhaps this should follow a power law?)
        # so have inflated the limits by a factor of 100 (should probably
        # be more) to make this useful... FIXME this should rely on an
        # analysis of the actual statistics... allowing 5-times more
        # sdb steps than before too as this is probably most use...
        # alternatively could scale-down all of the reflected intensity
        # values in COMBAT...

        best_sdadd_full = 0.0
        best_sdb_full = 0.0

        max_sdadd_full = 0.1
        max_sdb_full = 10000.0

        step_sdadd_full = 0.01
        step_sdb_full = 200.0

        sdadd_full = 0.0
        sdb_full = 0.0

        best_rms_full = 1.0e9

        # compute sd_add first...

        # FIXME I need to assess whether this route is appropriate, or
        # whether I would be better off following some kind of mimisation
        # procedure...

        # perhaps the following would be more use:
        # 
        # refine SdB based on "flatness" of the curve - flatten it out
        # refine SdAdd afterwards to work on the gradient

        while sdadd_full < max_sdadd_full:
            
            rms_full = self._refine_sd_parameters_remerge(
                scales_file, sdadd_full, sdb_full)

            Chatter.write('Tested SdAdd %4.2f: %4.2f' % \
                          (sdadd_full, rms_full))

            if rms_full < best_rms_full:
                best_sdadd_full = sdadd_full
                best_rms_full = rms_full

            # check to see if we're going uphill again...
            # FIXME in here I have to allow for the scores being
            # exactly zero as an alternative - i.e. there are
            # no reflections which are full, for instance.

            if rms_full > best_rms_full:
                break

            sdadd_full += step_sdadd_full

        best_rms_full = 1.0e9

        # then compute sdb ...

        while sdb_full < max_sdb_full:

            rms_full = self._refine_sd_parameters_remerge(
                scales_file, best_sdadd_full, sdb_full)

            Chatter.write('Tested SdB %4.1f: %4.2f' % \
                          (sdb_full, rms_full))

            if rms_full < best_rms_full:
                best_sdb_full = sdb_full
                best_rms_full = rms_full

            # check to see if we're going uphill again...

            if rms_full > best_rms_full:
                break

            sdb_full += step_sdb_full

        # now we have good parameters for the SdB try rerefining the
        # SdAdd...

        sdadd_full = 0.0
        best_rms_full = 1.0e9
        
        while sdadd_full < max_sdadd_full:
            
            rms_full = self._refine_sd_parameters_remerge(
                scales_file, sdadd_full, best_sdb_full)

            Chatter.write('Tested SdAdd %4.2f: %4.2f' % \
                          (sdadd_full, rms_full))

            if rms_full < best_rms_full:
                best_sdadd_full = sdadd_full
                best_rms_full = rms_full

            if rms_full > best_rms_full:
                break

            sdadd_full += step_sdadd_full

        Chatter.write('Optimised SD corrections (A, B) found to be:')
        Chatter.write('Full:       %4.2f   %4.1f' %
                      (best_sdadd_full, best_sdb_full))

        return best_sdadd_full, best_sdb_full

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

        for epoch in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()
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
                'batch_offset':0                
                }

            # what are these used for?
            # pname / xname / dname - dataset identifiers
            # image to epoch / batch offset / batches - for RD analysis

            Debug.write('For EPOCH %s have:' % str(epoch))
            Debug.write('ID = %s/%s/%s' % (pname, xname, dname))
            Debug.write('SWEEP = %s' % intgr.get_integrater_sweep_name())

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

        if len(self._sweep_information.keys()) > 1:

            lattices = []

            for epoch in self._sweep_information.keys():

                intgr = self._sweep_information[epoch]['integrater']
                hklin = intgr.get_integrater_reflections()
                indxr = intgr.get_integrater_indexer()

                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, indxr)

                lattice = Syminfo.get_lattice(pointgroup)

                if not lattice in lattices:
                    lattices.append(lattice)

                if ntr:
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
                        raise RuntimeError, 'Lattice %s impossible for %s' % \
                              (correct_lattice, sname)
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
            Chatter.write('Using HKLREF %s' % self._reference)

            md = self._factory.Mtzdump()
            md.set_hklin(self.get_scaler_reference_reflection_file())
            md.dump()

            self._spacegroup = Syminfo.spacegroup_name_to_number(
                md.get_spacegroup())

            Chatter.write('Spacegroup %d' % self._spacegroup)

        if len(self._sweep_information.keys()) > 1 and \
               not self.get_scaler_reference_reflection_file():
            # need to generate a reference reflection file - generate this
            # from the reflections in self._first_epoch

            intgr = self._sweep_information[self._first_epoch]['integrater']

            hklin = intgr.get_integrater_reflections()
            indxr = intgr.get_integrater_indexer()
            
            pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                hklin, indxr)

            if ntr:
                need_to_return = True

            # 27/FEB/08 to support user assignment of pointgroups
            if self._scalr_input_pointgroup:
                Chatter.write('Using input pointgroup: %s' % \
                              self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup

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

            if False:

                combat = self._factory.Combat()
                combat.set_hklin(hklin)
                combat.set_hklout(hklout)
                combat.run()

            else:

                pointless = self._factory.Pointless()
                pointless.set_xdsin(hklin)
                pointless.set_hklout(hklout)
                pointless.xds_to_mtz()

            hklin = hklout
            
            hklout = os.path.join(self.get_working_directory(),
                                  'xds-pointgroup-reference-sorted.mtz')
            FileHandler.record_temporary_file(hklout)

            sortmtz = self._factory.Sortmtz()
            sortmtz.add_hklin(hklin)
            sortmtz.set_hklout(hklout)
            sortmtz.sort()

            hklin = hklout

            self._reference = os.path.join(self.get_working_directory(),
                                           'xds-pointgroup-reference.mtz')
            FileHandler.record_temporary_file(self._reference)            

            scala = self._factory.Scala()            
            scala.set_hklin(hklin)
            scala.set_hklout(self._reference)
            scala.quick_scale()            

        if self._reference:

            for epoch in self._sweep_information.keys():

                intgr = self._sweep_information[epoch]['integrater']
                hklin = intgr.get_integrater_reflections()
                indxr = intgr.get_integrater_indexer()

                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, indxr)

                if ntr:
                    need_to_return = True
            
                # 27/FEB/08 to support user assignment of pointgroups
                if self._scalr_input_pointgroup:
                    Chatter.write('Using input pointgroup: %s' % \
                                  self._scalr_input_pointgroup)
                    pointgroup = self._scalr_input_pointgroup
                    
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

                if False:
                
                    combat = self._factory.Combat()
                    combat.set_hklin(hklin)
                    combat.set_hklout(hklout)
                    combat.run()

                else:
                    
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

                # this should send back enough information that this
                # is in the correct pointgroup (from the call above) and
                # also in the correct setting, from the interaction
                # with the reference set... - though I guess that the
                # spacegroup number should not have changed, right?
                
                intgr.set_integrater_reindex_operator(reindex_op)
                intgr.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))

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

            if False:

                combat = self._factory.Combat()
                combat.set_hklin(intgr.get_integrater_reflections())
                combat.set_hklout(hklout)
                combat.run()
                
            else:
                
                pointless = self._factory.Pointless()
                pointless.set_xdsin(intgr.get_integrater_reflections())
                pointless.set_hklout(hklout)
                pointless.xds_to_mtz()

            # run it through pointless interacting with the
            # Indexer which belongs to this sweep

            hklin = hklout 

            pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                hklin, indxr)

            if ntr:
                need_to_return = True

            # 27/FEB/08 to support user assignment of pointgroups
            if self._scalr_input_pointgroup:
                Chatter.write('Using input pointgroup: %s' % \
                              self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup

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
        # average unit cell... using CELLPARM

        cellparm = self.Cellparm()

        for epoch in self._sweep_information.keys():
            integrater = self._sweep_information[epoch]['integrater']
            cell = integrater.get_integrater_cell()
            n_ref = integrater.get_integrater_n_ref()
            
            Debug.write('Cell for %s: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                        (integrater.get_integrater_sweep_name(),
                         cell[0], cell[1], cell[2],
                         cell[3], cell[4], cell[5]))
            Debug.write('=> %d reflections' % n_ref)
            
            cellparm.add_cell(cell, n_ref)

        self._scalr_cell = cellparm.get_cell()

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
            resolution = intgr.get_integrater_resolution()

            if resolution == 0.0:
                raise RuntimeError, 'zero resolution for %s' % \
                      self._sweep_information[epoch][
                    'integrater'].get_integrater_sweep_name()

            Debug.write('Epoch: %d' % epoch)
            Debug.write('HKL: %s (%s)' % (reflections, dname))

            xscale.add_reflection_file(reflections, dname, resolution)

        # set the global properties of the sample
        xscale.set_crystal(self._scalr_xname)
        xscale.set_anomalous(self._scalr_anomalous)

        if Flags.get_zero_dose():
            Debug.write('Switching on zero-dose extrapolation')
            xscale.set_zero_dose()

        # do the scaling keeping the reflections unmerged

        xscale.run()

        # record the log file 

        pname = self._scalr_pname
        xname = self._scalr_xname

        FileHandler.record_log_file('%s %s XSCALE' % \
                                    (pname, xname),
                                    os.path.join(self.get_working_directory(),
                                                 'XSCALE.LP'))

        # check for outlier reflections and if a number are found
        # then iterate (that is, rerun XSCALE, rejecting these outliers)

        if not Flags.get_quick():
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
        resolution_limits = { }

        for epoch in self._sweep_information.keys():
            
            input = self._sweep_information[epoch]

            intgr = input['integrater']

            if intgr.get_integrater_user_resolution():
                dmin = intgr.get_integrater_high_resolution()
                
                if not user_resolution_limits.has_key(input['dname']):
                    user_resolution_limits[input['dname']] = dmin
                elif dmin < user_resolution_limits[input['dname']]:
                    user_resolution_limits[input['dname']] = dmin

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
                hklin, 'SCALED_', project_info)

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

            Chatter.write('In reflection file %s found:' % hklin)
            for d in datasets:
                Chatter.write('... %s' % d)
            
            dataset_info = md.get_dataset_info(datasets[0])

            # FIXME should also confirm the batch numbers from this
            # reflection file...

            # now make the comparison - FIXME this needs to be implemented
            # FIXME also - if the pname, xname, dname is not defined by
            # this time, make a note of this so that it can be included
            # at a later stage.

        Chatter.write('Biggest sweep has %d batches' % max_batches)
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

            hklin = self._sweep_information[epoch]['scaled_reflections']

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

        # then sort the files together, making sure that the resulting
        # reflection file looks right.

        s = self._factory.Sortmtz()

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted.mtz' % \
                              (self._common_pname, self._common_xname))
        
        s.set_hklout(hklout)

        for epoch in epochs:
            s.add_hklin(self._sweep_information[epoch]['hklin'])

        s.sort()

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

            # get one spacegroup and so on which will be used for
            # all of the reflection files...
            
            spacegroups = pointless.get_likely_spacegroups()
            reindex_operator = pointless.get_spacegroup_reindex_operator()

            if self._scalr_input_spacegroup:
                Chatter.write('Assigning user input spacegroup: %s' % \
                              self._scalr_input_spacegroup)
                spacegroups = [self._scalr_input_spacegroup]
                reindex_operator = 'h,k,l'

        # save these for later - we will reindex the merged
        # data after scaling - the first of these will be used
        # as correct so spacegroup assignment should just work...

        self._scalr_likely_spacegroups = spacegroups
        self._scalr_reindex_operator = reindex_operator

        Debug.write('Reindex operator: %s' % reindex_operator)
        Debug.write('Will save this for later')

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
                       dname = input['dname'])

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

            resolution = _resolution_estimate(
                resolution_points, Flags.get_i_over_sigma_limit())

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

        Chatter.write('Scaler highest resolution set to %5.2f' % \
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
                Chatter.write('Quick, so not resetting resolution limits')

            elif intgr.get_integrater_user_resolution():
                Chatter.write('Using user specified resolution limits')

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
            Chatter.write('Returning as scaling not finished...')
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

        if Flags.get_quick() or not Flags.get_fiddle_sd():
            Chatter.write('Not optimising error parameters')
            sdadd_full = 0.0
            sdb_full = 0.0

        elif average_completeness < 50.0:
            Chatter.write('Incomplete data, so not refining error parameters')
            sdadd_full = 0.0
            sdb_full = 0.0

        else:

            # ---------- SD CORRECTION PARAMETER LOOP ----------
            
            # first "fix" the sd add parameters to match up the sd curve from
            # the fulls only, and minimise RMS[N (scatter / sigma - 1)]
            
            Chatter.write('Optimising error parameters')
            
            sdadd_full, sdb_full = self._refine_sd_parameters(scales_file)

            try:
                os.remove(os.path.join(self.get_working_directory(),
                                       scales_file))
            except:
                Chatter.write('Error removing %s' % scales_file)

        # then try tweaking the sdB parameter in a range say 0-20
        # starting at 0 and working until the RMS stops going down

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
        sc.add_sd_correction('both', 1.0, sdadd_full, sdb_full)

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

            for j in range(len(info['1_Range'])):
                n_full = int(info['5_Number'][j])
                I_full = float(info['4_Irms'][j])
                s_full = float(info['7_SigmaFull'][j])

                i_tot = I_full
                s_tot = s_full

                # FIXME is this useless dead code???


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
            m2v = self._factory.Mtz2various()
            m2v.set_hklin(file)
            m2v.set_hklout('%s.sca' % file[:-4])
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][
                key] = '%s.sca' % file[:-4]

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
                sc.set_resolution(resolution_limits[dname])

            sc.set_hklout(os.path.join(self.get_working_directory(),
                                           'temp.mtz'))
                
            if self.get_scaler_anomalous():
                sc.set_anomalous()
                
            sc.multi_merge()
            stats = sc.get_summary()

            # this should just work ... by magic!
            self._scalr_statistics[key] = stats[key]

        self._scalr_highest_resolution = best_resolution
                   
        return

    def _scale_finish(self):
        
        # next transform to F's from I's

        if len(self._tmp_scaled_refl_files.keys()) == 0:
            raise RuntimeError, 'no reflection files stored'

        for wavelength in self._tmp_scaled_refl_files.keys():

            hklin = self._tmp_scaled_refl_files[wavelength]

            # perhaps reindex first?

            # FIXED in here need to check if the spacegroup
            # needs assigning e.g. from P 2 2 2 to P 21 21 21
            # bug 2511
            
            if self._scalr_reindex_operator != 'h,k,l':

                hklout = os.path.join(self.get_working_directory(),
                                      '%s_reindexed.mtz' % wavelength)
                FileHandler.record_temporary_file(hklout)

                Debug.write('Reindexing operator = %s' % \
                            self._scalr_reindex_operator)
                
                reindex = self._factory.Reindex()
                reindex.set_hklin(hklin)
                reindex.set_spacegroup(self._scalr_likely_spacegroups[0])
                reindex.set_operator(self._scalr_reindex_operator)
                reindex.set_hklout(hklout)
                reindex.reindex()
                hklin = hklout

                # record the updated cell parameters...
                # they should be the same in all files so...
                Debug.write(
                    'Updating unit cell to %.2f %.2f %.2f %.2f %.2f %.2f' % \
                    tuple(reindex.get_cell()))
                self._scalr_cell = tuple(reindex.get_cell())

            else:
                # just assign the spacegroup - note that this may be
                # a worthless step, but never mind...

                hklout = os.path.join(self.get_working_directory(),
                                      '%s_reindexed.mtz' % wavelength)
                FileHandler.record_temporary_file(hklout)

                Debug.write('Setting spacegroup = %s' % \
                            self._scalr_likely_spacegroups[0])
                
                reindex = self._factory.Reindex()
                reindex.set_hklin(hklin)
                reindex.set_spacegroup(self._scalr_likely_spacegroups[0])
                reindex.set_hklout(hklout)
                reindex.reindex()
                hklin = hklout

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
            
        # and cad together into a single data set - recalling that we already
        # have a standard unit cell... and remembering where the files go...

        self._scalr_scaled_reflection_files = { }

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

            Chatter.write('Merging all data sets to %s' % hklout)

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
                              '%s_%s_free.mtz' % (self._common_pname,
                                                  self._common_xname))
        
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

            f = self._factory.Freerflag()
            f.set_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
            f.set_hklout(hklout)
            f.add_free_flag()

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
            Chatter.write('Not sure what this means (1.6 < score < 1.9)')

        # next have a look for radiation damage... if more than one wavelength

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
            Chatter.write('Inter-wavelength radiation damage analysis.')
            for s in status:
                Chatter.write('%s %s' % s)
            Chatter.write('')
        

        return

