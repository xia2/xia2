#!/usr/bin/env python
# CCP4ScalerA.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 07/OCT/2011
#
# An implementation of the Scaler interface using CCP4 programs and Aimless.
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
from lib.SymmetryLib import lattices_in_order, sort_lattices

from CCP4ScalerHelpers import _resolution_estimate, \
     _prepare_pointless_hklin, _fraction_difference, \
     CCP4ScalerHelper, SweepInformationHandler, erzatz_resolution, \
     anomalous_signals

from Modules.CCP4InterRadiationDamageDetector import \
     CCP4InterRadiationDamageDetector
from Modules.DoseAccumulate import accumulate

from Modules.AnalyseMyIntensities import AnalyseMyIntensities
from Experts.ResolutionExperts import determine_scaled_resolution
from Toolkit.Merger import merger

# newly implemented CCTBX powered functions to replace xia2 binaries
from Modules.Scaler.add_dose_time_to_mtz import add_dose_time_to_mtz

class CCP4ScalerA(Scaler):
    '''An implementation of the Scaler interface using CCP4 programs.'''

    def __init__(self):
        Scaler.__init__(self)

        self._sweep_handler = None

        self._tmp_scaled_refl_files = { }
        self._wavelengths_in_order = []

        self.__sweep_resolution_limits = { }

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

    def _updated_aimless(self):
        '''Generate a correctly configured Aimless...'''

        aimless = None

        if not self._scalr_corrections:
            aimless = self._factory.Aimless()
        else:

            aimless = self._factory.Aimless(
                partiality_correction = self._scalr_correct_partiality,
                absorption_correction = self._scalr_correct_absorption,
                decay_correction = self._scalr_correct_decay)

        if Flags.get_microcrystal():

            # fiddly little data sets - allow more rapid scaling...

            aimless.set_scaling_parameters('rotation', 2.0)
            if self._scalr_correct_decay:
                aimless.set_bfactor(bfactor = True, brotation = 2.0)

        return aimless

    def _pointless_indexer_jiffy(self, hklin, indexer):
        return self._helper.pointless_indexer_jiffy(hklin, indexer)

    def _assess_scaling_model(self, tails, bfactor, secondary):

        epochs = self._sweep_handler.get_epochs()

        sc_tst = self._updated_aimless()
        sc_tst.set_cycles(5)

        sc_tst.set_hklin(self._prepared_reflections)
        sc_tst.set_hklout('temp.mtz')

        sc_tst.set_tails(tails = tails)
        sc_tst.set_bfactor(bfactor = bfactor)

        resolutions = self._resolution_limit_estimates

        if secondary:
            sc_tst.set_scaling_parameters(
                'rotation', secondary = Flags.get_scala_secondary())
        else:
            sc_tst.set_scaling_parameters('rotation', secondary = 0)

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)

            start, end = si.get_batch_range()

            resolution = resolutions[(start, end)]

            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()

            sc_tst.add_run(start, end, exclude = False,
                           resolution = resolution, name = sname)

            if self.get_scaler_anomalous():
                sc_tst.set_anomalous()

        if True:
            # try:
            sc_tst.scale()
        else:
            # except RuntimeError, e:
            if 'scaling not converged' in str(e):
                return -1, -1
            if 'negative scales' in str(e):
                return -1, -1
            raise e

        data_tst = sc_tst.get_summary()

        # compute average Rmerge, number of cycles to converge - these are
        # what will form the basis of the comparison

        target = {'overall':0, 'low':1, 'high':2}

        rmerges_tst = [data_tst[k]['Rmerge'][target[
            Flags.get_rmerge_target()]] for k in data_tst]
        rmerge_tst = sum(rmerges_tst) / len(rmerges_tst)

        return rmerge_tst

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

        rmerge_def = self._assess_scaling_model(
            tails = False, bfactor = False, secondary = False)

        results = { }

        consider = []

        log_results = []

        for partiality in True, False:
            for decay in True, False:
                for absorption in True, False:
                    if partiality or decay or absorption:
                        r = self._assess_scaling_model(
                            tails = partiality, bfactor = decay,
                            secondary = absorption)
                    else:
                        r = rmerge_def

                    results[(partiality, decay, absorption)] = r

                    log_results.append((partiality, decay, absorption, r))

                    consider.append(
                        (r, partiality, decay, absorption))


        Debug.write('. Tails Decay  Abs  R(%s)' % \
                    Flags.get_rmerge_target())

        for result in log_results:
            Debug.write('. %5s %5s %5s %.3f' % result)

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

        self._sweep_handler = SweepInformationHandler(self._scalr_integraters)

        Journal.block(
            'gathering', self.get_scaler_xcrystal().get_name(), 'CCP4',
            {'working directory':self.get_working_directory()})

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()

            Journal.entry({'adding data from':'%s/%s/%s' % \
                           (xname, dname, sname)})

        # gather data for all images which belonged to the parent
        # crystal - allowing for the fact that things could go wrong
        # e.g. epoch information not available, exposure times not in
        # headers etc...

        for e in self._sweep_handler.get_epochs():
            assert(is_mtz_file(self._sweep_handler.get_sweep_information(
                e).get_reflections()))

        p, x = self._sweep_handler.get_project_info()
        self._scalr_pname = p
        self._scalr_xname = x

        # verify that the lattices are consistent, calling eliminate if
        # they are not N.B. there could be corner cases here

        need_to_return = False

        if len(self._sweep_handler.get_epochs()) > 1:

            lattices = []

            for epoch in self._sweep_handler.get_epochs():

                si = self._sweep_handler.get_sweep_information(epoch)
                intgr = si.get_integrater()
                hklin = intgr.get_integrater_intensities()
                indxr = intgr.get_integrater_indexer()

                if self._scalr_input_pointgroup:
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = 'h,k,l'
                    ntr = False

                else:
                    pointless_hklin = self._prepare_pointless_hklin(
                        hklin, si.get_header()['phi_width'])

                    pointgroup, reindex_op, ntr, pt = \
                                self._pointless_indexer_jiffy(
                        pointless_hklin, indxr)

                    Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

                lattice = Syminfo.get_lattice(pointgroup)

                if not lattice in lattices:
                    lattices.append(lattice)

                if ntr:

                    intgr.integrater_reset_reindex_operator()
                    need_to_return = True

            if len(lattices) > 1:

                # why not using pointless indexer jiffy??!

                correct_lattice = sort_lattices(lattices)[0]

                Chatter.write('Correct lattice asserted to be %s' % \
                              correct_lattice)

                # transfer this information back to the indexers
                for epoch in self._sweep_handler.get_epochs():

                    si = self._sweep_handler.get_sweep_information(epoch)
                    indxr = si.get_integrater().get_integrater_indexer()
                    sname = si.get_sweep_name()

                    state = indxr.set_indexer_asserted_lattice(
                        correct_lattice)

                    if state == indxr.LATTICE_CORRECT:
                        Chatter.write('Lattice %s ok for sweep %s' % \
                                      (correct_lattice, sname))
                    elif state == indxr.LATTICE_IMPOSSIBLE:
                        raise RuntimeError, 'Lattice %s impossible for %s' \
                              % (correct_lattice, sname)
                    elif state == indxr.LATTICE_POSSIBLE:
                        Chatter.write('Lattice %s assigned for sweep %s' % \
                                      (correct_lattice, sname))
                        need_to_return = True

        # if one or more of them was not in the lowest lattice,
        # need to return here to allow reprocessing

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------

        # all should share the same pointgroup, unless twinned... in which
        # case force them to be...

        pointgroups = { }
        reindex_ops = { }
        probably_twinned = False

        need_to_return = False

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)

            hklin = si.get_reflections()
            hklout = os.path.join(
                self.get_working_directory(),
                os.path.split(hklin)[-1].replace('.mtz', '_rdx.mtz'))

            FileHandler.record_temporary_file(hklout)

            integrater = si.get_integrater()
            indexer = integrater.get_integrater_indexer()

            if self._scalr_input_pointgroup:
                Debug.write('Using input pointgroup: %s' % \
                            self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup
                reindex_op = 'h,k,l'
                pt = False

            else:

                pointless_hklin = self._prepare_pointless_hklin(
                    hklin, si.get_header()['phi_width'])

                pointgroup, reindex_op, ntr, pt = \
                            self._pointless_indexer_jiffy(
                    pointless_hklin, indexer)

                Debug.write('X1698: %s: %s' % (pointgroup, reindex_op))

                if ntr:

                    integrater.integrater_reset_reindex_operator()
                    need_to_return = True

            if pt and not probably_twinned:
                probably_twinned = True

            Debug.write('Pointgroup: %s (%s)' % (pointgroup, reindex_op))

            pointgroups[epoch] = pointgroup
            reindex_ops[epoch] = reindex_op

        overall_pointgroup = None

        pointgroup_set = set([pointgroups[e] for e in pointgroups])

        if len(pointgroup_set) > 1 and \
           not probably_twinned:
            raise RuntimeError, 'non uniform pointgroups'

        if len(pointgroup_set) > 1:
            Debug.write('Probably twinned, pointgroups: %s' % \
                        ' '.join([p.replace(' ', '') for p in \
                                  list(pointgroup_set)]))
            numbers = [Syminfo.spacegroup_name_to_number(s) for s in \
                       pointgroup_set]
            overall_pointgroup = Syminfo.spacegroup_number_to_name(
                min(numbers))
            self._scalr_input_pointgroup = overall_pointgroup

            Chatter.write('Twinning detected, assume pointgroup %s' % \
                          overall_pointgroup)

            need_to_return = True

        else:
            overall_pointgroup = pointgroup_set.pop()

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)

            integrater = si.get_integrater()

            integrater.set_integrater_reindex_operator(
                reindex_ops[epoch])
            integrater.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(overall_pointgroup))

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        if self.get_scaler_reference_reflection_file():
            self._reference = self.get_scaler_reference_reflection_file()
            Chatter.write('Using HKLREF %s' % self._reference)

        elif Flags.get_reference_reflection_file():
            self._reference = Flags.get_reference_reflection_file()
            Chatter.write('Using HKLREF %s' % self._reference)

        if len(self._sweep_handler.get_epochs()) > 1 and \
               not self._reference:

            first = self._sweep_handler.get_epochs()[0]
            si = self._sweep_handler.get_sweep_information(first)
            integrater = si.get_integrater()
            self._reference = integrater.get_integrater_intensities()

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

            for epoch in self._sweep_handler.get_epochs():
                pl = self._factory.Pointless()

                si = self._sweep_handler.get_sweep_information(epoch)
                hklin = si.get_reflections()

                pl.set_hklin(self._prepare_pointless_hklin(
                    hklin, si.get_header()['phi_width']))

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

                integrater = si.get_integrater()

                integrater.set_integrater_reindex_operator(reindex_op)
                integrater.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup))

                md = self._factory.Mtzdump()
                md.set_hklin(integrater.get_integrater_intensities())
                md.dump()

                datasets = md.get_datasets()

                if len(datasets) > 1:
                    raise RuntimeError, 'more than one dataset in %s' % \
                          integrater.get_integrater_intensities()

                # then get the unit cell, lattice etc.

                lattice = Syminfo.get_lattice(md.get_spacegroup())
                cell = md.get_dataset_info(datasets[0])['cell']

                if lattice != reference_lattice:
                    raise RuntimeError, 'lattices differ in %s and %s' % \
                          (self._reference,
                           integrater.get_integrater_intensities())

                for j in range(6):
                    if math.fabs((cell[j] - reference_cell[j]) /
                                 reference_cell[j]) > 0.1:
                        raise RuntimeError, \
                              'unit cell parameters differ in %s and %s' % \
                              (self._reference,
                               integrater.get_integrater_intensities())

        # ---------- SORT TOGETHER DATA ----------

        max_batches = 0

        for epoch in self._sweep_handler.get_epochs():

            # keep a count of the maximum number of batches in a block -
            # this will be used to make rebatch work below.

            si = self._sweep_handler.get_sweep_information(epoch)
            hklin = si.get_reflections()

            md = self._factory.Mtzdump()
            md.set_hklin(hklin)
            md.dump()

            batches = si.get_batches()
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

        counter = 0

        for epoch in self._sweep_handler.get_epochs():

            si = self._sweep_handler.get_sweep_information(epoch)
            rb = self._factory.Rebatch()

            hklin = si.get_reflections()

            pname, xname, dname = si.get_project_info()

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_%s_%d.mtz' % \
                                  (pname, xname, dname, counter))

            FileHandler.record_temporary_file(hklout)

            first_batch = min(si.get_batches())
            si.set_batch_offset(counter * max_batches - first_batch + 1)

            rb.set_hklin(hklin)
            rb.set_first_batch(counter * max_batches + 1)
            rb.set_project_info(pname, xname, dname)
            rb.set_hklout(hklout)

            new_batches = rb.rebatch()

            # update the "input information"

            si.set_reflections(hklout)
            si.set_batches(new_batches)

            # update the counter & recycle

            counter += 1

        s = self._factory.Sortmtz()

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted.mtz' % \
                              (self._scalr_pname, self._scalr_xname))

        s.set_hklout(hklout)

        for epoch in self._sweep_handler.get_epochs():
            s.add_hklin(self._sweep_handler.get_sweep_information(
                epoch).get_reflections())

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

            if len(self._sweep_handler.get_epochs()) > 1:
                p.set_hklin(hklin)
            else:
                # permit the use of pointless preparation...
                epoch = self._sweep_handler.get_epochs()[0]
                p.set_hklin(self._prepare_pointless_hklin(
                    hklin, self._sweep_handler.get_sweep_information(
                    epoch).get_header()['phi_width']))

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

        self._sweep_resolution_limits = { }

        # store central resolution limit estimates

        batch_ranges = [self._sweep_handler.get_sweep_information(
            epoch).get_batch_range() for epoch in
                        self._sweep_handler.get_epochs()]

        self._resolution_limit_estimates = erzatz_resolution(
            self._prepared_reflections, batch_ranges)


        return

    def _scale(self):
        '''Perform all of the operations required to deliver the scaled
        data.'''

        epochs = self._sweep_handler.get_epochs()

        self._determine_best_scale_model_8way()

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

        sc = self._updated_aimless()
        sc.set_hklin(self._prepared_reflections)

        sc.set_chef_unmerged(True)

        scales_file = '%s.scales' % self._scalr_xname

        sc.set_new_scales_file(scales_file)

        user_resolution_limits = { }

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            intgr = si.get_integrater()

            if intgr.get_integrater_user_resolution():
                dmin = intgr.get_integrater_high_resolution()

                if not user_resolution_limits.has_key((dname, sname)):
                    user_resolution_limits[(dname, sname)] = dmin
                elif dmin < user_resolution_limits[(dname, sname)]:
                    user_resolution_limits[(dname, sname)] = dmin

            start, end = si.get_batch_range()

            if (dname, sname) in self._sweep_resolution_limits:
                resolution = self._sweep_resolution_limits[(dname, sname)]
                sc.add_run(start, end, exclude = False,
                           resolution = resolution, name = sname)
            else:
                sc.add_run(start, end, name = sname)

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled_test.mtz' % \
                                   (self._scalr_pname, self._scalr_xname)))

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        # what follows, sucks

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

        reflection_files = sc.get_scaled_reflection_files()

        for dataset in reflection_files:
            FileHandler.record_temporary_file(reflection_files[dataset])

        for key in loggraph:
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

        highest_resolution = 100.0

        # check in here that there is actually some data to scale..!

        if len(resolution_info) == 0:
            raise RuntimeError, 'no resolution info'

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            intgr = si.get_integrater()
            start, end = si.get_batch_range()

            if (dname, sname) in user_resolution_limits:
                resolution = user_resolution_limits[(dname, sname)]
                self._sweep_resolution_limits[(dname, sname)] = resolution
                if resolution < highest_resolution:
                    highest_resolution = resolution
                Chatter.write('Resolution limit for %s: %5.2f' % \
                              (dname, resolution))
                continue

            # extract the reflections for this sweep...

            hklin = sc.get_unmerged_reflection_file()
            hklout = os.path.join(self.get_working_directory(),
                                  'resolution_%s_%s.mtz' % (dname, sname))

            rb = self._factory.Rebatch()
            rb.set_hklin(hklin)
            rb.set_hklout(hklout)
            rb.limit_batches(start, end)

            FileHandler.record_temporary_file(hklout)

            log_completeness = os.path.join(self.get_working_directory(),
                                            '%s-completeness.log' % dname)

            if os.path.exists(log_completeness):
                log_completeness = None

            log_rmerge = os.path.join(self.get_working_directory(),
                                      '%s-rmerge.log' % dname)

            if os.path.exists(log_rmerge):
                log_rmerge = None

            log_isigma = os.path.join(self.get_working_directory(),
                                      '%s-isigma.log' % dname)

            if os.path.exists(log_isigma):
                log_isigma = None

            log_misigma = os.path.join(self.get_working_directory(),
                                      '%s-misigma.log' % dname)

            if os.path.exists(log_misigma):
                log_misigma = None

            m = merger(hklout)

            m.calculate_resolution_ranges(nbins = 100)

            r_comp = m.resolution_completeness(log = log_completeness)
            r_rm = m.resolution_rmerge(log = log_rmerge)
            r_uis = m.resolution_unmerged_isigma(log = log_isigma)
            r_mis = m.resolution_merged_isigma(log = log_misigma)

            resolution = max([r_comp, r_rm, r_uis, r_mis])

            Debug.write('Resolution for sweep %s: %.2f' % \
                        (sname, resolution))

            if not (dname, sname) in self._sweep_resolution_limits:
                self._sweep_resolution_limits[(dname, sname)] = resolution
                self.set_scaler_done(False)

            if resolution < highest_resolution:
                highest_resolution = resolution

            Chatter.write('Resolution limit for %s/%s: %5.2f' % \
                          (dname, sname,
                           self._sweep_resolution_limits[(dname, sname)]))

        self._scalr_highest_resolution = highest_resolution

        Debug.write('Scaler highest resolution set to %5.2f' % \
                    highest_resolution)

        if not self.get_scaler_done():
            Debug.write('Returning as scaling not finished...')
            return

        batch_info = { }

        for key in loggraph:
            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                batch_info[dataset] = transpose_loggraph(
                    loggraph[key])

        sc = self._updated_aimless()

        FileHandler.record_log_file('%s %s aimless' % (self._scalr_pname,
                                                       self._scalr_xname),
                                    sc.get_log_file())

        highest_resolution = 100.0

        sc.set_hklin(self._prepared_reflections)

        scales_file = '%s_final.scales' % self._scalr_xname

        sc.set_new_scales_file(scales_file)

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            start, end = si.get_batch_range()

            resolution_limit = self._sweep_resolution_limits[(dname, sname)]

            if resolution_limit < highest_resolution:
                highest_resolution = resolution_limit

            sc.add_run(start, end, exclude = False,
                       resolution = resolution_limit, name = xname)

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._scalr_pname, self._scalr_xname)))

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.scale()

        for dataset in resolution_info:
            if False:
                print dataset
                determine_scaled_resolution(
                    reflection_files[dataset], 3.0)[1]

        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()

        standard_deviation_info = { }

        for key in loggraph:
            if 'standard deviation v. Intensity' in key:
                dataset = key.split(',')[-1].strip()
                standard_deviation_info[dataset] = transpose_loggraph(
                    loggraph[key])

        resolution_info = { }

        for key in loggraph:
            if 'Analysis against resolution' in key:
                dataset = key.split(',')[-1].strip()
                resolution_info[dataset] = transpose_loggraph(
                    loggraph[key])

        batch_info = { }

        for key in loggraph:
            if 'Analysis against Batch' in key:
                dataset = key.split(',')[-1].strip()
                batch_info[dataset] = transpose_loggraph(
                    loggraph[key])

        # finally put all of the results "somewhere useful"

        self._scalr_statistics = data

        self._tmp_scaled_refl_files = copy.deepcopy(
            sc.get_scaled_reflection_files())

        self._scalr_scaled_reflection_files = { }
        self._scalr_scaled_reflection_files['sca'] = { }

        for key in self._tmp_scaled_refl_files:
            f = self._tmp_scaled_refl_files[key]
            scaout = '%s.sca' % f[:-4]

            m2v = self._factory.Mtz2various()
            m2v.set_hklin(f)
            m2v.set_hklout(scaout)
            m2v.convert()

            self._scalr_scaled_reflection_files['sca'][key] = scaout

            FileHandler.record_data_file(scaout)

        sc = self._updated_aimless()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        self._wavelengths_in_order = []

        for epoch in epochs:
            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            start, end = si.get_batch_range()

            resolution_limit = self._sweep_resolution_limits[(dname, sname)]

            sc.add_run(start, end, exclude = False,
                       resolution = resolution_limit, name = sname)

            if not dname in self._wavelengths_in_order:
                self._wavelengths_in_order.append(dname)

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_scaled.mtz' % \
                                   (self._scalr_pname,
                                    self._scalr_xname)))

        sc.set_scalepack()

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.scale()

        self._scalr_scaled_reflection_files['sca_unmerged'] = { }
        for key in self._tmp_scaled_refl_files:
            f = self._tmp_scaled_refl_files[key]
            scalepack = os.path.join(os.path.split(f)[0],
                                     os.path.split(f)[1].replace(
                '_scaled', '_scaled_unmerged').replace('.mtz', '.sca'))
            self._scalr_scaled_reflection_files['sca_unmerged'][
                key] = scalepack
            FileHandler.record_data_file(scalepack)

        sc = self._updated_aimless()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        self._wavelengths_in_order = []

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            start, end = si.get_batch_range()

            resolution_limit = self._sweep_resolution_limits[(dname, sname)]

            sc.add_run(start, end, exclude = False,
                       resolution = resolution_limit, name = sname)

            if not dname in self._wavelengths_in_order:
                self._wavelengths_in_order.append(dname)

        sc.set_hklout(os.path.join(self.get_working_directory(),
                                   '%s_%s_chef.mtz' % \
                                   (self._scalr_pname,
                                    self._scalr_xname)))

        sc.set_chef_unmerged(True)

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.scale()

        reflection_files = sc.get_scaled_reflection_files()

        return

    def _scale_finish(self):
        '''Finish off the scaling... This needs to be replaced with a
        call to AMI.'''

        # compute anomalous signals if anomalous

        if self.get_scaler_anomalous():
            for key in self._tmp_scaled_refl_files:
                f = self._tmp_scaled_refl_files[key]
                a_s = anomalous_signals(f)
                self._scalr_statistics[
                    (self._scalr_pname, self._scalr_xname, key)
                    ]['dF/F'] = [a_s[0]]
                self._scalr_statistics[
                    (self._scalr_pname, self._scalr_xname, key)
                    ]['dI/s(dI)'] = [a_s[1]]

        # convert I's to F's in Truncate

        if not Flags.get_small_molecule():
            for key in self._tmp_scaled_refl_files:
                f = self._tmp_scaled_refl_files[key]
                t = self._factory.Truncate()
                t.set_hklin(f)

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
                for path in os.path.split(f)[:-1]:
                    hklout = os.path.join(hklout, path)
                hklout = os.path.join(hklout, os.path.split(f)[-1].replace(
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

        ami = AnalyseMyIntensities()
        ami.set_working_directory(self.get_working_directory())

        average_unit_cell, ignore_sg = ami.compute_average_cell(
            [self._tmp_scaled_refl_files[key] for key in
             self._tmp_scaled_refl_files])

        Chatter.write('Computed average unit cell (will use in all files)')
        Chatter.write('%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
                      average_unit_cell)

        self._scalr_cell = average_unit_cell

        for key in self._tmp_scaled_refl_files:
            f = self._tmp_scaled_refl_files[key]

            hklout = '%s_cad.mtz' % f[:-4]
            FileHandler.record_temporary_file(hklout)

            c = self._factory.Cad()
            c.add_hklin(f)
            c.set_new_suffix(key)
            c.set_new_cell(average_unit_cell)
            c.set_hklout(hklout)
            c.update()

            self._tmp_scaled_refl_files[key] = hklout

        if len(self._tmp_scaled_refl_files) > 1:
            c = self._factory.Cad()
            for key in self._tmp_scaled_refl_files:
                f = self._tmp_scaled_refl_files[key]
                c.add_hklin(f)

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

            if len(self._tmp_scaled_refl_files) > 1 and \
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

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            if batch in si.get_batches():
                epochs.append(epoch)

        if len(epochs) > 1:
            raise RuntimeError, 'batch %d found in multiple sweeps' % batch

        return epochs[0]

    def _prepare_pointless_hklin(self, hklin, phi_width):
        return _prepare_pointless_hklin(self.get_working_directory(),
                                        hklin, phi_width)
