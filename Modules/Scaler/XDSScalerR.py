#!/usr/bin/env python
# XDSScalerR.py
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

import os
import sys
import shutil
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the interface definition that this will conform to
# from Schema.Interfaces.Scaler import Scaler
from CommonScaler import CommonScaler as Scaler

# other tools that this will need
from Modules.Scaler.XDSScalerHelpers import XDSScalerHelper

# program wrappers that we will need

from Wrappers.XDS.XScaleR import XScaleR as _XScale
from Wrappers.XDS.Cellparm import Cellparm as _Cellparm
from Modules.TTT import ttt

from Wrappers.CCP4.CCP4Factory import CCP4Factory

# random odds and sods - the resolution estimate should be somewhere better
from lib.bits import auto_logfiler, transpose_loggraph, is_mtz_file
from lib.SymmetryLib import lattices_in_order
from Handlers.Citations import Citations
from Handlers.Syminfo import Syminfo
from Handlers.Streams import Chatter, Debug, Journal
from Handlers.Flags import Flags
from Handlers.Files import FileHandler

# stuff I have nicked from the CCP4 Scaler implementation
from Modules.DoseAccumulate import accumulate

# new resolution limit code
from Wrappers.XIA.Merger import Merger

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

        self._reference = None

        # spacegroup and unit cell information - these will be
        # derived from an average of all of the sweeps which are
        # passed in

        self._spacegroup = None
        self._factory = CCP4Factory()

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

        rerun_pointless = False

        possible = pointless.get_possible_lattices()

        correct_lattice = None

        Debug.write('Possible lattices (pointless):')
        Debug.write(' '.join(possible))

        for lattice in possible:
            state = indexer.set_indexer_asserted_lattice(lattice)
            if state == indexer.LATTICE_CORRECT:

                Debug.write(
                    'Agreed lattice %s' % lattice)
                correct_lattice = lattice

                break

            elif state == indexer.LATTICE_IMPOSSIBLE:
                Debug.write(
                    'Rejected lattice %s' % lattice)

                rerun_pointless = True

                continue

            elif state == indexer.LATTICE_POSSIBLE:
                Debug.write(
                    'Accepted lattice %s ...' % lattice)
                Debug.write(
                    '... will reprocess accordingly')

                need_to_return = True

                correct_lattice = lattice

                break

        if correct_lattice == None:
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
            sname = intgr.get_integrater_sweep_name()
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
                'sname':sname
                }

            Journal.entry({'adding data from':'%s/%s/%s' % \
                           (xname, dname, sname)})

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
            # 'integrater'].get_integrater_intensities()
            pass

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
                hklin = intgr.get_integrater_intensities()
                indxr = intgr.get_integrater_indexer()

                if self._scalr_input_pointgroup:
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = 'h,k,l'
                    ntr = False

                else:

                    pointgroup, reindex_op, ntr = \
                                self._pointless_indexer_jiffy(hklin, indxr)

                    Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

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
                    if state == indexer.LATTICE_CORRECT:
                        Debug.write('Lattice %s ok for sweep %s' % \
                                    (correct_lattice, sname))
                    elif state == indexer.LATTICE_IMPOSSIBLE:
                        raise RuntimeError, 'Lattice %s impossible for %s' % \
                              (correct_lattice, sname)
                    elif state == indexer.LATTICE_POSSIBLE:
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

            hklin = intgr.get_integrater_intensities()
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

                Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

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

            hklin = intgr.get_integrater_intensities()

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
                hklin = intgr.get_integrater_intensities()
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

                hklin = intgr.get_integrater_intensities()
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
                hklin = intgr.get_integrater_intensities()
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
            pointless.set_xdsin(intgr.get_integrater_intensities())
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

            hklin = intgr.get_integrater_intensities()
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
            sname = self._sweep_information[epoch]['sname']

            # and the resolution range for the reflections
            intgr = self._sweep_information[epoch]['integrater']
            Debug.write('Epoch: %d' % epoch)
            Debug.write('HKL: %s (%s/%s)' % (reflections, dname, sname))

            resolution_low = intgr.get_integrater_low_resolution()
            resolution_high = self._resolution_limits.get((dname, sname), 0.0)

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

        output_files = xscale.get_output_reflection_files()
        wavelength_names = output_files.keys()

        # these are per wavelength - also allow for user defined resolution
        # limits a la bug # 3183. No longer...

        for epoch in self._sweep_information.keys():

            input = self._sweep_information[epoch]

            intgr = input['integrater']

            if intgr.get_integrater_user_resolution():
                dmin = intgr.get_integrater_high_resolution()
                rkey = input['dname'], input['sname']

                if not self._user_resolution_limits.has_key(rkey):
                    self._resolution_limits[rkey] = dmin
                    self._user_resolution_limits[rkey] = dmin
                elif dmin < self._user_resolution_limits[rkey]:
                    self._resolution_limits[rkey] = dmin
                    self._user_resolution_limits[rkey] = dmin

        self._tmp_scaled_refl_files = { }

        self._scalr_statistics = { }

        max_batches = 0
        mtz_dict = { }

        project_info = { }
        for epoch in self._sweep_information.keys():
            pname = self._scalr_pname
            xname = self._scalr_xname
            dname = self._sweep_information[epoch]['dname']
            reflections = os.path.split(
                self._sweep_information[epoch]['prepared_reflections'])[-1]
            project_info[reflections] = (pname, xname, dname)

        for epoch in self._sweep_information.keys():
            self._sweep_information[epoch]['scaled_reflections'] = None

        for wavelength in wavelength_names:
            hklin = output_files[wavelength]

            xsh = XDSScalerHelper()
            xsh.set_working_directory(self.get_working_directory())

            ref = xsh.split_and_convert_xscale_output(
                hklin, 'SCALED_', project_info, 1.0 / scale_factor)

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

            del(xsh)

        for epoch in self._sweep_information.keys():
            hklin = self._sweep_information[epoch]['scaled_reflections']
            dname = self._sweep_information[epoch]['dname']
            sname = self._sweep_information[epoch]['sname']

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

            hkl_copy = os.path.join(self.get_working_directory(),
                                    'R_%s' % os.path.split(hklin)[-1])

            if not os.path.exists(hkl_copy):
                shutil.copyfile(hklin, hkl_copy)

            # let's properly listen to the user's resolution limit needs...

            if self._user_resolution_limits.get((dname, sname), False):
                resolution = self._user_resolution_limits[(dname, sname)]

            else:
                m = Merger()
                m.set_hklin(hklin)
                if Flags.get_rmerge():
                    m.set_limit_rmerge(Flags.get_rmerge())
                if Flags.get_completeness():
                    m.set_limit_completeness(Flags.get_completeness())
                if Flags.get_isigma():
                    m.set_limit_isigma(Flags.get_isigma())
                if Flags.get_misigma():
                    m.set_limit_misigma(Flags.get_misigma())
                if Flags.get_small_molecule():
                    m.set_nbins(20)

                m.run()

                if Flags.get_completeness():
                    r_comp = m.get_resolution_completeness()
                else:
                    r_comp = 0.0

                if Flags.get_rmerge():
                    r_rm = m.get_resolution_rmerge()
                else:
                    r_rm = 0.0

                if Flags.get_isigma():
                    r_uis = m.get_resolution_isigma()
                else:
                    r_uis = 0.0

                if Flags.get_misigma():
                    r_mis = m.get_resolution_misigma()
                else:
                    r_mis = 0.0

                resolution = max([r_comp, r_rm, r_uis, r_mis])

            Chatter.write('Resolution for sweep %s/%s: %.2f' % \
                          (dname, sname, resolution))

            if not (dname, sname) in self._resolution_limits:
                self._resolution_limits[(dname, sname)] = resolution
                self.set_scaler_done(False)
            else:
                if resolution < self._resolution_limits[(dname, sname)]:
                    self._resolution_limits[(dname, sname)] = resolution
                    self.set_scaler_done(False)

        if not self.get_scaler_done():
            Debug.write('Returning as scaling not finished...')
            return

        self._sort_together_data_xds()

        doses = { }

        for epoch in self._sweep_information.keys():
            i2d = self._sweep_information[epoch]['image_to_dose']
            i2e = self._sweep_information[epoch]['image_to_epoch']
            offset = self._sweep_information[epoch]['batch_offset']
            images = sorted(i2d.keys())
            for i in images:
                batch = i + offset
                doses[batch] = i2d[i]

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

            for wave in bits:
                s = self._factory.Sortmtz()
                s.set_hklout(bits[wave][0])
                for hklin in bits[wave][1:]:
                    s.add_hklin(hklin)
                s.sort()

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

        highest_resolution = min(
            [self._resolution_limits[k] for k in self._resolution_limits])

        self._scalr_highest_resolution = highest_resolution

        Debug.write('Scaler highest resolution set to %5.2f' % \
                    highest_resolution)

        if not self.get_scaler_done():
            Debug.write('Returning as scaling not finished...')
            return

        sdadd_full = 0.0
        sdb_full = 0.0

        # ---------- FINAL MERGING ----------

        scales_file = '%s_final.scales' % self._scalr_xname

        sc = self._factory.Scala()

        FileHandler.record_log_file('%s %s scala' % (self._scalr_pname,
                                                     self._scalr_xname),
                                    sc.get_log_file())

        sc.set_resolution(highest_resolution)
        sc.set_hklin(self._prepared_reflections)
        sc.set_new_scales_file(scales_file)

        if sdadd_full == 0.0 and sdb_full == 0.0:
            pass
        else:
            sc.add_sd_correction('both', 1.0, sdadd_full, sdb_full)

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            rkey = input['dname'], input['sname']
            run_resolution_limit = self._resolution_limits[rkey]

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit,
                       name = input['sname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._scalr_pname, self._scalr_xname)))

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.multi_merge()

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

        self._tmp_scaled_refl_files = copy.deepcopy(
            sc.get_scaled_reflection_files())

        self._scalr_scaled_reflection_files = { }

        # convert reflection files to .sca format - use mtz2various for this
        # also SHELX format if small molecule...

        self._scalr_scaled_reflection_files['sca'] = { }
        self._scalr_scaled_reflection_files['hkl'] = { }

        for key in self._tmp_scaled_refl_files:
            file = self._tmp_scaled_refl_files[key]
            scaout = '%s.sca' % file[:-4]

            m2v = self._factory.Mtz2various()
            m2v.set_hklin(file)
            m2v.set_hklout(scaout)
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][key] = scaout
            FileHandler.record_data_file(scaout)

            if Flags.get_small_molecule():
                hklout = '%s.hkl' % file[:-4]

                m2v = self._factory.Mtz2various()
                m2v.set_hklin(file)
                m2v.set_hklout(hklout)
                m2v.convert_shelx()

                self._scalr_scaled_reflection_files['hkl'][key] = hklout
                FileHandler.record_data_file(hklout)

        for key in self._scalr_statistics:
            pname, xname, dname = key

            sc = self._factory.Scala()
            sc.set_hklin(self._prepared_reflections)
            sc.set_scales_file(scales_file)
            sc.add_sd_correction('both', 1.0, sdadd_full, sdb_full)

            for epoch in epochs:
                input = self._sweep_information[epoch]
                rkey = input['dname'], input['sname']
                start, end = (min(input['batches']), max(input['batches']))

                if dname == input['dname']:
                    sc.add_run(start, end, pname = input['pname'],
                               xname = input['xname'],
                               dname = input['dname'],
                               exclude = False,
                               resolution = self._resolution_limits[rkey])
                else:
                    sc.add_run(start, end, pname = input['pname'],
                               xname = input['xname'],
                               dname = input['dname'],
                               exclude = True)

            sc.set_hklout(os.path.join(self.get_working_directory(),
                                       'temp.mtz'))

            if self.get_scaler_anomalous():
                sc.set_anomalous()

            sc.multi_merge()
            stats = sc.get_summary()

            self._scalr_statistics[key] = stats[key]

        # also output the unmerged scalepack format files...

        sc = self._factory.Scala()
        sc.set_resolution(highest_resolution)
        sc.set_hklin(self._prepared_reflections)
        sc.set_scalepack(os.path.join(self.get_working_directory(),
                                      '%s_%s_unmerged.sca' % \
                                      (self._scalr_pname,
                                       self._scalr_xname)))

        # this is now handled more elegantly by the Scala wrapper

        if sdadd_full == 0.0 and sdb_full == 0.0:
            pass
        else:
            sc.add_sd_correction('both', 1.0, sdadd_full, sdb_full)

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input['batches']), max(input['batches']))

            rkey = input['dname'], input['sname']
            run_resolution_limit = self._resolution_limits[rkey]

            sc.add_run(start, end, pname = input['pname'],
                       xname = input['xname'],
                       dname = input['dname'],
                       exclude = False,
                       resolution = run_resolution_limit,
                       name = input['sname'])

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_temp.mtz' % \
                                   (self._scalr_pname, self._scalr_xname)))

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.multi_merge()

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

