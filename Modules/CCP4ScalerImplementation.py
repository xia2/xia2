#!/usr/bin/env python
# CCP4ScalerImplementation.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the terms and conditions of the
#   CCP4 Program Suite Licence Agreement as a CCP4 Library.
#   A copy of the CCP4 licence can be obtained by writing to the
#   CCP4 Secretary, Daresbury Laboratory, Warrington WA4 4AD, UK.
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
# FIXME 27/SEP/06 need to define a reference wavelength for the anomalous
#                 dispersive differences. This is best assigned at this 
#                 level as the wavelength with the smallest |f'| + |f''|
#                 or something:
# 
#                 BASE keyword to scala - BASE [crystal xname] dataset dname
# 
#                 This defaults to the data set with the shortest wavelength.
#  
# FIXME 27/OCT/06 need to make sure that the pointless run in here does not
#                 select a symmetry for the crystal which has been eliminated
#                 already...
# 
# FIXME 31/OCT/06 need to make the scaling do the following:
#                 (1) assert a sensible resolution limit.
#                 (2) twiddle the sd parameters to get the flattest
#                     error curve possible.
#                 (3) limit by batch in radiation damage terms.
#                 (4) eliminate badly radiation damaged data in different
#                     sweeps.
#
# FIXME 01/NOV/06 should probably sort together all data for a particular
#                 wavelength before running pointless - this will probably
#                 give better statistics from that program.
#  
# FIXME 03/NOV/06 need to merge the first sweep in whatever pointgroup we 
#                 think is correct, and then reindex the rest of this data
#                 using the first one as a reference, and then perform the 
#                 scaling based on this. TS02 breaks on the unit cell check
#                 at the CAD phase below.
#
# FIXME 03/NOV/06 should check that the reflection files have consistent
#                 unit cell parameters going in to scaling. c/f FIXME above.
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
# FIXME 06/NOV/06 need also to investigate the systematic absences and reset
#                 to a standard setting (pointless does this) if appropriate.
#                 If it's P43212 or P41212 then I need to decide what is 
#                 best to do...

import os
import sys
import math

if not os.environ.has_key('DPA_ROOT'):
    raise RuntimeError, 'DPA_ROOT not defined'

if not os.environ['DPA_ROOT'] in sys.path:
    sys.path.append(os.environ['DPA_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.Scaler import Scaler

# the wrappers that this will use - these are renamed so that the internal
# factory version can be used...
from Wrappers.CCP4.Scala import Scala as _Scala
from Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz
from Wrappers.CCP4.Mtzdump import Mtzdump as _Mtzdump
from Wrappers.CCP4.Truncate import Truncate as _Truncate
from Wrappers.CCP4.Rebatch import Rebatch as _Rebatch
from Wrappers.CCP4.Reindex import Reindex as _Reindex
from Wrappers.CCP4.Mtz2various import Mtz2various as _Mtz2various
from Wrappers.CCP4.Cad import Cad as _Cad
from Wrappers.CCP4.Pointless import Pointless as _Pointless

from Handlers.Streams import Chatter

# jiffys
from lib.Guff import is_mtz_file, nifty_power_of_ten, auto_logfiler
from lib.Guff import transpose_loggraph

class CCP4Scaler(Scaler):
    '''An implementation of the Scaler interface using CCP4 programs.'''

    def __init__(self):
        Scaler.__init__(self)

        self._working_directory = os.getcwd()

        self._sweep_information = { }

        # hacky... this is to pass information from prepare to scale
        # and could probably be handled better (they used to be
        # all in just the scale() method)
        
        self._prepared_reflections = None
        self._common_pname = None
        self._common_xname = None
        self._common_dname = None

        return

    # factory methods...

    def Scala(self):
        '''Create a Scala wrapper from _Scala - set the working directory
        and log file stuff as a part of this...'''
        scala = _Scala()
        scala.set_working_directory(self.get_working_directory())
        auto_logfiler(scala)
        return scala

    def Sortmtz(self):
        '''Create a Sortmtz wrapper from _Sortmtz - set the working directory
        and log file stuff as a part of this...'''
        sortmtz = _Sortmtz()
        sortmtz.set_working_directory(self.get_working_directory())
        auto_logfiler(sortmtz)
        return sortmtz

    def Mtzdump(self):
        '''Create a Mtzdump wrapper from _Mtzdump - set the working directory
        and log file stuff as a part of this...'''
        mtzdump = _Mtzdump()
        mtzdump.set_working_directory(self.get_working_directory())
        auto_logfiler(mtzdump)
        return mtzdump

    def Truncate(self):
        '''Create a Truncate wrapper from _Truncate - set the working directory
        and log file stuff as a part of this...'''
        truncate = _Truncate()
        truncate.set_working_directory(self.get_working_directory())
        auto_logfiler(truncate)
        return truncate

    def Rebatch(self):
        '''Create a Rebatch wrapper from _Rebatch - set the working directory
        and log file stuff as a part of this...'''
        rebatch = _Rebatch()
        rebatch.set_working_directory(self.get_working_directory())
        auto_logfiler(rebatch)
        return rebatch

    def Reindex(self):
        '''Create a Reindex wrapper from _Reindex - set the working directory
        and log file stuff as a part of this...'''
        reindex = _Reindex()
        reindex.set_working_directory(self.get_working_directory())
        auto_logfiler(reindex)
        return reindex

    def Mtz2various(self):
        '''Create a Mtz2various wrapper from _Mtz2various - set the working
        directory and log file stuff as a part of this...'''
        mtz2various = _Mtz2various()
        mtz2various.set_working_directory(self.get_working_directory())
        auto_logfiler(mtz2various)
        return mtz2various

    def Cad(self):
        '''Create a Cad wrapper from _Cad - set the working directory
        and log file stuff as a part of this...'''
        cad = _Cad()
        cad.set_working_directory(self.get_working_directory())
        auto_logfiler(cad)
        return cad

    def Pointless(self):
        '''Create a Pointless wrapper from _Pointless - set the working directory
        and log file stuff as a part of this...'''
        pointless = _Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)
        return pointless

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory 

    def _scale_prepare(self):
        '''Perform all of the preparation required to deliver the scaled
        data. This should sort together the reflection files, ensure that
        they are correctly indexed (via pointless) and generally tidy
        things up.'''

        # ---------- GATHER ----------

        # first gather reflection files - seeing as we go along if any
        # of them need transforming to MTZ format, e.g. from d*TREK
        # format. N.B. this will also require adding the project,
        # crystal, dataset name from the parent integrater.

        # FIXED 30/OCT/06 in here need to check that the input batches
        # are not 0,0 - because if they are I will need to do some
        # MTZ dumping... see a little further down!

        self._sweep_information = { }

        for epoch in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_information()
            self._sweep_information[epoch] = {
                'hklin':intgr.get_integrater_reflections(),
                'pname':pname,
                'xname':xname,
                'dname':dname,
                'batches':intgr.get_integrater_batches()}
            
        # next check through the reflection files that they are all MTZ
        # format - if not raise an exception.
        # FIXME this should include the conversion to MTZ.
        
        epochs = self._sweep_information.keys()

        for epoch in epochs:
            if not is_mtz_file(self._sweep_information[epoch]['hklin']):
                raise RuntimeError, \
                      'input file %s not MTZ format' % \
                      self._sweep_information[epoch]['hklin']

        self._common_pname = self._sweep_information[epochs[0]]['pname']
        self._common_xname = self._sweep_information[epochs[0]]['xname']
        self._common_dname = self._sweep_information[epochs[0]]['dname']

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
            dname = self._sweep_information[epoch]['dname']
            if self._common_dname != dname:
                self._common_dname = None



        # FIXME 06/NOV/06 and before, need to merge the first reflection
        # file in the "correct" pointgroup, so that the others can be
        # reindexed against this - this will ensure consistent indexing
        # in the TS02 case where the unit cell parameters are a bit fiddly.

        # get the "first" sweep (in epoch terms)

        # ---------- GENERATE REFERENCE SET ----------

        # pointless it, sort it, quick scale it

        # record this as the reference set, feed this to all subsequent
        # pointless runs through HKLREF (FIXED this needs to be added to the
        # pointless interface - set_hklref()!) 

        epochs = self._sweep_information.keys()
        epochs.sort()
        first = epochs[0]
        
        pl = self.Pointless()
        hklin = self._sweep_information[first]['hklin']
        hklout = os.path.join(
            self.get_working_directory(),
            os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))
        pl.set_hklin(hklin)

        # write a pointless log file...
        pl.decide_pointgroup()
        
        Chatter.write('Pointless analysis of %s' % hklin)

        # FIXME here - do I need to contemplate reindexing
        # the reflections? if not, don't bother - could be an
        # expensive waste of time for large reflection files
        # (think Ed Mitchell data...)
        
        # get the correct pointgroup
        pointgroup = pl.get_pointgroup()
        
        # and reindexing operation
        reindex_op = pl.get_reindex_operator()
        
        Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

        # perform a reindexing operation
        ri = self.Reindex()
        ri.set_hklin(hklin)
        ri.set_hklout(hklout)
        ri.set_spacegroup(pointgroup)
        ri.set_operator(reindex_op)
        ri.reindex()
        
        # next sort this reflection file
            
        hklin = hklout
        hklout = os.path.join(
            self.get_working_directory(),
            os.path.split(hklin)[-1].replace('_rdx.mtz', '_ref_srt.mtz'))

        s = self.Sortmtz()
        s.set_hklout(hklout)
        s.add_hklin(hklin)
        s.sort()
        
        # now quickly merge the reflections

        hklin = hklout
        reference = os.path.join(
            self.get_working_directory(),
            os.path.split(hklin)[-1].replace('_ref_srt.mtz', '_ref.mtz'))

        # need to remember this hklout - it will be the reference reflection
        # file for all of the reindexing below...

        Chatter.write('Quickly scaling reference data set: %s' % \
                      os.path.split(hklin)[-1])

        qsc = self.Scala()
        qsc.set_hklin(hklin)
        qsc.set_hklout(reference)
        qsc.quick_scale()

        # for the moment ignore all of the scaling statistics and whatnot!

        # then check that the unit cells &c. in these reflection files
        # correspond to those rescribed in the indexers belonging to the
        # parent integraters.

        # at this stage (see FIXME from 25/SEP/06) I need to run pointless
        # to assess the likely pointgroup. This, unfortunately, will need to
        # tie into the .xinfo hierarchy, as the crystal lattice management
        # takes place in there...
        # also need to make sure that the results from each sweep match
        # up...

        # FIXME 27/OCT/06 need a hook in here to the integrater->indexer
        # to inspect the lattices which have ben contemplated (read tested)
        # because it is quite possible that pointless will come up with
        # a solution which has already been eliminated in the data reduction
        # (e.g. TS01 native being reindexed to I222.)

        # FIXME 06/NOV/06 first run through this with the reference ignored
        # to get the reflections reindexed into the correct pointgroup

        # ---------- REINDEX TO CORRECT POINTGROUP ----------
        
        for epoch in self._sweep_information.keys():
            pl = self.Pointless()
            hklin = self._sweep_information[epoch]['hklin']
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))
            pl.set_hklin(hklin)

            # write a pointless log file...
            pl.decide_pointgroup()

            Chatter.write('Pointless analysis of %s' % hklin)

            # FIXME here - do I need to contemplate reindexing
            # the reflections? if not, don't bother - could be an
            # expensive waste of time for large reflection files
            # (think Ed Mitchell data...)

            # get the correct pointgroup
            pointgroup = pl.get_pointgroup()

            # and reindexing operation
            reindex_op = pl.get_reindex_operator()

            Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            # perform a reindexing operation
            ri = self.Reindex()
            ri.set_hklin(hklin)
            ri.set_hklout(hklout)
            ri.set_spacegroup(pointgroup)
            ri.set_operator(reindex_op)
            ri.reindex()

            # record the change in reflection file...
            self._sweep_information[epoch]['hklin'] = hklout

        # FIXME 06/NOV/06 need to run this again - this time with the
        # reference file... messy but perhaps effective?

        # ---------- REINDEX TO CORRECT SETTING ---------- 

        for epoch in self._sweep_information.keys():
            pl = self.Pointless()
            hklin = self._sweep_information[epoch]['hklin']
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('_rdx.mtz', '_rdx2.mtz'))
            pl.set_hklin(hklin)

            # now set the initial reflection set as a reference...
            
            pl.set_hklref(reference)

            # write a pointless log file...
            pl.decide_pointgroup()

            Chatter.write('Pointless analysis of %s' % hklin)

            # FIXME here - do I need to contemplate reindexing
            # the reflections? if not, don't bother - could be an
            # expensive waste of time for large reflection files
            # (think Ed Mitchell data...)

            # get the correct pointgroup
            pointgroup = pl.get_pointgroup()

            # and reindexing operation
            reindex_op = pl.get_reindex_operator()

            Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            # perform a reindexing operation
            ri = self.Reindex()
            ri.set_hklin(hklin)
            ri.set_hklout(hklout)
            ri.set_spacegroup(pointgroup)
            ri.set_operator(reindex_op)
            ri.reindex()

            # record the change in reflection file...
            self._sweep_information[epoch]['hklin'] = hklout

        # ---------- SORT TOGETHER DATA ----------
            
        max_batches = 0
        
        for epoch in self._sweep_information.keys():

            # keep a count of the maximum number of batches in a block -
            # this will be used to make rebatch work below.

            hklin = self._sweep_information[epoch]['hklin']

            md = self.Mtzdump()
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
            rb = self.Rebatch()

            hklin = self._sweep_information[epoch]['hklin']

            pname = self._sweep_information[epoch]['pname']
            xname = self._sweep_information[epoch]['xname']
            dname = self._sweep_information[epoch]['dname']

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_%s_%d.mtz' % \
                                  (pname, xname, dname, counter))

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

        s = self.Sortmtz()
        s.set_hklout(os.path.join(self.get_working_directory(),
                                  '%s_%s_sorted.mtz' % \
                                  (self._common_pname, self._common_xname)))

        for epoch in epochs:
            s.add_hklin(self._sweep_information[epoch]['hklin'])

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

        sc = self.Scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        sc.add_sd_correction('full', 1.0, sdadd_f, sdb_f)
        sc.add_sd_correction('partial', 1.0, sdadd_p, sdb_p)
        
        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(), 'temp.mtz'))

        # FIXME this needs to be set only is we have f', f'' values
        # for the wavelength
        
        sc.set_anomalous()
        sc.set_tails()
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
                n_full = int(info['5_Number'][j])
                I_full = float(info['4_Irms'][j])
                s_full = float(info['7_SigmaFull'][j])

                n_partial = int(info['9_Number'][j])
                I_partial = float(info['8_Irms'][j])
                s_partial = float(info['11_SigmaPartial'][j])
                
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

                # FIXME should this really measure the errors in terms
                # of total numbers of reflections, or just flatten the
                # graph???

                # TEST! Solve the structures and work out what is better...

                # bugger! trying to minimise difference between this and
                # 1.0!
                
                s_full -= 1.0
                s_partial -= 1.0

                # try uniform weighting...

                if n_full > 0:
                    n_full = 1
                if n_partial > 0:
                    n_partial = 1

                # end try uniform weighting...

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

        max_sdadd_full = 0.1
        max_sdadd_partial = 0.1
        max_sdb_full = 20.0
        max_sdb_partial = 20.0

        step_sdadd_full = 0.01
        step_sdadd_partial = 0.01
        step_sdb_full = 2.0
        step_sdb_partial = 2.0

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

        while sdadd_full < max_sdadd_full:
            
            sdadd_partial = sdadd_full

            rms_full, rms_partial = self._refine_sd_parameters_remerge(
                scales_file, sdadd_full, sdb_full, sdadd_partial, sdb_partial)

            Chatter.write('Tested SdAdd %4.2f: %4.2f %4.2f' % \
                          (sdadd_full, rms_full, rms_partial))

            if rms_full < best_rms_full:
                best_sdadd_full = sdadd_full
                best_rms_full = rms_full

            if rms_partial < best_rms_partial:
                best_sdadd_partial = sdadd_partial
                best_rms_partial = rms_partial

            # check to see if we're going uphill again...

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

            Chatter.write('Tested SdB %4.1f: %4.2f %4.2f' % \
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

        # FIXME in here I need to implement "proper" scaling...
        # this will need to do things like imposing a sensible
        # resolution limit on the data, deciding on the appropriate
        # scaling parameters. The former is best done by analysing
        # the "by resolution" output for each run, and then passing
        # this information back somewhere. The latter can be achieved
        # by a search using "onlymerge restore" type commands.

        # ---------- INITIAL SCALING ----------

        sc = self.Scala()
        sc.set_hklin(self._prepared_reflections)

        # generate a name for the "scales" file - this will be used for
        # recycling the scaling parameters to compute appropriate
        # sd correction parameters

        scales_file = os.path.join(self.get_working_directory(),
                                   '%s.scales' % self._common_xname)

        sc.set_new_scales_file(scales_file)

        # this will require first sorting out the batches/runs, then
        # deciding what the "standard" wavelength/dataset is, then
        # combining everything appropriately...

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        # FIXME this needs to be set only is we have f', f'' values
        # for the wavelength
        
        sc.set_anomalous()
        sc.set_tails()

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

        for key in loggraph.keys():
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

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

        # ---------- SD CORRECTION PARAMETER LOOP ----------

        # first "fix" the sd add parameters to match up the sd curve from
        # the fulls and partials, and minimise RMS[N (scatter / sigma - 1)]

        Chatter.write('Optimising error parameters')

        sdadd_full, sdb_full, sdadd_partial, sdb_partial = \
                    self._refine_sd_parameters(scales_file)

        # then try tweaking the sdB parameter in a range say 0-20
        # starting at 0 and working until the RMS stops going down

        # ---------- FINAL SCALING ----------

        # assert the resolution limits in the integraters - beware, this
        # means that the reflection files will probably have to be
        # regenerated (integration restarted!) and so we will have to
        # build in some "fudge factor" to ensure we don't get stuck in a
        # tight loop - initially just rerun the scaling with all of the
        # "right" parameters...
        
        sc = self.Scala()
        sc.set_hklin(self._prepared_reflections)

        sc.add_sd_correction('full', 1.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 1.0, sdadd_partial, sdb_partial)

        sc.set_new_scales_file(scales_file)

        # this will require first sorting out the batches/runs, then
        # deciding what the "standard" wavelength/dataset is, then
        # combining everything appropriately...

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))
            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._common_pname, self._common_xname)))
        
        # FIXME this needs to be set only is we have f', f'' values
        # for the wavelength
        
        sc.set_anomalous()
        sc.set_tails()

        sc.scale()

        # then gather up all of the resulting reflection files
        # and convert them into the required formats (.sca, .mtz.)

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()

        # parse the statistics from Scala - these are printed in the
        # loggraph output, and therefore need some transformation &
        # massaging to be useful.

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
                n_full = int(info['5_Number'][j])
                I_full = float(info['4_Irms'][j])
                s_full = float(info['7_SigmaFull'][j])

                n_part = int(info['9_Number'][j])
                I_part = float(info['8_Irms'][j])
                s_part = float(info['11_SigmaPartial'][j])
                
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


        # finally put all of the results "somewhere useful"
        
        self._scalr_statistics = data

        # FIXME this is not correct for multi-wavelength data...
        # it should be now!

        scaled_reflection_files = sc.get_scaled_reflection_files()
        self._scalr_scaled_reflection_files = { }
        
        # compute a "standard unit cell" - FIXME perhaps - looks like
        # sortmtz will already assign somehow a standard unit cell -
        # interesting!

        # convert reflection files to .sca format - use mtz2various for this

        self._scalr_scaled_reflection_files['sca'] = { }
        for key in scaled_reflection_files:
            file = scaled_reflection_files[key]
            m2v = self.Mtz2various()
            m2v.set_hklin(file)
            m2v.set_hklout('%s.sca' % file[:-4])
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][
                key] = '%s.sca' % file[:-4]

        # convert I's to F's in Truncate

        self._scalr_scaled_reflection_files['mtz'] = { }
        for key in scaled_reflection_files.keys():
            file = scaled_reflection_files[key]
            t = self.Truncate()
            t.set_hklin(file)

            # this is tricksy - need to really just replace the last
            # instance of this string FIXME 27/OCT/06

            hklout = ''
            for path in os.path.split(file)[:-1]:
                hklout = os.path.join(hklout, path)
            hklout = os.path.join(hklout, os.path.split(file)[-1].replace(
                '_scaled', '_truncated'))
            t.set_hklout(hklout)
            t.truncate()

            # replace old with the new version which has F's in it 
            scaled_reflection_files[key] = hklout

            # record the separated reflection file too
            self._scalr_scaled_reflection_files['mtz'][key] = hklout

        # standardise the unit cells and relabel each of the columns in
        # each reflection file appending the DNAME to the column name

        # compute a standard unit cell here - this should be equal to
        # an average of the unit cells in each of the reflection files,
        # weighted according to (1) the number of reflections and
        # perhaps (2) the epoch order of that data set...

        average_cell_a = 0.0
        average_cell_b = 0.0
        average_cell_c = 0.0
        average_cell_alpha = 0.0
        average_cell_beta = 0.0
        average_cell_gamma = 0.0

        average_cell_nref = 0

        for key in scaled_reflection_files.keys():
            hklin = scaled_reflection_files[key]
            md = self.Mtzdump()
            md.set_hklin(hklin)
            md.dump()
            datasets = md.get_datasets()
            reflections = md.get_reflections()

            # ASSERT at this stage there should be exactly one dataset
            # in each reflection file - however we won't make that
            # assumption here as that could get us into trouble later on

            if average_cell_nref == 0:
                # this is the first data set - take these as read
                for d in datasets:
                    info = md.get_dataset_info(d)
                    cell = info['cell']

                    Chatter.write('%d reflections in dataset %s' % \
                                  (reflections, d))
                    
                    average_cell_nref += reflections
                    average_cell_a += cell[0] * reflections
                    average_cell_b += cell[1] * reflections
                    average_cell_c += cell[2] * reflections
                    average_cell_alpha += cell[3] * reflections
                    average_cell_beta += cell[4] * reflections
                    average_cell_gamma += cell[5] * reflections

            else:
                # as above, but also check that the unit cell parameters
                # are reasonably compatible with the current running average
                for d in datasets:
                    info = md.get_dataset_info(d)
                    cell = info['cell']

                    # check the cell - allow 0.5A, 0.5 degrees - this
                    # is shockingly wide!

                    Chatter.write('%d reflections in dataset %s' % \
                                  (reflections, d))

                    if math.fabs(cell[0] -
                                 (average_cell_a / average_cell_nref)) > 0.5:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d
                    if math.fabs(cell[1] -
                                 (average_cell_b / average_cell_nref)) > 0.5:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d
                    if math.fabs(cell[2] -
                                 (average_cell_c / average_cell_nref)) > 0.5:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d
                    if math.fabs(cell[3] -
                                 (average_cell_alpha /
                                  average_cell_nref)) > 0.5:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d
                    if math.fabs(cell[4] -
                                 (average_cell_beta /
                                  average_cell_nref)) > 0.5:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d
                    if math.fabs(cell[5] -
                                 (average_cell_gamma /
                                  average_cell_nref)) > 0.5:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d

                    average_cell_nref += reflections
                    average_cell_a += cell[0] * reflections
                    average_cell_b += cell[1] * reflections
                    average_cell_c += cell[2] * reflections
                    average_cell_alpha += cell[3] * reflections
                    average_cell_beta += cell[4] * reflections
                    average_cell_gamma += cell[5] * reflections

        average_unit_cell = (average_cell_a / average_cell_nref,
                             average_cell_b / average_cell_nref,
                             average_cell_c / average_cell_nref,
                             average_cell_alpha / average_cell_nref,
                             average_cell_beta / average_cell_nref,
                             average_cell_gamma / average_cell_nref)

        Chatter.write('Computed average unit cell (will use in all files)')
        Chatter.write('%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                      average_unit_cell)

        for key in scaled_reflection_files.keys():
            file = scaled_reflection_files[key]
            
            c = self.Cad()
            c.add_hklin(file)
            c.set_new_suffix(key)
            c.set_new_cell(average_unit_cell)
            hklout = '%s_cad.mtz' % file[:-4]
            c.set_hklout(hklout)
            c.update()
            
            scaled_reflection_files[key] = hklout

        # merge all columns into a single uber-reflection-file
        # FIXME this is only worth doing if there are more
        # than one scaled reflection file...

        if len(scaled_reflection_files.keys()) > 1:

            c = self.Cad()
            for key in scaled_reflection_files.keys():
                file = scaled_reflection_files[key]
                c.add_hklin(file)
        
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_merged.mtz' % (self._common_pname,
                                                        self._common_xname))

            Chatter.write('Merging all data sets to %s' % hklout)

            c.set_hklout(hklout)
            c.merge()
            
            self._scalr_scaled_reflection_files['mtz_merged'] = hklout

        else:

            # we don't need to explicitly merge it, since that's just
            # silly ;o)
            
            self._scalr_scaled_reflection_files[
                'mtz_merged'] = scaled_reflection_files[
                scaled_reflection_files.keys()[0]]

        return

    
