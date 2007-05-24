#!/usr/bin/env python
# XDSScaler.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# 2nd January 2007
#
# This will provide the Scaler interface using just XDS - a hybrid including
# pointless &c. will be developed at a later stage.
#
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
from Wrappers.CCP4.Cad import Cad as _Cad
from Wrappers.CCP4.Freerflag import Freerflag as _Freerflag
from Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz
from Wrappers.CCP4.Pointless import Pointless as _Pointless

# random odds and sods - the resolution estimate should be somewhere better
from lib.Guff import auto_logfiler, transpose_loggraph
from Handlers.Citations import Citations
from Handlers.Syminfo import Syminfo
from Handlers.Streams import Chatter, Debug
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

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
        self._cell = None

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
        self._common_dname = self._sweep_information[epochs[0]]['dname']
        
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

        # next if there is more than one sweep then generate
        # a merged reference reflection file to check that the
        # setting for all reflection files is the same...

        if len(self._sweep_information.keys()) > 1:
            # need to generate a reference reflection file

            raise RuntimeError, 'can\'t do multi sweep yet!'

            # convert the XDS_ASCII for this sweep to mtz
            
            # run it through pointless interacting with the
            # Indexer which belongs to this sweep

            # record this spacegroup for future reference...
            # self._spacegroup = Syminfo.spacegroup_name_to_number(pointgroup)

            # quickly scale it to a standard reference setting

            # next for all integraters reindex to the correct
            # pointgroup - again interacting with the indexer

            # now for all reflection files calculate the reindexing
            # operation needed to reset to the correct setting

            # regather all of the reflection files which we have prepared
            # and copy them to the working directory for scaling
            pass
        else:
            # convert the XDS_ASCII for this sweep to mtz

            epoch = self._first_epoch
            intgr = self._sweep_information[epoch]['integrater']
            sname = intgr.get_integrater_sweep_name()

            hklout = os.path.join(self.get_working_directory(),
                                  '%s-combat.mtz' % sname)

            combat = self.Combat()
            combat.set_hklin(intgr.get_integrater_reflections())
            combat.set_hklout(hklout)
            combat.run()

            # run it through pointless interacting with the
            # Indexer which belongs to this sweep

            hklin = hklout 

            pointless = self.Pointless()
            pointless.set_hklin(hklin)
            pointless.decide_pointgroup()

            indxr = intgr.get_integrater_indexer()

            if indxr:
                rerun_pointless = False

                possible = pointless.get_possible_lattices()

                correct_lattice = None

                Chatter.write('Possible lattices (pointless):')
                lattices = ''
                for lattice in possible:
                    lattices += '%s ' % lattice
                Chatter.write(lattices)

                for lattice in possible:
                    state = indxr.set_indexer_asserted_lattice(lattice)
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
            self._spacegroup = Syminfo.spacegroup_name_to_number(pointgroup)
            
            Chatter.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))
            
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

        # finally work through all of the reflection files we have
        # been given and compute the correct spacegroup and an
        # average unit cell... using CELLPARM

        cellparm = self.Cellparm()

        for epoch in self._sweep_information.keys():
            integrater = self._sweep_information[epoch]['integrater']
            cell = integrater.get_integrater_cell()
            n_ref = integrater.get_integrater_n_ref()
            cellparm.add_cell(cell, n_ref)

        self._cell = cellparm.get_cell()

        return

    def _scale(self):
        '''Actually scale all of the data together.'''

        epochs = self._sweep_information.keys()

        xscale = self.XScale()

        for epoch in epochs:

            # get the prepared reflections
            reflections = self._sweep_information[epoch][
                'prepared_reflections']
            
            # and the get wavelength that this belongs to
            dname = self._sweep_information[epoch]['dname']

            # and the resolution range for the reflections
            intgr = self._sweep_information[epoch]['integrater']
            resolution = intgr.get_integrater_resolution()
        
            xscale.add_reflection_file(reflections, dname, resolution)

        # set the global properties of the sample
        xscale.set_crystal(self._scalr_xname)
        xscale.set_anomalous(self._scalr_anomalous)

        # FIXME have to make sure that this is recorded
        # as a number...
        xscale.set_spacegroup_number(self._spacegroup)
        xscale.set_cell(self._cell)

        # do the scaling keeping the reflections unmerged

        xscale.run()

        # now get the reflection files out and merge them with scala

        output_files = xscale.get_output_reflection_files()
        wavelength_names = output_files.keys()

        # these are per wavelength
        resolution_limits = { } 
        scaled_reflection_files = { }

        self._scalr_statistics = { }
        
        for wavelength in wavelength_names:
            # convert the reflections to MTZ format with combat
            # - setting the pname, xname, dname
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_combat.mtz' % wavelength)

            combat = self.Combat()
            combat.set_hklin(output_files[wavelength])
            combat.set_hklout(hklout)
            combat.set_project_info(self._scalr_pname, self._scalr_xname,
                                    wavelength)
            combat.run()

            # then sort them

            hklin = hklout
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_sort.mtz' % wavelength)

            sortmtz = self.Sortmtz()
            sortmtz.add_hklin(hklin)
            sortmtz.set_hklout(hklout)
            sortmtz.sort()

            # then merge them in Scala - FIXME want also to convert them
            # to unmerged polish format...

            hklin = hklout
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_scaled.mtz' % wavelength)

            scala = self.Scala()
            scala.set_hklin(hklin)
            scala.set_hklout(hklout)
            scala.set_anomalous(self._scalr_anomalous)
            scala.set_onlymerge()
            scala.merge()

            scaled_reflection_files[
                wavelength] = hklout

            # get the resolution limits out -> statistics dictionary
            self._scalr_statistics[wavelength] = scala.get_summary()

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

        # if we need to redo the scaling, return to allow this to happen

        if not self.get_scaler_done():
            return
            
        # next transform to F's from I's

        for wavelength in scaled_reflection_files.keys():

            hklin = scaled_reflection_files[wavelength]
            
            truncate = self.Truncate()
            truncate.set_hklin(file)

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

            t.set_hklout(hklout)
            t.truncate()

            b_factor = t.get_b_factor()

            # record the b factor somewhere (hopefully) useful...

            self._scalr_statistics[
                (self._common_pname, self._common_xname, wavelength)
                ]['Wilson B factor'] = [b_factor]
            
            # and record the reflection file..
            scaled_reflection_files[wavelength] = hklout
            
        # and cad together into a single data set - recalling that we already
        # have a standard unit cell...

        if len(scaled_reflection_files.keys()) > 1:

            c = self.Cad()
            for wavelength in scaled_reflection_files.keys():
                c.add_hklin(scaled_reflection_files[wavelength])
        
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

