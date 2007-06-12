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

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to 
from Schema.Interfaces.Scaler import Scaler

# other tools that this will need
from Modules.XDSPointgroup import XDSPointgroup

# program wrappers that we will need

from Wrappers.XDS.XScale import XScale as _XScale
from Wrappers.XDS.Cellparm import Cellparm as _Cellparm

from Wrappers.CCP4.Scala import Scala as _Scala
from Wrappers.CCP4.Truncate import Truncate as _Truncate
from Wrappers.CCP4.Combat import Combat as _Combat
from Wrappers.CCP4.Reindex import Reindex as _Reindex
from Wrappers.CCP4.Rebatch import Rebatch as _Rebatch
from Wrappers.CCP4.Mtzdump import Mtzdump as _Mtzdump
from Wrappers.CCP4.Sfcheck import Sfcheck as _Sfcheck
from Wrappers.CCP4.Cad import Cad as _Cad
from Wrappers.CCP4.Freerflag import Freerflag as _Freerflag
from Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz
from Wrappers.CCP4.Pointless import Pointless as _Pointless

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

        # spacegroup and unit cell information - these will be
        # derived from an average of all of the sweeps which are
        # passed in
        
        self._spacegroup = None

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

    def Sortmtz(self):
        '''Create a Sortmtz wrapper from _Sortmtz - set the working directory
        and log file stuff as a part of this...'''
        sortmtz = _Sortmtz()
        sortmtz.set_working_directory(self.get_working_directory())
        auto_logfiler(sortmtz)
        return sortmtz

    def Pointless(self):
        '''Create a Pointless wrapper from _Pointless - and set the
        working directory and log file stuff as a part of this...'''
        pointless = _Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)
        return pointless

    def Combat(self):
        '''Create a Combat wrapper from _Combat - set the working directory
        and log file stuff as a part of this...'''
        combat = _Combat()
        combat.set_working_directory(self.get_working_directory())
        auto_logfiler(combat)
        return combat

    def Reindex(self):
        '''Create a Reindex wrapper from _Reindex - set the working directory
        and log file stuff as a part of this...'''
        reindex = _Reindex()
        reindex.set_working_directory(self.get_working_directory())
        auto_logfiler(reindex)
        return reindex

    def Rebatch(self):
        '''Create a Rebatch wrapper from _Rebatch - set the working directory
        and log file stuff as a part of this...'''
        rebatch = _Rebatch()
        rebatch.set_working_directory(self.get_working_directory())
        auto_logfiler(rebatch)
        return rebatch

    def Mtzdump(self):
        '''Create a Mtzdump wrapper from _Mtzdump - set the working directory
        and log file stuff as a part of this...'''
        mtzdump = _Mtzdump()
        mtzdump.set_working_directory(self.get_working_directory())
        auto_logfiler(mtzdump)
        return mtzdump

    def Sfcheck(self):
        '''Create a Sfcheck wrapper from _Sfcheck - set the working directory
        and log file stuff as a part of this...'''
        sfcheck = _Sfcheck()
        sfcheck.set_working_directory(self.get_working_directory())
        auto_logfiler(sfcheck)
        return sfcheck

    def Cad(self):
        '''Create a Cad wrapper from _Cad - set the working directory
        and log file stuff as a part of this...'''
        cad = _Cad()
        cad.set_working_directory(self.get_working_directory())
        auto_logfiler(cad)
        return cad

    def Freerflag(self):
        '''Create a Freerflag wrapper from _Freerflag - set the working
        directory and log file stuff as a part of this...'''
        freerflag = _Freerflag()
        freerflag.set_working_directory(self.get_working_directory())
        auto_logfiler(freerflag)
        return freerflag

    def Scala(self):
        '''Create a Scala wrapper from _Scala - set the working directory
        and log file stuff as a part of this...'''
        scala = _Scala()
        scala.set_working_directory(self.get_working_directory())
        auto_logfiler(scala)
        return scala

    def Truncate(self):
        '''Create a Truncate wrapper from _Truncate - set the working directory
        and log file stuff as a part of this...'''
        truncate = _Truncate()
        truncate.set_working_directory(self.get_working_directory())
        auto_logfiler(truncate)
        return truncate

    def _pointless_indexer_jiffy(self, hklin, indexer):
        '''A jiffy to centralise the interactions between pointless
        (in the blue corner) and the Indexer, in the red corner.'''

        # check to see if HKLIN is MTZ format, and if not, render it
        # so!

        need_to_return = False

        if not is_mtz_file(hklin):

            hklout = os.path.join(self.get_working_directory(),
                                  'temp-combat.mtz')

            FileHandler.record_temporary_file(hklout)
            
            combat = self.Combat()
            combat.set_hklin(hklin)
            combat.set_hklout(hklout)
            combat.run()

            hklin = hklout

        pointless = self.Pointless()
        pointless.set_hklin(hklin)
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

        for epoch in self._scalr_integraters.keys():
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()
            self._sweep_information[epoch] = {
                'pname':pname,
                'xname':xname,
                'dname':dname,
                'integrater':intgr,
                'prepared_reflections':None,
                'header':intgr.get_header(),
                }

            Debug.write('For EPOCH %s have:' % str(epoch))
            Debug.write('ID = %s/%s/%s' % (pname, xname, dname))
            Debug.write('SWEEP = %s' % intgr.get_integrater_sweep_name())

        # next work through all of the reflection files and make sure that
        # they are XDS_ASCII format...

        epochs = self._sweep_information.keys()

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
                        raise RuntimeError, 'Lattice %s impossible for %s' \
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

        if len(self._sweep_information.keys()) > 1:
            # need to generate a reference reflection file - generate this
            # from the reflections in self._first_epoch

            intgr = self._sweep_information[self._first_epoch]['integrater']

            hklin = intgr.get_integrater_reflections()
            indxr = intgr.get_integrater_indexer()
            
            pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                hklin, indxr)

            if ntr:
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

            combat = self.Combat()
            combat.set_hklin(hklin)
            combat.set_hklout(hklout)
            combat.run()

            hklin = hklout
            
            hklout = os.path.join(self.get_working_directory(),
                                  'xds-pointgroup-reference-sorted.mtz')
            FileHandler.record_temporary_file(hklout)

            sortmtz = self.Sortmtz()
            sortmtz.add_hklin(hklin)
            sortmtz.set_hklout(hklout)
            sortmtz.sort()

            hklin = hklout

            reference_mtz = os.path.join(self.get_working_directory(),
                                         'xds-pointgroup-reference.mtz')
            FileHandler.record_temporary_file(reference_mtz)            

            scala = self.Scala()            
            scala.set_hklin(hklin)
            scala.set_hklout(reference_mtz)
            scala.quick_scale()            

            for epoch in self._sweep_information.keys():

                intgr = self._sweep_information[epoch]['integrater']
                hklin = intgr.get_integrater_reflections()
                indxr = intgr.get_integrater_indexer()

                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, indxr)

                if ntr:
                    need_to_return = True
            
                intgr.set_integrater_reindex_operator(reindex_op)
                intgr.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))
                
                # convert the XDS_ASCII for this sweep to mtz - on the next
                # get this should be in the correct setting...

                hklin = intgr.get_integrater_reflections()
                hklout = os.path.join(self.get_working_directory(),
                                      'xds-pointgroup-unsorted.mtz')
                FileHandler.record_temporary_file(hklout)
                
                combat = self.Combat()
                combat.set_hklin(hklin)
                combat.set_hklout(hklout)
                combat.run()

                pointless = self.Pointless()
                pointless.set_hklin(hklout)
                pointless.set_hklref(reference_mtz)
                pointless.decide_pointgroup()

                pointgroup = pointless.get_pointgroup()
                reindex_op = pointless.get_reindex_operator()

                # this should send back enough information that this
                # is in the correct pointgroup (from the call above) and
                # also in the correct setting, from the interaction
                # with the reference set...
                
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

            combat = self.Combat()
            combat.set_hklin(intgr.get_integrater_reflections())
            combat.set_hklout(hklout)
            combat.run()

            # run it through pointless interacting with the
            # Indexer which belongs to this sweep

            hklin = hklout 

            pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                hklin, indxr)

            if ntr:
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

        return

    def _scale(self):
        '''Actually scale all of the data together.'''

        epochs = self._sweep_information.keys()

        xscale = self.XScale()

        xscale.set_spacegroup_number(self._spacegroup)
        xscale.set_cell(self._scalr_cell)

        Debug.write('Set CELL: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                    tuple(self._scalr_cell))
        Debug.write('Set SPACEGROUP_NUMBER: %d' % \
                    self._spacegroup)

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
        
            xscale.add_reflection_file(reflections, dname, resolution)

        # set the global properties of the sample
        xscale.set_crystal(self._scalr_xname)
        xscale.set_anomalous(self._scalr_anomalous)

        # do the scaling keeping the reflections unmerged

        xscale.run()

        # now get the reflection files out and merge them with scala

        output_files = xscale.get_output_reflection_files()
        wavelength_names = output_files.keys()

        # these are per wavelength
        resolution_limits = { } 
        self._scaled_ref_files = { }

        self._scalr_statistics = { }

        # FIXED in here I need to get the spacegroup and reindexing
        # operator to put the reflections in the standard setting from
        # all reflections merged together rather than from each
        # wavelength separately. I will therefore need to include the
        # rebatch-and-sort-together shuffle from CCP4 scaler
        # implementation.

        max_batches = 0
        mtz_dict = { } 
        
        for wavelength in wavelength_names:
            # convert the reflections to MTZ format with combat
            # - setting the pname, xname, dname
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_combat.mtz' % wavelength)
            FileHandler.record_temporary_file(hklout)

            combat = self.Combat()
            combat.set_hklin(output_files[wavelength])
            combat.set_hklout(hklout)
            combat.set_project_info(self._scalr_pname, self._scalr_xname,
                                    wavelength)
            combat.run()

            hklin = hklout
            mtz_dict[wavelength] = hklout

            md = self.Mtzdump()
            md.set_hklin(hklin)
            md.dump()

            Chatter.write('Getting batches from %s' % hklin)
            batches = md.get_batches()
            Chatter.write('=> %d to %d' % (min(batches),
                                           max(batches)))

            # FIXME here check that this matches up with the input,
            # if we have both sources of batch information
            if 1 + max(batches) - min(batches) > max_batches:
                max_batches = max(batches) - min(batches) + 1
            
        Chatter.write('Biggest sweep has %d batches' % max_batches)
        max_batches = nifty_power_of_ten(max_batches)
    
        counter = 0

        for wavelength in wavelength_names:
            hklin = mtz_dict[wavelength]
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_rebatch.mtz' % wavelength)
            rebatch = self.Rebatch()

            # we will want to delete this one exit
            FileHandler.record_temporary_file(hklout)
            rebatch.set_hklin(hklin)
            rebatch.set_first_batch(counter * max_batches + 1)
            rebatch.set_hklout(hklout)
            rebatch.rebatch()

            mtz_dict[wavelength] = hklout

            counter += 1

        # then sort the files together, making sure that the resulting
        # reflection file looks right. Only sorting here to put all
        # of the reflections in a single file...

        s = self.Sortmtz()

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted.mtz' % \
                              (self._common_pname, self._common_xname))
        
        s.set_hklout(hklout)

        FileHandler.record_temporary_file(hklout)

        for wavelength in wavelength_names:
            s.add_hklin(mtz_dict[wavelength])

        s.sort()

        pointless = self.Pointless()
        pointless.set_hklin(hklout)
        pointless.decide_spacegroup()

        # get one spacegroup and so on which will be used for
        # all of the reflection files...
        
        spacegroups = pointless.get_likely_spacegroups()
        reindex_operator = pointless.get_spacegroup_reindex_operator()

        # save these for later - we will reindex the merged
        # data after scaling

        self._scalr_likely_spacegroups = spacegroups
        self._scalr_reindex_operator = reindex_operator

        Debug.write('Reindex operator: %s' % reindex_operator)
        Debug.write('Will save this for later')

        for wavelength in wavelength_names:

            # convert the reflections to MTZ format with combat
            # - setting the pname, xname, dname

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_combat.mtz' % wavelength)
            FileHandler.record_temporary_file(hklout)

            combat = self.Combat()
            combat.set_hklin(output_files[wavelength])
            combat.set_hklout(hklout)
            combat.set_project_info(self._scalr_pname, self._scalr_xname,
                                    wavelength)
            combat.run()

            hklin = hklout
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_sort.mtz' % wavelength)
            FileHandler.record_temporary_file(hklout)

            sortmtz = self.Sortmtz()
            sortmtz.add_hklin(hklin)
            sortmtz.set_hklout(hklout)
            sortmtz.sort()

            # then merge them in Scala - FIXME want also to convert them
            # to unmerged polish format... though can't do this for
            # the moment as we can't reindex the unmerged reflections

            hklin = hklout
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_scaled.mtz' % wavelength)

            scala = self.Scala()
            scala.set_hklin(hklin)
            scala.set_hklout(hklout)
            scala.set_anomalous(self._scalr_anomalous)
            scala.set_onlymerge()
            scala.merge()

            FileHandler.record_log_file('%s %s %s merge' % \
                                        (self._common_pname,
                                         self._common_xname,
                                         wavelength),
                                        scala.get_log_file())

            self._scaled_ref_files[wavelength] = hklout

            # get the resolution limits out -> statistics dictionary

            stats_id = (self._scalr_pname, self._scalr_xname, wavelength)
            self._scalr_statistics[stats_id] = scala.get_summary()[stats_id]

            loggraph = scala.parse_ccp4_loggraph()
            
            for key in loggraph.keys():
                if 'Analysis against resolution' in key:
                    dataset = key.split(',')[-1].strip()
                    resolution_info = transpose_loggraph(loggraph[key])
                    resolution_points = []
                    resol_ranges = resolution_info['3_Dmin(A)']
                    mn_i_sigma_values = resolution_info['13_Mn(I/sd)']
                    for i in range(len(resol_ranges)):
                        dmin = float(resol_ranges[i])
                        i_sigma = float(mn_i_sigma_values[i])
                        resolution_points.append((dmin, i_sigma))

                    resolution = _resolution_estimate(
                        resolution_points, 2.0)
                    resolution_limits[wavelength] = resolution
            

        # for each integrater set the resolution limit where Mn(I/sigma) ~ 2
        # but only of the resolution limit is noticeably lower than the
        # integrated resolution limit (used 0.075A difference before)
        # and if this is the case, return as we want the integration to
        # be repeated, after resetting the "done" flags.

        # so...

        # next work though the epochs of integraters setting the resolution
        # limit by the value from the wavelength recorded above

        best_resolution = 100.0

        for epoch in self._sweep_information.keys():
            intgr = self._sweep_information[epoch]['integrater']
            dname = self._sweep_information[epoch]['dname']
            dmin = intgr.get_integrater_high_resolution()

            # compare this against the resolution limit computed above
            if dmin == 0.0 and not Flags.get_quick():
                intgr.set_integrater_high_resolution(
                    resolution_limits[dname])

                self.set_scaler_done(False)
                self.set_scaler_prepare_done(False)

            # note well that this spacing (0.075A) is designed to ensure that
            # integration shouldn't be repeated once it has been repeated
            # once...
            
            elif dmin > resolution_limits[dname] - 0.075:
                pass

            elif Flags.get_quick():
                # that is we would reprocess if we weren't in a hurry
                Chatter.write('Quick, so not resetting resolution limits')

            else:
                intgr.set_integrater_high_resolution(
                    resolution_limits[dname])

                self.set_scaler_done(False)
                self.set_scaler_prepare_done(False)

            if resolution_limits[dname] < best_resolution:
                best_resolution = resolution_limits[dname]

        self._scalr_highest_resolution = best_resolution
                   
        return

    def _scale_finish(self):
        
        # next transform to F's from I's

        for wavelength in self._scaled_ref_files.keys():

            hklin = self._scaled_ref_files[wavelength]

            # perhaps reindex first?
            if self._scalr_reindex_operator != 'h,k,l':

                hklout = os.path.join(self.get_working_directory(),
                                      '%s_reindexed.mtz' % wavelength)
                FileHandler.record_temporary_file(hklout)

                Debug.write('Reindexing operator = %s' % \
                            self._scalr_reindex_operator)
                
                reindex = self.Reindex()
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
            
            truncate = self.Truncate()
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
            self._scaled_ref_files[wavelength] = hklout
            
        # and cad together into a single data set - recalling that we already
        # have a standard unit cell... and remembering where the files go...

        self._scalr_scaled_reflection_files = { }

        if len(self._scaled_ref_files.keys()) > 1:

            # for each reflection file I need to (1) ensure that the
            # spacegroup is uniformly set and (2) ensure that
            # the column names are appropriately relabelled.

            reflection_files = { }

            for wavelength in self._scaled_ref_files.keys():
                cad = self.Cad()
                cad.add_hklin(self._scaled_ref_files[wavelength])
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

            cad = self.Cad()
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
                'mtz_merged'] = self._scaled_ref_files[
                self._scaled_ref_files.keys()[0]]

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

        if len(self._scaled_ref_files.keys()) > 1:
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

