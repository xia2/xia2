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

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.Scaler import Scaler

# the wrappers that this will use - these are renamed so that the internal
# factory version can be used...
from Wrappers.CCP4.Scala import Scala as _Scala
from Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz
from Wrappers.CCP4.Mtzdump import Mtzdump as _Mtzdump
from Wrappers.CCP4.Truncate import Truncate as _Truncate
from Wrappers.CCP4.Rebatch import Rebatch as _Rebatch
from Wrappers.CCP4.Mtz2various import Mtz2various as _Mtz2various
from Wrappers.CCP4.Cad import Cad as _Cad
from Wrappers.CCP4.Freerflag import Freerflag as _Freerflag
from Wrappers.CCP4.Pointless import Pointless as _Pointless
from Wrappers.CCP4.Sfcheck import Sfcheck as _Sfcheck

from Wrappers.CCP4.CCP4Factory import CCP4Factory

from Handlers.Streams import Chatter
from Handlers.Files import FileHandler
from Handlers.Citations import Citations
from Handlers.Flags import Flags        
from Handlers.Syminfo import Syminfo

# jiffys
from lib.Guff import is_mtz_file, nifty_power_of_ten, auto_logfiler
from lib.Guff import transpose_loggraph, nint
from lib.SymmetryLib import lattices_in_order

from CCP4ScalerImplementationHelpers import _resolution_estimate, \
     _prepare_pointless_hklin, _fraction_difference

from CCP4InterRadiationDamageDetector import CCP4InterRadiationDamageDetector

# See FIXME_X0001 below...
# from CCP4IntraRadiationDamageDetector import CCP4IntraRadiationDamageDetector

class CCP4Scaler(Scaler):
    '''An implementation of the Scaler interface using CCP4 programs.'''

    def __init__(self):
        Scaler.__init__(self)

        self._sweep_information = { }

        # hacky... this is to pass information from prepare to scale
        # and could probably be handled better (they used to be
        # all in just the scale() method)
        
        self._prepared_reflections = None
        self._common_pname = None
        self._common_xname = None
        self._common_dname = None

        self._factory = CCP4Factory()

        return

    # This is overloaded from the Scaler interface...
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        return

    # factory methods...

    def Scala(self):
        return self._factory.Scala()

    def Sortmtz(self):
        return self._factory.Sortmtz()

    def Mtzdump(self):
        return self._factory.Mtzdump()

    def Truncate(self):
        return self._factory.Truncate()

    def Rebatch(self):
        return self._factory.Rebatch()

    def Reindex(self):
        return self._factory.Reindex()

    def Mtz2various(self):
        return self._factory.Mtz2various()

    def Cad(self):
        return self._factory.Cad()

    def Freerflag(self):
        return self._factory.Freerflag()

    def Pointless(self):
        return self._factory.Pointless()

    def Sfcheck(self):
        return self._factory.Sfcheck()

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

        for epoch in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()
            self._sweep_information[epoch] = {
                'pname':pname,
                'xname':xname,
                'dname':dname,
                'batches':intgr.get_integrater_batches(),
                'integrater':intgr,
                'header':intgr.get_header(),
                'image_to_epoch':intgr.get_integrater_sweep(                
                ).get_image_to_epoch(),
                'batch_offset':0
                }
            
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

        # record the project and crystal in the scaler interface - for
        # future reference

        self._scalr_pname = self._common_pname
        self._scalr_xname = self._common_xname

        # FIXME 06/NOV/06 and before, need to merge the first reflection
        # file in the "correct" pointgroup, so that the others can be
        # reindexed against this - this will ensure consistent indexing
        # in the TS02 case where the unit cell parameters are a bit fiddly.

        if len(self._sweep_information.keys()) > 1:

            # ---------- PREPARE REFERENCE SET ----------

            # pointless it, sort it, quick scale it

            # record this as the reference set, feed this to all subsequent
            # pointless runs through HKLREF (FIXED this needs to be added to
            # the pointless interface - set_hklref()!) 

            epochs = self._sweep_information.keys()
            epochs.sort()
            first = epochs[0]

            hklin = self._sweep_information[first][
                'integrater'].get_integrater_reflections()
            header = self._sweep_information[first]['header']

            # prepare pointless hklin makes something much smaller...

            pl = self.Pointless()
            pl.set_hklin(_prepare_pointless_hklin(
                self.get_working_directory(),
                hklin, self._sweep_information[epoch]['header'].get(
                'phi_width', 0.0)))

            pl.decide_pointgroup()

            integrater = self._sweep_information[epoch]['integrater']
            indexer = integrater.get_integrater_indexer()
            
            if indexer:
                # flag to record whether I need to do some rerunning
                rerun_pointless = False
                
                possible = pl.get_possible_lattices()
                
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
                    pl.set_correct_lattice(correct_lattice)
                    pl.decide_pointgroup()

            Chatter.write('Pointless analysis of %s' % pl.get_hklin())

            pointgroup = pl.get_pointgroup()
            reindex_op = pl.get_reindex_operator()
        
            Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))

            # we will want to delete this one exit
            # FileHandler.record_temporary_file(hklout)

            # tell the integrater about this - may not be too much
            # of a problem...

            integrater.set_integrater_reindex_operator(reindex_op)
            integrater.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup))
            
            hklin = integrater.get_integrater_reflections()
            hklout = os.path.join(
                self.get_working_directory(),
                '%s_ref_srt.mtz' % os.path.split(hklin)[-1][:-4])
            
            # we will want to delete this one exit
            FileHandler.record_temporary_file(hklout)

            s = self.Sortmtz()
            s.set_hklout(hklout)
            s.add_hklin(hklin)
            s.sort()
        
            # now quickly merge the reflections
            
            hklin = hklout
            self._reference = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('_ref_srt.mtz', '_ref.mtz'))
            
            # need to remember this hklout - it will be the reference
            # reflection file for all of the reindexing below...

            Chatter.write('Quickly scaling reference data set: %s' % \
                          os.path.split(hklin)[-1])
            Chatter.write('to give indexing standard')

            qsc = self.Scala()
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
            
            pl = self.Pointless()
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

            # check this against the records in the indexer

            integrater = self._sweep_information[epoch]['integrater']
            indexer = integrater.get_integrater_indexer()

            # flag to record whether I need to do some rerunning
            rerun_pointless = False
            
            if indexer:
                possible = pl.get_possible_lattices()
                
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

                        # pointless wants something where no indexing
                        # solution exists...
                        Chatter.write(
                            'Rejected lattice %s' % lattice)
                        
                        # this means that I will need to rerun pointless
                        # with a lower symmetry target...

                        rerun_pointless = True
                        
                        continue
                    
                    elif state == 'possible':
                        # then this is a possible indexing solution
                        # but is not the highest symmetry - need to
                        # return...
                        
                        Chatter.write(
                            'Accepted lattice %s ...' % lattice)
                        Chatter.write(
                            '... will reprocess accordingly')

                        need_to_return = True
                        correct_lattice = lattice

                        break
                    
            if rerun_pointless:
                pl.set_correct_lattice(correct_lattice)
                pl.decide_pointgroup()

            Chatter.write('Pointless analysis of %s' % pl.get_hklin())

            # get the correct pointgroup etc.
            pointgroup = pl.get_pointgroup()
            reindex_op = pl.get_reindex_operator()

            if not overall_pointgroup:
                overall_pointgroup = pointgroup
            if overall_pointgroup != pointgroup:
                raise RuntimeError, 'non uniform pointgroups'
            
            Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

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
        # reference file... messy but perhaps effective?

        if len(self._sweep_information.keys()) > 1:
            
            # ---------- REINDEX TO CORRECT (REFERENCE) SETTING ----------
            
            for epoch in self._sweep_information.keys():
                pl = self.Pointless()
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

                Chatter.write('Pointless analysis of %s' % pl.get_hklin())
                
                # FIXED here - do I need to contemplate reindexing
                # the reflections? if not, don't bother - could be an
                # expensive waste of time for large reflection files
                # (think Ed Mitchell data...) - delegated to the Integrater
                # to manage...
                
                # get the correct pointgroup etc
                pointgroup = pl.get_pointgroup()
                reindex_op = pl.get_reindex_operator()
                
                Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

                # apply this...

                integrater = self._sweep_information[epoch]['integrater']
                
                integrater.set_integrater_reindex_operator(reindex_op)
                integrater.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))
                
        # ---------- SORT TOGETHER DATA ----------
            
        max_batches = 0
        
        for epoch in self._sweep_information.keys():

            # keep a count of the maximum number of batches in a block -
            # this will be used to make rebatch work below.

            hklin = self._sweep_information[epoch][
                'integrater'].get_integrater_reflections()

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

        # then sort the files together, making sure that the resulting
        # reflection file looks right.

        s = self.Sortmtz()

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

        # note here I am not abbreviating the reflection file as I
        # don't know whether this is a great idea...?  30/NOV/06

        # if it's a huge SAD data set then do it! else don't...

        p = self.Pointless()
        if len(self._sweep_information.keys()) > 1:
            p.set_hklin(hklin)
        else:
            # permit the use of pointless preparation...
            epoch = self._sweep_information.keys()[0]
            p.set_hklin(_prepare_pointless_hklin(
                self.get_working_directory(),
                hklin, self._sweep_information[epoch]['header'].get(
                'phi_width', 0.0)))

        p.decide_spacegroup()
        spacegroup = p.get_spacegroup()
        reindex_operator = p.get_spacegroup_reindex_operator()
        
        # Write this spacegroup information back to the storage areas
        # in the Scaler interface to allow them to be obtained by the
        # calling entity. Note well that I also want to write in
        # here the spacegroup enantiomorphs.

        # FIXED 21/NOV/06 need now to get this from the pointless output...

        self._scalr_likely_spacegroups = p.get_likely_spacegroups()

        # these are generated by the get_likely_spacegroups so we don't need
        # to be worrying about this - 

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

        Chatter.write('Reindexing to correct spacegroup setting: %s (%s)' % \
                      (spacegroup, reindex_operator))

        # then run reindex to set the correct spacegroup
        
        ri = self.Reindex()
        ri.set_hklin(hklin)
        ri.set_hklout(hklout)
        ri.set_spacegroup(spacegroup)
        ri.set_operator(reindex_operator)
        ri.reindex()
        
        # we will want to delete this one exit
        FileHandler.record_temporary_file(hklout)
        
        # then resort the reflections (one last time!)

        s = self.Sortmtz()

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

        # bug # 2326
        if self.get_scaler_anomalous():
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

        # FIXME need an option somewhere to configure this...
        
        if False:
            return (0.0, 0.0, 0.0, 0.0)

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

            Chatter.write('Tested SdAdd %4.2f: %4.2f %4.2f' % \
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

            Chatter.write('Tested SdAdd %4.2f: %4.2f %4.2f' % \
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

        sc = self.Scala()
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
        
        # bug # 2326
        if self.get_scaler_anomalous():
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

        # next compute resolution limits for each dataset.

        resolution_limits = { }

        # FIXME 10/NOV/06 after talking to Steve Prince I suspect I should
        # not be "massaging" the resolution information... remove this!

        massage_resolution = False

        highest_resolution = 100.0

        # check in here that there is actually some data to scale..!

        if len(resolution_info.keys()) == 0:
            raise RuntimeError, 'no resolution info'

        for dataset in resolution_info.keys():
            # transform this to a useful form... [(resol, i/sigma), (resol..)]
            resolution_points = []
            resol_ranges = resolution_info[dataset]['3_Dmin(A)']
            mn_i_sigma_values = resolution_info[dataset]['13_Mn(I/sd)']
            for i in range(len(resol_ranges)):
                dmin = float(resol_ranges[i])
                i_sigma = float(mn_i_sigma_values[i])
                resolution_points.append((dmin, i_sigma))

            resolution = _resolution_estimate(
                resolution_points, 2.0)

            # next compute "useful" versions of these resolution limits
            # want 0.05A steps - in here it would also be useful to
            # gather up an "average" best resolution and perhaps use this
            # where it seems appropriate e.g. TS03 INFL, LREM.

            if massage_resolution:
                resolution = 0.05 * nint(20.0 * resolution)
                
            resolution_limits[dataset] = resolution

            if resolution < highest_resolution:
                highest_resolution = resolution

            if resolution - highest_resolution < 0.051 and massage_resolution:
                # why not use this, to be tidy?
                resolution_limits[dataset] = highest_resolution

            Chatter.write('Resolution limit for %s: %5.2f' % \
                          (dataset, resolution_limits[dataset]))

        self._scalr_highest_resolution = highest_resolution

        Chatter.write('Scaler highest resolution set to %5.2f' % \
                      self.get_scaler_highest_resolution())

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
            Chatter.write('Quick, so not optimising error parameters')
            sdadd_full = 0.02
            sdb_full = 0.0
            sdadd_partial = 0.02
            sdb_partial = 0.0

        elif average_completeness < 50.0:
            Chatter.write('Incomplete data, so not refining error parameters')
            sdadd_full = 0.02
            sdb_full = 0.0
            sdadd_partial = 0.02
            sdb_partial = 0.0

        else:

            # ---------- SD CORRECTION PARAMETER LOOP ----------
            
            # first "fix" the sd add parameters to match up the sd curve from
            # the fulls and partials, and minimise RMS[N (scatter / sigma - 1)]
            
            Chatter.write('Optimising error parameters')
            
            sdadd_full, sdb_full, sdadd_partial, sdb_partial = \
                        self._refine_sd_parameters(scales_file)

            # remove the old scales file
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
        
        sc = self.Scala()

        FileHandler.record_log_file('%s %s scala' % (self._common_pname,
                                                     self._common_xname),
                                    sc.get_log_file())

        sc.set_resolution(best_resolution)

        sc.set_hklin(self._prepared_reflections)

        # scales_file = os.path.join(self.get_working_directory(),
        # '%s_final.scales' % self._common_xname)

        scales_file = '%s_final.scales' % self._common_xname

        sc.set_new_scales_file(scales_file)

        sc.add_sd_correction('full', 1.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 1.0, sdadd_partial, sdb_partial)

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
        sc.set_tails()

        sc.scale()

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

        # FIXED this is not correct for multi-wavelength data...
        # it should be now!

        scaled_reflection_files = sc.get_scaled_reflection_files()
        self._scalr_scaled_reflection_files = { }
        
        # compute a "standard unit cell" - FIXME perhaps - looks like
        # sortmtz will already assign somehow a standard unit cell -
        # interesting!

        # convert reflection files to .sca format - use mtz2various for this

        self._scalr_scaled_reflection_files['sca'] = { }

        # this is confusing as it implicitly iterates over the keys of the
        # dictionary
        
        for key in scaled_reflection_files:
            file = scaled_reflection_files[key]
            m2v = self.Mtz2various()
            m2v.set_hklin(file)
            m2v.set_hklout('%s.sca' % file[:-4])
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][
                key] = '%s.sca' % file[:-4]

        # FIXED BUG 2146

        # in here rerun scala recycling the final scales and writing out
        # unmerged reflection files in scalepack format

        sc = self.Scala()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        sc.add_sd_correction('full', 1.0, sdadd_full, sdb_full)
        sc.add_sd_correction('partial', 1.0, sdadd_partial, sdb_partial)
        
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
            
        sc.set_hklout(os.path.join(self.get_working_directory(), 'temp.mtz'))
        sc.set_scalepack(os.path.join(self.get_working_directory(),
                                      '%s_%s_unmerged.sca' % \
                                      (self._common_pname,
                                       self._common_xname)))

        # bug # 2326
        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.set_tails()
        sc.scale()

        # this will delete the mtz files which have been made 
        # and record the unmerged scalepack files in the file dictionary
        # BUG FIXME this is only right for MAD data... but that should now
        # be fixed...

        self._scalr_scaled_reflection_files['sca_unmerged'] = { }
        for key in scaled_reflection_files:
            file = scaled_reflection_files[key]
            scalepack = os.path.join(os.path.split(file)[0],
                                     os.path.split(file)[1].replace(
                '_scaled', '_unmerged').replace('.mtz', '.sca'))
            self._scalr_scaled_reflection_files['sca_unmerged'][
                key] = scalepack
            FileHandler.record_data_file(scalepack)

        # finally repeat the merging again (!) but keeping the
        # wavelengths separate to generate the statistics on a
        # per-wavelength basis - note that we do not want the
        # reflection files here... bug# 2229

        for key in self._scalr_statistics:
            pname, xname, dname = key

            sc = self.Scala()
            sc.set_hklin(self._prepared_reflections)
            sc.set_scales_file(scales_file)

            sc.add_sd_correction('full', 1.0, sdadd_full, sdb_full)
            sc.add_sd_correction('partial', 1.0, sdadd_partial, sdb_partial)
        
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
                
            sc.set_tails()
            sc.scale()
            stats = sc.get_summary()

            # this should just work ... by magic!
            self._scalr_statistics[key] = stats[key]

        # end bug # 2229 stuff

        # convert I's to F's in Truncate

        # 01MAR07 no longer have this...
        # self._scalr_scaled_reflection_files['mtz'] = { }
        for key in scaled_reflection_files.keys():
            file = scaled_reflection_files[key]
            t = self.Truncate()
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
            scaled_reflection_files[key] = hklout

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

                    # FIXED 08/DEC/06 cell axis differences now in 1% range,
                    # keep angles as 0.5 degrees

                    if _fraction_difference(
                        cell[0],
                        average_cell_a / average_cell_nref) > 0.01:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d
                    if _fraction_difference(
                        cell[1],
                        average_cell_b / average_cell_nref) > 0.01:
                        raise RuntimeError, \
                              'incompatible unit cell for set %s' % d
                    if _fraction_difference(
                        cell[2],
                        average_cell_c / average_cell_nref) > 0.01:
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

        self._scalr_cell = average_unit_cell

        for key in scaled_reflection_files.keys():
            file = scaled_reflection_files[key]
            
            hklout = '%s_cad.mtz' % file[:-4]
            FileHandler.record_temporary_file(hklout)

            c = self.Cad()
            c.add_hklin(file)
            c.set_new_suffix(key)
            c.set_new_cell(average_unit_cell)
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

            # however this doesn't allow for the renaming below in the free
            # flag adding step! Doh!
            
            self._scalr_scaled_reflection_files[
                'mtz_merged'] = scaled_reflection_files[
                scaled_reflection_files.keys()[0]]

        # finally add a FreeR column, and record the new merged reflection
        # file with the free column added.

        f = self.Freerflag()

        # changed this to not assume that the file is called _merged.mtz
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_free.mtz' % (self._common_pname,
                                                  self._common_xname))

        f.set_hklin(self._scalr_scaled_reflection_files['mtz_merged'])
        f.set_hklout(hklout)
        
        f.add_free_flag()

        # remove 'mtz_merged' from the dictionary - this is made
        # redundant by the merged free...
        del self._scalr_scaled_reflection_files['mtz_merged']

        # changed from mtz_merged_free to plain ol' mtz
        self._scalr_scaled_reflection_files['mtz'] = f.get_hklout()

        # record this for future reference
        FileHandler.record_data_file(f.get_hklout())

        # have a look for twinning ...
        sfc = self.Sfcheck()
        sfc.set_hklin(f.get_hklout())
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

        if len(scaled_reflection_files.keys()) > 1:
            crd = CCP4InterRadiationDamageDetector()

            crd.set_working_directory(self.get_working_directory())

            crd.set_hklin(f.get_hklout())
            
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

    
