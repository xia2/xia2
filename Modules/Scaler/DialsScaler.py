# An implementation of the scaler interface for dials.scale

from __future__ import absolute_import, division, print_function
import os
import math
import copy as copy

from xia2.Handlers.Files import FileHandler
from xia2.lib.bits import auto_logfiler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.SymmetryLib import sort_lattices
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Modules.Scaler.CommonScaler import CommonScaler as Scaler
from xia2.Wrappers.Dials.Scale import DialsScale
from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory
from xia2.Modules.Scaler.CCP4ScalerHelpers import (
    SweepInformationHandler,
    get_umat_bmat_lattice_symmetry_from_mtz,
)
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from xia2.Wrappers.Dials.Reindex import Reindex as DialsReindex
from xia2.Wrappers.Dials.AssignUniqueIdentifiers import DialsAssignIdentifiers
from xia2.Wrappers.Dials.SplitExperiments import SplitExperiments
from xia2.Handlers.Syminfo import Syminfo
from dxtbx.serialize import load
from dials.util.batch_handling import calculate_batch_offsets
from cctbx import sgtbx
from dials.array_family import flex


def clean_reindex_operator(reindex_operator):
    return reindex_operator.replace("[", "").replace("]", "")


class DialsScaler(Scaler):
    def __init__(self):
        super(DialsScaler, self).__init__()

        self._scalr_scaled_refl_files = {}
        self._scalr_statistics = {}
        self._factory = CCP4Factory()  # allows lots of post-scaling calculations
        self._helper = DialsScalerHelper()
        self._scaler = None
        self._scaled_experiments = None
        self._scaled_reflections = None
        self._reference_reflections = None
        self._reference_experiments = None
        self._no_times_scaled = 0
        self._scaler_symmetry_check_count = 0

    # Schema/Sweep.py wants these two methods need to be implemented by subclasses,
    # but are not actually used at the moment?
    def _scale_list_likely_pointgroups(self):
        pass

    def _scale_reindex_to_reference(self):
        pass

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        self._helper.set_working_directory(working_directory)

    def _updated_dials_scaler(self):
        # Sets the relevant parameters from the PhilIndex

        resolution = PhilIndex.params.xia2.settings.resolution
        self._scaler.set_resolution(d_min=resolution.d_min, d_max=resolution.d_max)

        self._scaler.set_model(PhilIndex.params.dials.scale.model)
        self._scaler.set_intensities(PhilIndex.params.dials.scale.intensity_choice)

        self._scaler.set_full_matrix(PhilIndex.params.dials.scale.full_matrix)
        self._scaler.set_outlier_rejection(
            PhilIndex.params.dials.scale.outlier_rejection
        )
        self._scaler.set_outlier_zmax(PhilIndex.params.dials.scale.outlier_zmax)
        self._scaler.set_optimise_errors(PhilIndex.params.dials.scale.optimise_errors)

        if PhilIndex.params.dials.scale.model == "physical":
            self._scaler.set_spacing(PhilIndex.params.dials.scale.rotation_spacing)
            if PhilIndex.params.dials.scale.Bfactor:
                self._scaler.set_bfactor(
                    True, PhilIndex.params.dials.scale.physical_model.Bfactor_spacing
                )
            if PhilIndex.params.dials.scale.absorption:
                self._scaler.set_absorption_correction(True)
                self._scaler.set_lmax(PhilIndex.params.dials.scale.physical_model.lmax)
        elif PhilIndex.params.dials.scale.model == "kb":
            # For KB model, want both Bfactor and scale terms
            self._scaler.set_bfactor(True)
        elif PhilIndex.params.dials.scale.model == "array":
            self._scaler.set_spacing(PhilIndex.params.dials.scale.rotation_spacing)
            if PhilIndex.params.dials.scale.Bfactor:
                self._scaler.set_bfactor(True)
                self._scaler.set_decay_bins(
                    PhilIndex.params.dials.scale.array_model.resolution_bins
                )
            if PhilIndex.params.dials.scale.absorption:
                self._scaler.set_absorption_correction(True)
                self._scaler.set_lmax(
                    PhilIndex.params.dials.scale.array_model.absorption_bins
                )

        return self._scaler

    def _scale_prepare(self):
        """Perform all of the preparation required to deliver the scaled
        data. This should sort together the reflection files, ensure that
        they are correctly indexed (via dials.symmetry) and generally tidy
        things up."""

        # AIM discover symmetry and reindex with dials.symmetry, and set the correct
        # reflections in si.reflections, si.experiments

        self._helper.set_working_directory(self.get_working_directory())
        self._factory.set_working_directory(self.get_working_directory())

        need_to_return = False

        self._sweep_handler = SweepInformationHandler(self._scalr_integraters)

        p, x = self._sweep_handler.get_project_info()
        self._scalr_pname = p
        self._scalr_xname = x

        self._helper.set_pname_xname(p, x)

        Journal.block(
            "gathering",
            self.get_scaler_xcrystal().get_name(),
            "Dials",
            {"working directory": self.get_working_directory()},
        )

        # First do stuff to work out if excluding any data
        # Note - does this actually work? I couldn't seem to get it to work
        # in either this pipeline or the standard dials pipeline
        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            intgr = si.get_integrater()
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()

            exclude_sweep = False

            for sweep in PhilIndex.params.xia2.settings.sweep:
                if sweep.id == sname and sweep.exclude:
                    exclude_sweep = True
                    break

            if exclude_sweep:
                self._sweep_handler.remove_epoch(epoch)
                Debug.write("Excluding sweep %s" % sname)
            else:
                Journal.entry({"adding data from": "%s/%s/%s" % (xname, dname, sname)})

        # If multiple files, want to run symmetry to check for consistent indexing
        # also

        multi_sweep_indexing = PhilIndex.params.xia2.settings.multi_sweep_indexing

        # try to reproduce what CCP4ScalerA is doing

        # first assign identifiers to avoid dataset-id collisions
        # Idea is that this should be called anytime you get data anew from the
        # integrater, to intercept and assign unique ids, then set in the
        # sweep_information (si) and always use si.set_reflections/
        # si.get_reflections as we process.
        self._sweep_handler = self._helper.assign_and_return_datasets(
            self._sweep_handler
        )

        # START OF if more than one epoch
        if len(self._sweep_handler.get_epochs()) > 1:

            # First - force all lattices to be same and hope its okay.
            # START OF if multi_sweep indexing and not input pg
            if multi_sweep_indexing and not self._scalr_input_pointgroup:

                refiners = []
                experiments = []
                reflections = []

                for epoch in self._sweep_handler.get_epochs():
                    si = self._sweep_handler.get_sweep_information(epoch)
                    integrater = si.get_integrater()
                    experiments.append(si.get_experiments())
                    reflections.append(si.get_reflections())
                    refiners.append(integrater.get_integrater_refiner())

                Debug.write(
                    "Running multisweep dials.symmetry for %d sweeps" % len(refiners)
                )
                pointgroup, reindex_op, ntr, pt, reind_refl, reind_exp, reindex_initial = self._dials_symmetry_indexer_jiffy(
                    experiments, reflections, refiners, multisweep=True
                )

                FileHandler.record_temporary_file(reind_refl)
                FileHandler.record_temporary_file(reind_exp)

                Debug.write("X1698: %s: %s" % (pointgroup, reindex_op))

                lattices = [Syminfo.get_lattice(pointgroup)]

                for epoch in self._sweep_handler.get_epochs():
                    si = self._sweep_handler.get_sweep_information(epoch)
                    intgr = si.get_integrater()
                    if ntr:
                        intgr.integrater_reset_reindex_operator()
                        need_to_return = True

                # SUMMARY - got data from all sweeps, ran _symmetry_indexer_multisweep
                # on this, made a list of one lattice and potentially reset reindex op?
            # END OF if multi_sweep indexing and not input pg

            # START OF if not multi_sweep, or input pg given
            else:
                lattices = []

                for epoch in self._sweep_handler.get_epochs():

                    si = self._sweep_handler.get_sweep_information(epoch)
                    intgr = si.get_integrater()
                    experiment = intgr.get_integrated_experiments()
                    reflections = intgr.get_integrated_reflections()
                    refiner = intgr.get_integrater_refiner()

                    if self._scalr_input_pointgroup:
                        pointgroup = self._scalr_input_pointgroup
                        reindex_op = "h,k,l"
                        ntr = False
                    else:
                        pointgroup, reindex_op, ntr, pt, reind_refl, reind_exp, reindex_initial = self._dials_symmetry_indexer_jiffy(
                            [experiment], [reflections], [refiner]
                        )
                        if reindex_initial:
                            self._helper.reindex_jiffy(si, reindex_op=reindex_op)
                        else:
                            si.set_experiments(reind_exp)
                            si.set_reflections(reind_refl)

                        Debug.write("X1698: %s: %s" % (pointgroup, reindex_op))

                    lattice = Syminfo.get_lattice(pointgroup)

                    if not lattice in lattices:
                        lattices.append(lattice)

                    if ntr:

                        intgr.integrater_reset_reindex_operator()
                        need_to_return = True
                # SUMMARY do dials.symmetry on each sweep, get lattices and make a list
                # of unique lattices, potentially reset reindex op.
            # END OF if not multi_sweep, or input pg given

            # SUMMARY - still within if more than one epoch, now have a list of number
            # of lattices

            # START OF if multiple-lattices
            if len(lattices) > 1:
                correct_lattice = sort_lattices(lattices)[0]
                Chatter.write("Correct lattice asserted to be %s" % correct_lattice)

                # transfer this information back to the indexers
                for epoch in self._sweep_handler.get_epochs():

                    si = self._sweep_handler.get_sweep_information(epoch)
                    refiner = si.get_integrater().get_integrater_refiner()
                    sname = si.get_sweep_name()

                    state = refiner.set_refiner_asserted_lattice(correct_lattice)

                    if state == refiner.LATTICE_CORRECT:
                        Chatter.write(
                            "Lattice %s ok for sweep %s" % (correct_lattice, sname)
                        )
                    elif state == refiner.LATTICE_IMPOSSIBLE:
                        raise RuntimeError(
                            "Lattice %s impossible for %s" % (correct_lattice, sname)
                        )
                    elif state == refiner.LATTICE_POSSIBLE:
                        Chatter.write(
                            "Lattice %s assigned for sweep %s"
                            % (correct_lattice, sname)
                        )
                        need_to_return = True

            # END OF if multiple-lattices
            # SUMMARY - forced all lattices to be same and hope its okay.
        # END OF if more than one epoch

        # if one or more of them was not in the lowest lattice,
        # need to return here to allow reprocessing

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------

        # all should share the same pointgroup, unless twinned... in which
        # case force them to be...

        pointgroups = {}
        reindex_ops = {}
        probably_twinned = False

        need_to_return = False

        multi_sweep_indexing = PhilIndex.params.xia2.settings.multi_sweep_indexing

        # START OF if multi-sweep and not input pg
        if multi_sweep_indexing and not self._scalr_input_pointgroup:

            refiners = []
            experiments = []
            reflections = []

            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                integrater = si.get_integrater()
                experiments.append(si.get_experiments())
                reflections.append(si.get_reflections())
                refiners.append(integrater.get_integrater_refiner())

            pointgroup, reindex_op, ntr, pt, reind_refl, reind_exp, reindex_initial = self._dials_symmetry_indexer_jiffy(
                experiments, reflections, refiners, multisweep=True
            )

            if reindex_initial:
                self._helper.reindex_jiffy(si, reindex_op=reindex_op)
            else:
                self._sweep_handler = self._helper.split_experiments(
                    reind_exp, reind_refl, self._sweep_handler
                )

            experiments_to_rebatch = []
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                experiments_to_rebatch.append(
                    load.experiment_list(si.get_experiments())[0]
                )

            offsets = calculate_batch_offsets(experiments_to_rebatch)

            for i, epoch in enumerate(self._sweep_handler.get_epochs()):
                si = self._sweep_handler.get_sweep_information(epoch)
                r = si.get_batch_range()
                si.set_batch_offset(offsets[i])
                si.set_batches([r[0] + offsets[i], r[1] + offsets[i]])

            Chatter.write(
                "Point group determined for multi sweep indexing: %s" % pointgroup
            )
            Chatter.write(
                "Reindexing operator for multi sweep indexing: %s" % reindex_op
            )

            for epoch in self._sweep_handler.get_epochs():
                pointgroups[epoch] = pointgroup
                reindex_ops[epoch] = reindex_op
            # SUMMARY ran dials.symmetry multisweep and made a dict
            # of pointgroups and reindex_ops (all same??)
        # END OF if multi-sweep and not input pg

        # START OF if not mulit-sweep or pg given
        else:
            experiments_to_rebatch = []

            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                intgr = si.get_integrater()
                experiment = si.get_experiments()
                reflections = si.get_reflections()
                refiner = intgr.get_integrater_refiner()
                if self._scalr_input_pointgroup:
                    Debug.write(
                        "Using input pointgroup: %s" % self._scalr_input_pointgroup
                    )
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = "h,k,l"
                    pt = False
                    experiments_to_rebatch.append(load.experiment_list(experiment)[0])

                else:
                    pointgroup, reindex_op, ntr, pt, reind_refl, reind_exp, reindex_initial = self._dials_symmetry_indexer_jiffy(
                        [experiment], [reflections], [refiner]
                    )
                    if reindex_initial:
                        self._helper.reindex_jiffy(si, reindex_op=reindex_op)
                        experiments_to_rebatch.append(
                            load.experiment_list(si.get_experiments())[0]
                        )
                    else:
                        experiments_to_rebatch.append(
                            load.experiment_list(reind_exp)[0]
                        )
                        si.set_experiments(reind_exp)
                        si.set_reflections(reind_refl)

                    Debug.write("X1698: %s: %s" % (pointgroup, reindex_op))

                    if ntr:
                        intgr.integrater_reset_reindex_operator()
                        need_to_return = True

                if pt and not probably_twinned:
                    probably_twinned = True

                Debug.write("Pointgroup: %s (%s)" % (pointgroup, reindex_op))

                pointgroups[epoch] = pointgroup
                reindex_ops[epoch] = reindex_op
            # SUMMARY - for each sweep, run indexer jiffy and get reindex operators
            # and pointgroups dictionaries (could be different between sweeps)

            offsets = calculate_batch_offsets(experiments_to_rebatch)

            for i, epoch in enumerate(self._sweep_handler.get_epochs()):
                si = self._sweep_handler.get_sweep_information(epoch)
                r = si.get_batch_range()
                si.set_batch_offset(offsets[i])
                si.set_batches([r[0] + offsets[i], r[1] + offsets[i]])

        # END OF if not mulit-sweep or pg given

        overall_pointgroup = None

        pointgroup_set = {pointgroups[e] for e in pointgroups}

        if len(pointgroup_set) > 1 and not probably_twinned:
            raise RuntimeError("non uniform pointgroups")

        if len(pointgroup_set) > 1:
            Debug.write(
                "Probably twinned, pointgroups: %s"
                % " ".join([p.replace(" ", "") for p in list(pointgroup_set)])
            )
            numbers = [Syminfo.spacegroup_name_to_number(s) for s in pointgroup_set]
            overall_pointgroup = Syminfo.spacegroup_number_to_name(min(numbers))
            self._scalr_input_pointgroup = overall_pointgroup

            Chatter.write(
                "Twinning detected, assume pointgroup %s" % overall_pointgroup
            )

            need_to_return = True

        else:
            overall_pointgroup = pointgroup_set.pop()
        # SUMMARY - Have handled if different pointgroups & chosen an overall_pointgroup
        # which is the lowest symmetry
        self._scalr_likely_spacegroups = [overall_pointgroup]
        if not self._scalr_input_pointgroup:
            Chatter.write("Likely pointgroup determined by dials.symmetry:")
            for spag in self._scalr_likely_spacegroups:
                Chatter.write("%s" % spag)
        else:
            assert len(self._scalr_likely_spacegroups) == 1
            Chatter.write(
                "Using preselected space group: %s" % self._scalr_likely_spacegroups[0]
            )

        # Now go through sweeps and do reindexing
        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)

            integrater = si.get_integrater()

            integrater.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(overall_pointgroup)
            )
            integrater.set_integrater_reindex_operator(
                reindex_ops[epoch], reason="setting point group"
            )
            integrater.set_output_format("pickle")
            _ = integrater.get_integrater_intensities()
            # ^ This will give us the reflections in the correct point group
            si.set_reflections(integrater.get_integrated_reflections())
            si.set_experiments(integrater.get_integrated_experiments())

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        if PhilIndex.params.xia2.settings.unify_setting:
            from scitbx.matrix import sqr

            reference_U = None
            i3 = sqr((1, 0, 0, 0, 1, 0, 0, 0, 1))

            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                intgr = si.get_integrater()
                fixed = sqr(intgr.get_goniometer().get_fixed_rotation())
                u, b, s = get_umat_bmat_lattice_symmetry_from_mtz(si.get_reflections())
                U = fixed.inverse() * sqr(u).transpose()
                B = sqr(b)

                if reference_U is None:
                    reference_U = U
                    continue

                results = []
                for op in s.all_ops():
                    R = B * sqr(op.r().as_double()).transpose() * B.inverse()
                    nearly_i3 = (U * R).inverse() * reference_U
                    score = sum([abs(_n - _i) for (_n, _i) in zip(nearly_i3, i3)])
                    results.append((score, op.r().as_hkl(), op))

                results.sort()
                best = results[0]
                Debug.write("Best reindex: %s %.3f" % (best[1], best[0]))
                intgr.set_integrater_reindex_operator(
                    best[2].r().inverse().as_hkl(), reason="unifying [U] setting"
                )
                si.set_reflections(intgr.get_integrater_intensities())

                # recalculate to verify
                u, b, s = get_umat_bmat_lattice_symmetry_from_mtz(si.get_reflections())
                U = fixed.inverse() * sqr(u).transpose()
                Debug.write("New reindex: %s" % (U.inverse() * reference_U))
            # need to set identifiers again
            self._sweep_handler = self._helper.assign_and_return_datasets(
                self._sweep_handler
            )

        # FIXME use a reference reflection file as set by xcrystal?
        # if self.get_scaler_reference_reflection_file():
        #  Debug.write('Using HKLREF %s' % self._reference)
        #  self._reference = self.get_scaler_reference_reflection_file()

        if PhilIndex.params.xia2.settings.scale.reference_reflection_file:
            if not PhilIndex.params.xia2.settings.scale.reference_experiment_file:
                Chatter.write(
                    "No reference experiments.json provided, reference reflection file will not be used"
                )
            else:
                self._reference_reflections = (
                    PhilIndex.params.xia2.settings.scale.reference_reflection_file
                )
                self._reference_experiments = (
                    PhilIndex.params.xia2.settings.scale.reference_experiment_file
                )
                Debug.write(
                    "Using reference reflections %s" % self._reference_reflections
                )
                Debug.write(
                    "Using reference experiments %s" % self._reference_experiments
                )

        params = PhilIndex.params
        use_brehm_diederichs = params.xia2.settings.use_brehm_diederichs
        if len(self._sweep_handler.get_epochs()) > 1 and use_brehm_diederichs:

            brehm_diederichs_files_in = []
            for epoch in self._sweep_handler.get_epochs():

                si = self._sweep_handler.get_sweep_information(epoch)
                hklin = (
                    si.get_reflections()
                )  # FIXME this currently gets a pickle, needs mtz
                brehm_diederichs_files_in.append(hklin)

            # now run cctbx.brehm_diederichs to figure out the indexing hand for
            # each sweep
            from xia2.Wrappers.Cctbx.BrehmDiederichs import BrehmDiederichs

            brehm_diederichs = BrehmDiederichs()
            brehm_diederichs.set_working_directory(self.get_working_directory())
            auto_logfiler(brehm_diederichs)
            brehm_diederichs.set_input_filenames(brehm_diederichs_files_in)
            # 1 or 3? 1 seems to work better?
            brehm_diederichs.set_asymmetric(1)
            brehm_diederichs.run()
            reindexing_dict = brehm_diederichs.get_reindexing_dict()

            for epoch in self._sweep_handler.get_epochs():

                si = self._sweep_handler.get_sweep_information(epoch)
                intgr = si.get_integrater()
                hklin = si.get_reflections()

                reindex_op = reindexing_dict.get(os.path.abspath(hklin))
                assert reindex_op is not None

                if 1 or reindex_op != "h,k,l":
                    # apply the reindexing operator
                    intgr.set_integrater_reindex_operator(
                        reindex_op, reason="match reference"
                    )
                    si.set_reflections(intgr.get_integrater_intensities())

        # If not Brehm-deidrichs, set reference as first sweep
        elif (
            len(self._sweep_handler.get_epochs()) > 1
            and not self._reference_reflections
        ):

            Chatter.write("First sweep will be used as reference for reindexing")
            first = self._sweep_handler.get_epochs()[0]
            si = self._sweep_handler.get_sweep_information(first)
            self._reference_experiments = si.get_experiments()
            self._reference_reflections = si.get_reflections()

        # Now reindex to be consistent with first dataset - run reindex on each
        # dataset with reference
        if self._reference_reflections:
            assert self._reference_experiments

            exp = load.experiment_list(self._reference_experiments)
            reference_cell = exp[0].crystal.get_unit_cell().parameters()

            # then compute the pointgroup from this...

            # ---------- REINDEX TO CORRECT (REFERENCE) SETTING ----------
            Chatter.write("Reindexing all datasets to common reference")
            counter = 1
            first = self._sweep_handler.get_epochs()[0]
            for epoch in self._sweep_handler.get_epochs():
                if epoch != first:
                    reindexed_exp_fpath = os.path.join(
                        self.get_working_directory(),
                        str(counter) + "_reindexed_experiments.json",
                    )
                    reindexed_refl_fpath = os.path.join(
                        self.get_working_directory(),
                        str(counter) + "_reindexed_reflections.pickle",
                    )

                    # if we are working with unified UB matrix then this should not
                    # be a problem here (note, *if*; *should*)

                    # what about e.g. alternative P1 settings?
                    # see JIRA MXSW-904
                    if PhilIndex.params.xia2.settings.unify_setting:
                        continue

                    reindexer = DialsReindex()
                    reindexer.set_working_directory(self.get_working_directory())
                    auto_logfiler(reindexer)

                    si = self._sweep_handler.get_sweep_information(epoch)
                    exp = si.get_experiments()
                    refl = si.get_reflections()

                    reindexer.set_reference_filename(self._reference_experiments)
                    reindexer.set_reference_reflections(self._reference_reflections)
                    reindexer.set_indexed_filename(refl)
                    reindexer.set_experiments_filename(exp)
                    reindexer.set_reindexed_experiments_filename(reindexed_exp_fpath)
                    reindexer.set_reindexed_reflections_filename(reindexed_refl_fpath)

                    reindexer.run()

                    # FIXME : Should implement something like the following - problem
                    # is currently no way to get reindex op from reindexer?
                    # integrater = si.get_integrater()
                    # integrater.set_integrater_reindex_operator(reindex_op,
                    #                                         reason='match reference')
                    # integrater.set_integrater_spacegroup_number(
                    #   Syminfo.spacegroup_name_to_number(pointgroup))
                    # integrater.integrate()
                    # si.set_reflections(integrater.get_integrated_reflections)
                    # si.set_experiments(integrater.get_integrated_experiments)

                    si.set_reflections(reindexed_refl_fpath)
                    si.set_experiments(reindexed_exp_fpath)

                    FileHandler.record_temporary_file(reindexed_exp_fpath)
                    FileHandler.record_temporary_file(reindexed_refl_fpath)

                    Debug.write("Completed reindexing of %s" % " ".join([exp, refl]))

                    # FIXME how to get some indication of the reindexing used?

                    counter += 1
                    exp = load.experiment_list(reindexed_exp_fpath)
                    cell = exp[0].crystal.get_unit_cell().parameters()

                    # Note - no lattice check as this will already be caught by reindex
                    Debug.write("Cell: %.2f %.2f %.2f %.2f %.2f %.2f" % cell)
                    Debug.write("Ref:  %.2f %.2f %.2f %.2f %.2f %.2f" % reference_cell)

                    for j in range(6):
                        if (
                            math.fabs((cell[j] - reference_cell[j]) / reference_cell[j])
                            > 0.1
                        ):
                            raise RuntimeError(
                                "unit cell parameters differ in %s and %s"
                                % (self._reference, si.get_reflections())
                            )

        # Now all have been reindexed, run a round of space group determination on
        # joint set.

        # FIXME not yet implemented for dials.symmetry? just take point group now
        # from first experiment - better to merge all into one refl file?

        # why was the next bit here before, as have already run dials.symmetry on
        # all data - was only setting self._scalr_likely_spacegroups?

        # should this now be passed back to integrater?

    def _scale(self):
        """Perform all of the operations required to deliver the scaled
        data."""
        epochs = self._sweep_handler.get_epochs()

        if self._scalr_corrections:
            Journal.block(
                "scaling",
                self.get_scaler_xcrystal().get_name(),
                "Dials",
                {
                    "scaling model": "automatic",
                    "absorption": self._scalr_correct_absorption,
                    "decay": self._scalr_correct_decay,
                },
            )

        else:
            Journal.block(
                "scaling",
                self.get_scaler_xcrystal().get_name(),
                "Dials",
                {"scaling model": "default"},
            )

        self._scaler = DialsScale()
        self._scaler = self._updated_dials_scaler()

        # Set paths
        scaled_mtz_path = os.path.join(
            self.get_working_directory(),
            "%s_%s_scaled.mtz" % (self._scalr_pname, self._scalr_xname),
        )
        scaled_unmerged_mtz_path = os.path.join(
            self.get_working_directory(),
            "%s_%s_scaled_unmerged.mtz" % (self._scalr_pname, self._scalr_xname),
        )

        if self._scaled_experiments and self._scaled_reflections:
            # going to continue-where-left-off
            self._scaler.add_experiments_json(self._scaled_experiments)
            self._scaler.add_reflections_pickle(self._scaled_reflections)
        else:
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                experiment = si.get_experiments()
                reflections = si.get_reflections()
                self._scaler.add_experiments_json(experiment)
                self._scaler.add_reflections_pickle(reflections)

        self._scaler.set_scaled_unmerged_mtz(scaled_unmerged_mtz_path)
        self._scaler.set_scaled_mtz(scaled_mtz_path)
        self._scaler.set_crystal_name(self._scalr_xname)
        self._scalr_scaled_reflection_files = {}
        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
        self._scalr_scaled_reflection_files["mtz_unmerged"] = {
            dname: scaled_unmerged_mtz_path
        }
        self._scalr_scaled_reflection_files["mtz"] = {dname: scaled_mtz_path}

        user_resolution_limits = {}

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            intgr = si.get_integrater()

            if intgr.get_integrater_user_resolution():
                # record user resolution here but don't use it until later - why?
                dmin = intgr.get_integrater_high_resolution()

                if (dname, sname) not in user_resolution_limits:
                    user_resolution_limits[(dname, sname)] = dmin
                elif dmin < user_resolution_limits[(dname, sname)]:
                    user_resolution_limits[(dname, sname)] = dmin

            if (dname, sname) in self._scalr_resolution_limits:
                d_min, d_max = self._scalr_resolution_limits[(dname, sname)]
                self._scaler.set_resolution(d_min=d_min, d_max=d_max)

        self._scaler.set_working_directory(self.get_working_directory())
        auto_logfiler(self._scaler)
        FileHandler.record_log_file(
            "%s %s SCALE" % (self._scalr_pname, self._scalr_xname),
            self._scaler.get_log_file(),
        )
        self._scaler.scale()
        self._scaled_experiments = self._scaler.get_scaled_experiments()
        self._scaled_reflections = self._scaler.get_scaled_reflections()

        FileHandler.record_data_file(scaled_unmerged_mtz_path)
        FileHandler.record_data_file(scaled_mtz_path)

        # make it so that only scaled.pickle and scaled_experiments.json are
        # the files that dials.scale knows about, so that if scale is called again,
        # scaling resumes from where it left off.
        self._scaler.clear_datafiles()

        '''if not self._scalr_input_spacegroup:
      self._determine_scaled_pointgroup()

    if self._scalr_done is False:
      if self._scaler_symmetry_check_count > 3:
        Chatter.write("""Scaling symmetry check and rescale appears unstable,
No further scaling will be performed.""")
        self.set_scaler_done(True)
      else:
        return'''

        hklout = copy.deepcopy(self._scaler.get_scaled_mtz())
        self._scalr_scaled_refl_files = {dname: hklout}
        FileHandler.record_data_file(hklout)

        highest_suggested_resolution = None
        highest_resolution = 100.0

        # copypasta from CCP4ScalerA - could be grouped into common method? -
        # no, different in future for how get individual mtz files from combined dataset
        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            intgr = si.get_integrater()
            start, end = si.get_batch_range()

            if (dname, sname) in self._scalr_resolution_limits:
                continue

            elif (dname, sname) in user_resolution_limits:
                limit = user_resolution_limits[(dname, sname)]
                self._scalr_resolution_limits[(dname, sname)] = (limit, None)
                if limit < highest_resolution:
                    highest_resolution = limit
                Chatter.write(
                    "Resolution limit for %s: %5.2f (user provided)" % (dname, limit)
                )
                continue

            # FIXME need to separate out data into different sweeps based on experiment
            # id in order to calculate a res limit for each dataset.
            # However dials.scale does not yet allow different resolutions per dataset

            hklin = (
                self._scaler.get_unmerged_reflection_file()
            )  # combined for all datasets
            # Need to get an individual mtz for each dataset
            limit, reasoning = self._estimate_resolution_limit(
                hklin, batch_range=None, use_misigma=False
            )

            if PhilIndex.params.xia2.settings.resolution.keep_all_reflections == True:
                suggested = limit
                if (
                    highest_suggested_resolution is None
                    or limit < highest_suggested_resolution
                ):
                    highest_suggested_resolution = limit
                limit = intgr.get_detector().get_max_resolution(
                    intgr.get_beam_obj().get_s0()
                )
                self._scalr_resolution_limits[(dname, sname)] = (limit, suggested)
                Debug.write("keep_all_reflections set, using detector limits")
            Debug.write("Resolution for sweep %s: %.2f" % (sname, limit))

            if not (dname, sname) in self._scalr_resolution_limits:
                self._scalr_resolution_limits[(dname, sname)] = (limit, None)
                self.set_scaler_done(False)

            if limit < highest_resolution:
                highest_resolution = limit

            limit, suggested = self._scalr_resolution_limits[(dname, sname)]
            if suggested is None or limit == suggested:
                reasoning_str = ""
                if reasoning:
                    reasoning_str = " (%s)" % reasoning
                Chatter.write(
                    "Resolution for sweep %s/%s: %.2f%s"
                    % (dname, sname, limit, reasoning_str)
                )
            else:
                Chatter.write(
                    "Resolution limit for %s/%s: %5.2f (%5.2f suggested)"
                    % (dname, sname, limit, suggested)
                )

        if highest_suggested_resolution is not None and highest_resolution >= (
            highest_suggested_resolution - 0.004
        ):
            Debug.write(
                "Dropping resolution cut-off suggestion since it is"
                " essentially identical to the actual resolution limit."
            )
            highest_suggested_resolution = None
        self._scalr_highest_resolution = highest_resolution
        self._scalr_highest_suggested_resolution = highest_suggested_resolution
        if highest_suggested_resolution is not None:
            Debug.write(
                "Suggested highest resolution is %5.2f (%5.2f suggested)"
                % (highest_resolution, highest_suggested_resolution)
            )
        else:
            Debug.write("Scaler highest resolution set to %5.2f" % highest_resolution)

        if PhilIndex.params.xia2.settings.merging_statistics.source == "cctbx":
            for key in self._scalr_scaled_refl_files:
                stats = self._compute_scaler_statistics(
                    self._scalr_scaled_reflection_files["mtz_unmerged"][key],
                    selected_band=(highest_suggested_resolution, None),
                    wave=key,
                )
                self._scalr_statistics[
                    (self._scalr_pname, self._scalr_xname, key)
                ] = stats  # adds here
                Chatter.write(
                    """Short summary of current overall merging statistics:
Resolution limits: %.2f, %.2f
Total observations/unique: %s, %s"""
                    % (
                        stats["High resolution limit"][0],
                        stats["Low resolution limit"][0],
                        stats["Total observations"][0],
                        stats["Total unique"][0],
                    )
                )
                if PhilIndex.params.xia2.settings.small_molecule:
                    try:
                        Chatter.write(
                            "Rmerge: %.4f, Rmeas: %.4f, Rpim: %.4f, CC1/2: %.4f)"
                            % (
                                stats["Rmerge(I)"][0],
                                stats["Rmeas(I)"][0],
                                stats["Rpim(I)"][0],
                                stats["CC half"][0],
                            )
                        )
                    except (KeyError, IndexError):
                        pass
                else:
                    try:
                        Chatter.write(
                            """Rmerge (I+/-): %.4f, Rmeas (I+/-): %.4f, Rpim (I+/-): %.4f
CC1/2: %.4f, Anomalous correlation %.4f"""
                            % (
                                stats["Rmerge(I+/-)"][0],
                                stats["Rmeas(I+/-)"][0],
                                stats["Rpim(I+/-)"][0],
                                stats["CC half"][0],
                                stats["Anomalous correlation"][0],
                            )
                        )
                    except (KeyError, IndexError):
                        pass

        if self._scalr_done is False:
            self._scaler_symmetry_check_count = (
                0
            )  # reset for when resolution limit applied
            return

        # Run twotheta refine
        self._update_scaled_unit_cell()

    def _determine_scaled_pointgroup(self):
        """Rerun symmetry after scaling to check for consistent space group. If not,
        then new space group should be used and data rescaled."""
        from cctbx import crystal

        exp_crystal = load.experiment_list(self._scaler.get_scaled_experiments())[
            0
        ].crystal
        cs = crystal.symmetry(
            space_group=exp_crystal.get_space_group(),
            unit_cell=exp_crystal.get_unit_cell(),
        )
        cs_ref = cs.as_reference_setting()
        current_pointgroup = cs_ref.space_group()
        current_patt_group = (
            current_pointgroup.build_derived_patterson_group().type().lookup_symbol()
        )
        Debug.write(
            "Space group used in scaling: %s"
            % current_pointgroup.type().lookup_symbol()
        )
        first = self._sweep_handler.get_epochs()[0]
        si = self._sweep_handler.get_sweep_information(first)
        refiner = si.get_integrater().get_integrater_refiner()
        point_group, reindex_op, _, _, reind_refl, reind_exp, reindex_initial = self._dials_symmetry_indexer_jiffy(
            [self._scaler.get_scaled_experiments()],
            [self._scaler.get_scaled_reflections()],
            [refiner],
        )
        Debug.write(
            "Point group determined by dials.symmetry on scaled dataset: %s"
            % point_group
        )
        sginfo = sgtbx.space_group_info(symbol=point_group)
        patt_group = (
            sginfo.group().build_derived_patterson_group().type().lookup_symbol()
        )
        self._scaler_symmetry_check_count += 1
        if patt_group != current_patt_group:
            if reindex_initial:
                reindexer = DialsReindex()
                reindexer.set_working_directory(self.get_working_directory())
                auto_logfiler(reindexer)
                reindexer.set_experiments_filename(
                    self._scaler.get_scaled_experiments()
                )
                reindexer.set_indexed_filename(self._scaler.get_scaled_reflections())
                reindexer.set_cb_op(reindex_op)
                reindexer.run()
                self._scaler.set_scaled_experiments(
                    reindexer.get_reindexed_experiments_filename()
                )
                self._scaler.set_scaled_reflections(
                    reindexer.get_reindexed_reflections_filename()
                )
            else:
                self._scaler.set_scaled_experiments(reind_exp)
                self._scaler.set_scaled_reflections(reind_refl)
            self.set_scaler_done(False)
            Chatter.write(
                """Inconsistent space groups determined before and after scaling: %s, %s \n
Data will be rescaled in new point group"""
                % (current_patt_group, patt_group)
            )
            return
        else:
            Chatter.write("Consistent space group determined before and after scaling")

    def _dials_symmetry_indexer_jiffy(
        self, experiments, reflections, refiners, multisweep=False
    ):
        return self._helper.dials_symmetry_indexer_jiffy(
            experiments, reflections, refiners, multisweep
        )


class DialsScalerHelper(object):
    """A class to help the CCP4 Scaler along a little."""

    def __init__(self):
        self._working_directory = os.getcwd()
        self._scalr_xname = None
        self._scalr_pname = None

    def set_pname_xname(self, pname, xname):
        self._scalr_xname = xname
        self._scalr_pname = pname

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory

    def get_working_directory(self):
        return self._working_directory

    def assign_dataset_identifiers(self, experiments, reflections):
        """Assign unique identifiers to the datasets"""
        assigner = DialsAssignIdentifiers()
        assigner.set_working_directory(self.get_working_directory())
        auto_logfiler(assigner)
        for (exp, refl) in zip(experiments, reflections):
            assigner.add_experiments(exp)
            assigner.add_reflections(refl)
        assigner.assign_identifiers()
        return assigner

    def split_experiments(self, experiment, reflection, sweep_handler):
        """Split a multi-experiment dataset into individual datasets and set in the
        sweep handler."""
        splitter = SplitExperiments()
        splitter.add_experiments(experiment)
        splitter.add_reflections(reflection)
        splitter.set_working_directory(self.get_working_directory())
        auto_logfiler(splitter)
        splitter.run()

        nn = len(sweep_handler.get_epochs())
        fmt = "%%0%dd" % (math.log10(nn) + 1)

        for i, epoch in enumerate(sweep_handler.get_epochs()):
            si = sweep_handler.get_sweep_information(epoch)
            nums = fmt % i
            si.set_reflections(
                os.path.join(
                    self.get_working_directory(), "split_reflections_%s.pickle" % nums
                )
            )
            si.set_experiments(
                os.path.join(
                    self.get_working_directory(), "split_experiments_%s.json" % nums
                )
            )
        return sweep_handler

    def _renumber_ids_in_tables(self, sweep_handler):
        """Renumber all dataset ids in tables to be unique, as this is not
        done in the current version of split_experiments, for backwards compability."""
        nn = len(sweep_handler.get_epochs())
        fmt = "%%0%dd" % (math.log10(nn) + 1)
        for i, epoch in enumerate(sweep_handler.get_epochs()):
            si = sweep_handler.get_sweep_information(epoch)
            nums = fmt % i
            r = flex.reflection_table.from_pickle(si.get_reflections())
            if len(set(r["id"]).difference(set([-1]))) > 1:
                raise ValueError("Only single-experiment tables expected")
            old_id = list(r.experiment_identifiers().keys())[0]
            exp_id = list(r.experiment_identifiers().values())[0]
            del r.experiment_identifiers()[old_id]
            r["id"].set_selected(r["id"] == old_id, i)
            r.experiment_identifiers()[i] = exp_id
            fname = os.path.join(
                self.get_working_directory(), "split_reflections_%s.pickle" % nums
            )
            r.as_pickle(fname)
            si.set_reflections(fname)
        return sweep_handler

    def assign_and_return_datasets(self, sweep_handler):
        """Assign unique identifiers to all integrated experiments & reflections,
        and set these in the sweep_information for each epoch."""
        experiments = []
        reflections = []
        for epoch in sweep_handler.get_epochs():
            si = sweep_handler.get_sweep_information(epoch)
            integrater = si.get_integrater()
            experiments.append(integrater.get_integrated_experiments())
            reflections.append(integrater.get_integrated_reflections())
        assigner = self.assign_dataset_identifiers(experiments, reflections)
        sweep_handler = self.split_experiments(
            assigner.get_output_experiments_filename(),
            assigner.get_output_reflections_filename(),
            sweep_handler,
        )
        return sweep_handler

    def dials_symmetry_indexer_jiffy(
        self, experiments, reflections, refiners, multisweep=False
    ):
        """A jiffy to centralise the interactions between dials.symmetry
        and the Indexer, multisweep edition."""
        # First check format of input against expected input
        assert len(experiments) == len(
            reflections
        ), """
Unequal number of experiments/reflections passed to dials_symmetry_indexer_jiffy"""
        if len(experiments) > 1:
            assert multisweep, """
Passing multple datasets to indexer_jiffy but not set multisweep=True"""

        probably_twinned = False
        reindex_initial = False

        symmetry_analyser = self.dials_symmetry_decide_pointgroup(
            experiments, reflections
        )

        possible = symmetry_analyser.get_possible_lattices()

        Debug.write("Possible lattices (dials.symmetry):")
        Debug.write(" ".join(possible))

        # all refiners contain the same indexer link, so any good here.
        correct_lattice, rerun_symmetry, need_to_return = decide_correct_lattice_using_refiner(
            possible, refiners[0]
        )

        if need_to_return and multisweep:
            if (
                PhilIndex.params.xia2.settings.integrate_p1
                and not PhilIndex.params.xia2.settings.reintegrate_correct_lattice
            ):
                need_to_return = False
                rerun_symmetry = True
            else:
                for refiner in refiners[1:]:
                    refiner.refiner_reset()

        if rerun_symmetry:
            # don't actually need to rerun, just set correct solution - this
            # call updates the relevant info in the Wrapper - but will need to reindex later
            symmetry_analyser.set_correct_lattice(correct_lattice)
            reindex_initial = True
            # rather than reindexing here, just set the reindex_inital and let the
            # scaler manage this as necessary

        Debug.write(
            "Symmetry analysis of %s" % " ".join(experiments) + " ".join(reflections)
        )

        pointgroup = symmetry_analyser.get_pointgroup()
        reindex_op = symmetry_analyser.get_reindex_operator()
        probably_twinned = symmetry_analyser.get_probably_twinned()

        reindexed_reflections = symmetry_analyser.get_output_reflections_filename()
        reindexed_experiments = symmetry_analyser.get_output_experiments_filename()

        Debug.write("Pointgroup: %s (%s)" % (pointgroup, reindex_op))

        return (
            pointgroup,
            reindex_op,
            need_to_return,
            probably_twinned,
            reindexed_reflections,
            reindexed_experiments,
            reindex_initial,
        )

    def dials_symmetry_decide_pointgroup(self, experiments, reflections):
        """Run the symmetry analyser and return it for later inspection."""
        symmetry_analyser = DialsSymmetry()
        symmetry_analyser.set_working_directory(self.get_working_directory())
        auto_logfiler(symmetry_analyser)

        FileHandler.record_log_file(
            "%s %s SYMMETRY" % (self._scalr_pname, self._scalr_xname),
            symmetry_analyser.get_log_file(),
        )

        for (exp, refl) in zip(experiments, reflections):
            symmetry_analyser.add_experiments(exp)
            symmetry_analyser.add_reflections(refl)
        symmetry_analyser.decide_pointgroup()

        return symmetry_analyser

    def reindex_jiffy(self, si, reindex_op):
        """Add data from si and reindex, setting back in si"""
        integrater = si.get_integrater()
        integrater.set_integrater_reindex_operator(
            reindex_op, reason="eliminated lattice"
        )
        integrater.set_output_format("pickle")
        _ = integrater.get_integrater_intensities()
        # ^ This will give us the reflections in the correct point group
        si.set_reflections(integrater.get_integrated_reflections())
        si.set_experiments(integrater.get_integrated_experiments())


def decide_correct_lattice_using_refiner(possible_lattices, refiner):
    """Use the refiner to determine which of the possible lattices is the
    correct one."""
    correct_lattice, rerun_symmetry, need_to_return = (None, False, False)
    for lattice in possible_lattices:
        state = refiner.set_refiner_asserted_lattice(lattice)
        if state == refiner.LATTICE_CORRECT:
            Debug.write("Agreed lattice %s" % lattice)
            correct_lattice = lattice
            break

        elif state == refiner.LATTICE_IMPOSSIBLE:
            Debug.write("Rejected lattice %s" % lattice)
            rerun_symmetry = True
            continue

        elif state == refiner.LATTICE_POSSIBLE:
            Debug.write("Accepted lattice %s, will reprocess" % lattice)
            need_to_return = True
            correct_lattice = lattice
            break

    if correct_lattice is None:
        correct_lattice = refiner.get_refiner_lattice()
        rerun_symmetry = True

        Debug.write("No solution found: assuming lattice from refiner")

    return correct_lattice, rerun_symmetry, need_to_return
