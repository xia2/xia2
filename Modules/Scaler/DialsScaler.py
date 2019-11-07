# An implementation of the scaler interface for dials.scale

from __future__ import absolute_import, division, print_function

import math
import os
from orderedset import OrderedSet

from xia2.Handlers.Files import FileHandler
from xia2.lib.bits import auto_logfiler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.SymmetryLib import sort_lattices
from xia2.Handlers.Streams import Chatter, Debug, Journal
from xia2.Handlers.CIF import CIF, mmCIF
from xia2.Modules.Scaler.CommonScaler import CommonScaler as Scaler
from xia2.Wrappers.Dials.Scale import DialsScale
from xia2.Wrappers.Dials.Merge import DialsMerge
from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory
from xia2.Modules.AnalyseMyIntensities import AnalyseMyIntensities
from xia2.Modules.Scaler.CCP4ScalerHelpers import (
    SweepInformationHandler,
    mosflm_B_matrix,
)
from xia2.Wrappers.Dials.Symmetry import DialsSymmetry
from xia2.Wrappers.Dials.Reindex import Reindex as DialsReindex
from xia2.Wrappers.Dials.AssignUniqueIdentifiers import DialsAssignIdentifiers
from xia2.Wrappers.Dials.SplitExperiments import SplitExperiments
from xia2.Wrappers.Dials.ExportMtz import ExportMtz
from xia2.Wrappers.Dials.TwoThetaRefine import TwoThetaRefine
from xia2.Handlers.Syminfo import Syminfo
from dxtbx.serialize import load
from dials.util.batch_handling import calculate_batch_offsets
from dials.util.export_mtz import match_wavelengths
from dials.array_family import flex
import dials.util.version
from cctbx.sgtbx import lattice_symmetry_group


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
        self._scaler.set_error_model(PhilIndex.params.dials.scale.error_model)
        self._scaler.set_partiality_cutoff(
            PhilIndex.params.dials.scale.partiality_threshold
        )

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

    def _do_multisweep_symmetry_analysis(self):
        refiners = []
        experiments = []
        reflections = []

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            integrater = si.get_integrater()
            experiments.append(integrater.get_integrated_experiments())
            reflections.append(integrater.get_integrated_reflections())
            refiners.append(integrater.get_integrater_refiner())

        Debug.write("Running multisweep dials.symmetry for %d sweeps" % len(refiners))
        (
            pointgroup,
            reindex_op,
            ntr,
            pt,
            reind_refl,
            reind_exp,
            reindex_initial,
        ) = self._dials_symmetry_indexer_jiffy(
            experiments, reflections, refiners, multisweep=True
        )

        FileHandler.record_temporary_file(reind_refl)
        FileHandler.record_temporary_file(reind_exp)
        return pointgroup, reindex_op, ntr, pt, reind_refl, reind_exp, reindex_initial

    def _multi_sweep_scale_prepare(self):
        need_to_return = False

        (
            pointgroup,
            reindex_op,
            ntr,
            _,
            reind_refl,
            reind_exp,
            reindex_initial,
        ) = self._do_multisweep_symmetry_analysis()
        if ntr:
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                si.get_integrater().integrater_reset_reindex_operator()
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            need_to_return = True
            return need_to_return
        else:
            self._scalr_likely_spacegroups = [pointgroup]
            if reindex_initial:
                self._helper.reindex_jiffy(si, pointgroup, reindex_op=reindex_op)
                # integrater reset reindex op and update in si.
            else:
                self._sweep_handler = self._helper.split_experiments(
                    reind_exp, reind_refl, self._sweep_handler
                )

        return need_to_return

    def _input_pointgroup_scale_prepare(self):
        # is this function completely pointless?
        # ---------- REINDEX ALL DATA TO CORRECT POINTGROUP ----------
        ####Redoing batches only seems to be in multi_sweep_idxing for CCP4A
        self._scalr_likely_spacegroups = [self._scalr_input_pointgroup]
        Debug.write("Using input pointgroup: %s" % self._scalr_input_pointgroup)
        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            self._helper.reindex_jiffy(si, self._scalr_input_pointgroup, "h,k,l")

    def _standard_scale_prepare(self):
        pointgroups = {}
        reindex_ops = {}
        probably_twinned = False
        need_to_return = False

        lattices = []
        # First check for the existence of multiple lattices. If only one
        # epoch, then this gives the necessary data for proceeding straight
        # to the point group check.
        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            intgr = si.get_integrater()
            experiment = intgr.get_integrated_experiments()
            reflections = intgr.get_integrated_reflections()
            refiner = intgr.get_integrater_refiner()

            (
                pointgroup,
                reindex_op,
                ntr,
                pt,
                _,
                __,
                ___,
            ) = self._dials_symmetry_indexer_jiffy(
                [experiment], [reflections], [refiner]
            )

            lattice = Syminfo.get_lattice(pointgroup)
            if lattice not in lattices:
                lattices.append(lattice)
            if ntr:
                si.get_integrater().integrater_reset_reindex_operator()
                need_to_return = True
            if pt:
                probably_twinned = True
            pointgroups[epoch] = pointgroup
            reindex_ops[epoch] = reindex_op
            Debug.write("Pointgroup: %s (%s)" % (pointgroup, reindex_op))

        if len(lattices) > 1:
            # Check consistency of lattices if more than one. If not, then
            # can proceed to straight to checking point group consistency
            # using the cached results.
            correct_lattice = sort_lattices(lattices)[0]
            Chatter.write("Correct lattice asserted to be %s" % correct_lattice)

            # transfer this information back to the indexers
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                refiner = si.get_integrater().get_integrater_refiner()
                _tup = (correct_lattice, si.get_sweep_name())

                state = refiner.set_refiner_asserted_lattice(correct_lattice)

                if state == refiner.LATTICE_CORRECT:
                    Chatter.write("Lattice %s ok for sweep %s" % _tup)
                elif state == refiner.LATTICE_IMPOSSIBLE:
                    raise RuntimeError("Lattice %s impossible for %s" % _tup)
                elif state == refiner.LATTICE_POSSIBLE:
                    Chatter.write("Lattice %s assigned for sweep %s" % _tup)
                    need_to_return = True

        if need_to_return:
            return need_to_return

        need_to_return = False

        pointgroup_set = {pointgroups[e] for e in pointgroups}

        if len(pointgroup_set) > 1 and not probably_twinned:
            raise RuntimeError(
                "non uniform pointgroups: %s" % str(list(pointgroup_set))
            )

        if len(pointgroup_set) > 1:
            Debug.write(
                "Probably twinned, pointgroups: %s"
                % " ".join(p.replace(" ", "") for p in list(pointgroup_set))
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
        self._scalr_likely_spacegroups = [overall_pointgroup]
        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            self._helper.reindex_jiffy(si, overall_pointgroup, reindex_ops[epoch])
        return need_to_return

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
            _, xname, dname = si.get_project_info()
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

        # try to reproduce what CCP4ScalerA is doing

        # first assign identifiers to avoid dataset-id collisions
        # Idea is that this should be called anytime you get data anew from the
        # integrater, to intercept and assign unique ids, then set in the
        # sweep_information (si) and always use si.set_reflections/
        # si.get_reflections as we process.

        # self._sweep_handler = self._helper.assign_and_return_datasets(
        #    self._sweep_handler
        # ) symmetry now sorts out identifiers.

        need_to_return = False

        if self._scalr_input_pointgroup:
            self._input_pointgroup_scale_prepare()
        elif (
            len(self._sweep_handler.get_epochs()) > 1
            and PhilIndex.params.xia2.settings.multi_sweep_indexing
        ):
            need_to_return = self._multi_sweep_scale_prepare()
        else:
            need_to_return = self._standard_scale_prepare()

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        ### After this point, point group is good and only need to
        ### reindex to consistent setting. Don't need to call back to the
        ### integator, just use the data in the sweep info.

        # First work out if we're going to reindex against external reference
        param = PhilIndex.params.xia2.settings.scale
        using_external_references = False
        reference_refl = None
        reference_expt = None
        if param.reference_reflection_file:
            if not param.reference_experiment_file:
                Chatter.write(
                    """
No DIALS reference experiments file provided, reference reflection file will
not be used. Reference mtz files for reindexing not currently supported for
pipeline=dials (supported for pipeline=dials-aimless).
"""
                )
            else:
                reference_refl = param.reference_reflection_file
                reference_expt = param.reference_experiment_file
                using_external_references = True
                Debug.write("Using reference reflections %s" % reference_refl)
                Debug.write("Using reference experiments %s" % reference_expt)

        if len(self._sweep_handler.get_epochs()) > 1:
            if PhilIndex.params.xia2.settings.unify_setting:
                self.unify_setting()

            if PhilIndex.params.xia2.settings.use_brehm_diederichs:
                self.brehm_diederichs_reindexing()
            # If not using Brehm-deidrichs reindexing, set reference as first
            # sweep, unless using external reference.
            elif not using_external_references:
                Debug.write("First sweep will be used as reference for reindexing")
                first = self._sweep_handler.get_epochs()[0]
                si = self._sweep_handler.get_sweep_information(first)
                reference_expt = si.get_experiments()
                reference_refl = si.get_reflections()

        # Now reindex to be consistent with first dataset - run reindex on each
        # dataset with reference (unless did brehm diederichs and didn't supply
        # a reference file)

        if reference_refl and reference_expt:
            exp = load.experiment_list(reference_expt)
            reference_cell = exp[0].crystal.get_unit_cell().parameters()

            # ---------- REINDEX TO CORRECT (REFERENCE) SETTING ----------
            Chatter.write("Reindexing all datasets to common reference")

            if using_external_references:
                epochs = self._sweep_handler.get_epochs()
            else:
                epochs = self._sweep_handler.get_epochs()[1:]
            for epoch in epochs:
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
                reindexer.set_reference_filename(reference_expt)
                reindexer.set_reference_reflections(reference_refl)
                reindexer.set_indexed_filename(si.get_reflections())
                reindexer.set_experiments_filename(si.get_experiments())
                reindexer.run()

                # At this point, CCP4ScalerA would reset in integrator so that
                # the integrater calls reindex, no need to do that here as
                # have access to the files and will never need to reintegrate.

                si.set_reflections(reindexer.get_reindexed_reflections_filename())
                si.set_experiments(reindexer.get_reindexed_experiments_filename())

                # FIXME how to get some indication of the reindexing used?

                exp = load.experiment_list(
                    reindexer.get_reindexed_experiments_filename()
                )
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
                            % (reference_expt, si.get_reflections())
                        )

        # Now make sure all batches ok before finish preparing
        # This should be made safer, currently after dials.scale there is no
        # concept of 'batch', dials.export uses the calculate_batch_offsets
        # to assign batches, giving the same result as below.

        experiments_to_rebatch = []
        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            experiment = si.get_experiments()
            experiments_to_rebatch.append(load.experiment_list(experiment)[0])
        offsets = calculate_batch_offsets(experiments_to_rebatch)

        for i, epoch in enumerate(self._sweep_handler.get_epochs()):
            si = self._sweep_handler.get_sweep_information(epoch)
            r = si.get_batch_range()
            si.set_batch_offset(offsets[i])
            si.set_batches([r[0] + offsets[i], r[1] + offsets[i]])

    def _scale(self):
        """Perform all of the operations required to deliver the scaled
        data."""
        sweep_infos = [
            self._sweep_handler.get_sweep_information(e)
            for e in self._sweep_handler.get_epochs()
        ]

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

        ### Set the parameters and datafiles for dials.scale

        self._scaler = DialsScale()
        self._scaler = self._updated_dials_scaler()

        if self._scaled_experiments and self._scaled_reflections:
            # going to continue-where-left-off
            self._scaler.add_experiments_json(self._scaled_experiments)
            self._scaler.add_reflections_file(self._scaled_reflections)
        else:
            for si in sweep_infos:
                self._scaler.add_experiments_json(si.get_experiments())
                self._scaler.add_reflections_file(si.get_reflections())

        self._scalr_scaled_reflection_files = {}
        self._scalr_scaled_reflection_files["mtz_unmerged"] = {}
        self._scalr_scaled_reflection_files["mtz"] = {}

        ### Set the resolution limit if applicable

        user_resolution_limits = {}
        highest_resolution = 100.0
        for si in sweep_infos:
            dname = si.get_project_info()[2]
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
                d_min, _ = self._scalr_resolution_limits[(dname, sname)]
                if d_min < highest_resolution:
                    highest_resolution = d_min
        if highest_resolution < 99.9:
            self._scaler.set_resolution(d_min=highest_resolution)

        ### Setup final job details and run scale

        self._scaler.set_working_directory(self.get_working_directory())
        auto_logfiler(self._scaler)
        FileHandler.record_log_file(
            "%s %s SCALE" % (self._scalr_pname, self._scalr_xname),
            self._scaler.get_log_file(),
        )
        self._scaler.scale()
        FileHandler.record_html_file(
            "%s %s SCALE" % (self._scalr_pname, self._scalr_xname),
            self._scaler.get_html(),
        )
        self._scaled_experiments = self._scaler.get_scaled_experiments()
        self._scaled_reflections = self._scaler.get_scaled_reflections()

        # make it so that only scaled.expt and scaled.refl are
        # the files that dials.scale knows about, so that if scale is called again,
        # scaling resumes from where it left off.
        self._scaler.clear_datafiles()

        ### Calculate the resolution limit and set done False if applicable

        highest_suggested_resolution = self.assess_resolution_limits(
            hklin=None,
            user_resolution_limits=user_resolution_limits,
            use_misigma=False,
            reflections=self._scaled_reflections,
            experiments=self._scaled_experiments,
        )

        if not self.get_scaler_done():
            # reset for when resolution limit applied
            Debug.write("Returning as scaling not finished...")
            return

        ### Want to do space group check after scaling. So run dials.symmetry
        ### with absences only before exporting merged and unmerged files
        ### again in correct s.g.
        if not PhilIndex.params.xia2.settings.small_molecule:
            Chatter.banner("Systematic absences check")
            symmetry = DialsSymmetry()
            symmetry.set_experiments_filename(self._scaled_experiments)
            symmetry.set_reflections_filename(self._scaled_reflections)
            symmetry.set_working_directory(self.get_working_directory())
            symmetry.set_mode_absences_only()
            auto_logfiler(symmetry)
            symmetry.decide_pointgroup()  # bad name - actually running absences here

            self._scaled_experiments = symmetry.get_output_experiments_filename()

            sg = load.experiment_list(self._scaled_experiments)[
                0
            ].crystal.get_space_group()
            Chatter.write("Most likely space group: %s" % sg.info())
            self._scalr_likely_spacegroups = [sg.type().lookup_symbol()]

        FileHandler.record_more_data_file(
            "%s %s scaled" % (self._scalr_pname, self._scalr_xname),
            self._scaled_experiments,
        )
        FileHandler.record_more_data_file(
            "%s %s scaled" % (self._scalr_pname, self._scalr_xname),
            self._scaled_reflections,
        )

        ### Now export and merge so that mtz files in correct space group.

        ### For MAD case, need to generate individual merged and unmerged mtz
        ### files. First split experiments on wavelength, then run dials.export
        ### and dials.merge on each

        # Find number of dnames (i.e. number of wavelengths)
        dnames_set = OrderedSet()
        experiments = load.experiment_list(self._scaled_experiments)
        wavelengths = flex.double(
            match_wavelengths(experiments)
        )  # in experiments order
        for si in sweep_infos:
            dnames_set.add(
                si.get_project_info()[2]
            )  # sweep info in same order as experiments
        assert len(wavelengths) == len(dnames_set)

        scaled_unmerged_mtz_path = os.path.join(
            self.get_working_directory(),
            "%s_%s_scaled_unmerged.mtz" % (self._scalr_pname, self._scalr_xname),
        )

        if len(dnames_set) > 1:
            self._scalr_scaled_refl_files = {}
            Debug.write("Splitting experiments by wavelength")
            # first split by wavelength
            splitter = SplitExperiments()
            splitter.add_experiments(self._scaled_experiments)
            splitter.add_reflections(self._scaled_reflections)
            splitter.set_by_wavelength(True)
            splitter.set_working_directory(self.get_working_directory())
            auto_logfiler(splitter)
            splitter.run()

            nn = len(dnames_set)
            fmt = "%%0%dd" % (math.log10(nn) + 1)

            wl_sort = flex.sort_permutation(wavelengths)
            sorted_dnames_by_wl = [dnames_set[i] for i in wl_sort]

            for i, dname in enumerate(sorted_dnames_by_wl):
                # need to sort by wavelength from low to high
                nums = fmt % i
                exporter = ExportMtz()
                exporter.set_working_directory(self.get_working_directory())
                expt_name = os.path.join(
                    self.get_working_directory(), "split_%s.expt" % nums
                )
                refl_name = os.path.join(
                    self.get_working_directory(), "split_%s.refl" % nums
                )
                exporter.set_experiments_filename(expt_name)
                exporter.set_reflections_filename(refl_name)
                exporter.set_intensity_choice("scale")
                exporter.set_partiality_threshold(
                    PhilIndex.params.dials.scale.partiality_threshold
                )  # 0.4 default
                auto_logfiler(exporter)
                mtz_filename = os.path.join(
                    self.get_working_directory(),
                    scaled_unmerged_mtz_path.rstrip(".mtz") + "_%s.mtz" % dname,
                )
                exporter.set_mtz_filename(mtz_filename)
                self._scalr_scaled_reflection_files["mtz_unmerged"][
                    dname
                ] = mtz_filename

                Debug.write("Exporting %s" % mtz_filename)
                exporter.run()
                FileHandler.record_data_file(mtz_filename)

                merger = DialsMerge()  # merge but don't truncate
                merger.set_working_directory(self.get_working_directory())
                merger.set_experiments_filename(expt_name)
                merger.set_reflections_filename(refl_name)
                merger.set_project_name(self._scalr_pname)
                merger.set_crystal_names(self._scalr_xname)
                merger.set_dataset_names(dname)
                merger.set_partiality_threshold(
                    PhilIndex.params.dials.scale.partiality_threshold
                )
                auto_logfiler(merger)
                mtz_filename = os.path.join(
                    self.get_working_directory(),
                    "%s_%s_scaled_%s.mtz"
                    % (self._scalr_pname, self._scalr_xname, dname),
                )
                self._scalr_scaled_refl_files[dname] = mtz_filename
                self._scalr_scaled_reflection_files["mtz"][dname] = mtz_filename
                merger.set_mtz_filename(mtz_filename)

                Debug.write("Merging %s" % mtz_filename)
                merger.run()
                FileHandler.record_data_file(mtz_filename)

        ### For non-MAD case, run dials.export and dials.merge on scaled data.
        else:
            exporter = ExportMtz()
            exporter.set_working_directory(self.get_working_directory())
            exporter.set_experiments_filename(self._scaled_experiments)
            exporter.set_reflections_filename(self._scaled_reflections)
            exporter.set_intensity_choice("scale")
            exporter.set_partiality_threshold(
                PhilIndex.params.dials.scale.partiality_threshold
            )  # 0.4 default
            auto_logfiler(exporter)
            exporter.set_mtz_filename(scaled_unmerged_mtz_path)

            Debug.write("Exporting %s" % scaled_unmerged_mtz_path)
            exporter.run()

            self._scalr_scaled_reflection_files["mtz_unmerged"] = {
                dnames_set[0]: scaled_unmerged_mtz_path
            }

            FileHandler.record_data_file(scaled_unmerged_mtz_path)

            merger = DialsMerge()
            merger.set_working_directory(self.get_working_directory())
            merger.set_experiments_filename(self._scaled_experiments)
            merger.set_reflections_filename(self._scaled_reflections)
            merger.set_project_name(self._scalr_pname)
            merger.set_crystal_names(self._scalr_xname)
            merger.set_dataset_names(dnames_set[0])
            merger.set_partiality_threshold(
                PhilIndex.params.dials.scale.partiality_threshold
            )
            auto_logfiler(merger)
            mtz_filename = os.path.join(
                self.get_working_directory(),
                "%s_%s_scaled.mtz" % (self._scalr_pname, self._scalr_xname),
            )
            self._scalr_scaled_refl_files[dnames_set[0]] = mtz_filename
            self._scalr_scaled_reflection_files["mtz"][dnames_set[0]] = mtz_filename
            merger.set_mtz_filename(mtz_filename)

            Debug.write("Merging %s" % mtz_filename)
            merger.run()
            FileHandler.record_data_file(mtz_filename)

        if PhilIndex.params.xia2.settings.merging_statistics.source == "cctbx":
            for key in self._scalr_scaled_refl_files:
                stats = self._compute_scaler_statistics(
                    self._scalr_scaled_reflection_files["mtz_unmerged"][key],
                    selected_band=(highest_suggested_resolution, None),
                    wave=key,
                )
                self._scalr_statistics[
                    (self._scalr_pname, self._scalr_xname, key)
                ] = stats

        # Run twotheta refine
        self._update_scaled_unit_cell_from_scaled_data()

    def _update_scaled_unit_cell_from_scaled_data(self):

        params = PhilIndex.params
        fast_mode = params.dials.fast_mode
        if (
            params.xia2.settings.integrater == "dials"
            and not fast_mode
            and params.xia2.settings.scale.two_theta_refine
        ):

            Chatter.banner("Unit cell refinement")

            # Collect a list of all sweeps, grouped by project, crystal, wavelength
            groups_list = []
            groups = {}
            self._scalr_cell_dict = {}
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                pi = "_".join(si.get_project_info())  # pname, xname, dname
                groups_list.append(pi)

            p4p_file = os.path.join(
                self.get_working_directory(),
                "%s_%s.p4p" % (self._scalr_pname, self._scalr_xname),
            )
            if len(set(groups_list)) > 1:
                # need to split up experiments and reflections
                self._sweep_handler = self._helper.split_experiments(
                    self._scaled_experiments,
                    self._scaled_reflections,
                    self._sweep_handler,
                )
                for epoch in self._sweep_handler.get_epochs():
                    si = self._sweep_handler.get_sweep_information(epoch)
                    pi = "_".join(si.get_project_info())  # pname, xname, dname
                    groups[pi] = groups.get(pi, []) + [
                        (si.get_experiments(), si.get_reflections())
                    ]  # if key exists, add another 2-tuple to the list.
                for pi in groups:
                    # Run twothetarefine on each group
                    tt_grouprefiner = TwoThetaRefine()
                    tt_grouprefiner.set_working_directory(self.get_working_directory())
                    auto_logfiler(tt_grouprefiner)
                    args = list(zip(*groups[pi]))
                    tt_grouprefiner.set_experiments(args[0])
                    tt_grouprefiner.set_reflection_files(args[1])
                    tt_grouprefiner.set_output_p4p(p4p_file)
                    tt_grouprefiner.run()
                    Chatter.write(
                        "%s: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
                        % tuple(
                            ["".join(pi.split("_")[2:])]
                            + list(tt_grouprefiner.get_unit_cell())
                        )
                    )
                    self._scalr_cell_dict[pi] = (
                        tt_grouprefiner.get_unit_cell(),
                        tt_grouprefiner.get_unit_cell_esd(),
                        tt_grouprefiner.import_cif(),
                        tt_grouprefiner.import_mmcif(),
                    )

                    cif_in = tt_grouprefiner.import_cif()
                    cif_out = CIF.get_block(pi)
                    for key in sorted(cif_in.keys()):
                        cif_out[key] = cif_in[key]
                    mmcif_in = tt_grouprefiner.import_mmcif()
                    mmcif_out = mmCIF.get_block(pi)
                    for key in sorted(mmcif_in.keys()):
                        mmcif_out[key] = mmcif_in[key]

            # now do two theta refine on combined scaled data.
            tt_refiner = TwoThetaRefine()
            tt_refiner.set_working_directory(self.get_working_directory())
            auto_logfiler(tt_refiner)
            tt_refiner.set_experiments([self._scaled_experiments])
            tt_refiner.set_reflection_files([self._scaled_reflections])  # needs a list
            tt_refiner.set_output_p4p(p4p_file)
            tt_refiner.run()

            self._scalr_cell = tt_refiner.get_unit_cell()
            Chatter.write(
                "Overall: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
                % tt_refiner.get_unit_cell()
            )
            self._scalr_cell_esd = tt_refiner.get_unit_cell_esd()
            cif_in = tt_refiner.import_cif()
            mmcif_in = tt_refiner.import_mmcif()

            if params.xia2.settings.small_molecule:
                FileHandler.record_data_file(p4p_file)

            cif_out = CIF.get_block("xia2")
            mmcif_out = mmCIF.get_block("xia2")
            cif_out["_computing_cell_refinement"] = mmcif_out[  # pylint: disable=E1137
                "_computing.cell_refinement"
            ] = ("DIALS 2theta refinement, %s" % dials.util.version.dials_version())
            for key in sorted(cif_in.keys()):
                cif_out[key] = cif_in[key]
            for key in sorted(mmcif_in.keys()):
                mmcif_out[key] = mmcif_in[key]

            Debug.write("Unit cell obtained by two-theta refinement")

        else:
            ami = AnalyseMyIntensities()
            ami.set_working_directory(self.get_working_directory())

            average_unit_cell, _ = ami.compute_average_cell(
                [
                    self._scalr_scaled_refl_files[key]
                    for key in self._scalr_scaled_refl_files
                ]
            )

            Debug.write("Computed average unit cell (will use in all files)")
            self._scalr_cell = average_unit_cell
            self._scalr_cell_esd = None

            # Write average unit cell to .cif
            cif_out = CIF.get_block("xia2")
            cif_out[  # pylint: disable=E1137
                "_computing_cell_refinement"
            ] = "AIMLESS averaged unit cell"
            for cell, cifname in zip(
                self._scalr_cell,
                [
                    "length_a",
                    "length_b",
                    "length_c",
                    "angle_alpha",
                    "angle_beta",
                    "angle_gamma",
                ],
            ):
                cif_out["_cell_%s" % cifname] = cell  # pylint: disable=E1137

        Debug.write("%7.3f %7.3f %7.3f %7.3f %7.3f %7.3f" % self._scalr_cell)

    def apply_reindex_operator_to_sweep_info(self, si, reindex_operator, reason):
        """Use a reindex operator to reindex the data.

        Take the data from the sweep info, reindex using
        dials.reindex, and set the new data into the si.
        """
        reindexer = DialsReindex()
        reindexer.set_working_directory(self.get_working_directory())
        auto_logfiler(reindexer)

        reindexer.set_indexed_filename(si.get_reflections())
        reindexer.set_experiments_filename(si.get_experiments())
        reindexer.set_cb_op(reindex_operator)

        reindexer.run()

        si.set_reflections(reindexer.get_reindexed_reflections_filename())
        si.set_experiments(reindexer.get_reindexed_experiments_filename())

        Debug.write(
            "Reindexed with operator %s, reason is %s" % (reindex_operator, reason)
        )

    def _dials_symmetry_indexer_jiffy(
        self, experiments, reflections, refiners, multisweep=False
    ):
        return self._helper.dials_symmetry_indexer_jiffy(
            experiments, reflections, refiners, multisweep
        )

    def get_UBlattsymm_from_sweep_info(self, sweep_info):
        """Calculate U, B and lattice symmetry from experiment."""
        expt = load.experiment_list(sweep_info.get_experiments())[0]
        uc = expt.crystal.get_unit_cell()
        umatrix = expt.crystal.get_U()
        lattice_symm = lattice_symmetry_group(uc, max_delta=0.0)
        return tuple(umatrix), mosflm_B_matrix(uc), lattice_symm

    def get_mtz_data_from_sweep_info(self, sweep_info):
        """Get the data in mtz form.

        Need to run dials.export to convert the data from experiment list
        and reflection table to mtz form."""
        return self.export_to_mtz(sweep_info)

    def export_to_mtz(self, sweep_info):
        """Export to mtz, using dials.integrate phil params"""
        params = PhilIndex.params.dials.integrate
        export = ExportMtz()
        export.set_working_directory(self.get_working_directory())
        export.set_experiments_filename(sweep_info.get_experiments())
        export.set_reflections_filename(sweep_info.get_reflections())
        export.set_combine_partials(params.combine_partials)
        export.set_partiality_threshold(params.partiality_threshold)
        if len(sweep_info.get_batches()) == 1:
            export.set_partiality_threshold(0.1)
        if (
            len(sweep_info.get_batches()) == 1
            or PhilIndex.params.dials.fast_mode
            or not PhilIndex.params.xia2.settings.integration.profile_fitting
        ):
            # With no profiles available have to rely on summation alone
            export.set_intensity_choice("sum")

        auto_logfiler(export, "EXPORTMTZ")
        mtz_filename = os.path.join(
            self.get_working_directory(), "%s.mtz" % sweep_info.get_sweep_name()
        )
        export.set_mtz_filename(mtz_filename)
        export.run()
        return mtz_filename


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
                os.path.join(self.get_working_directory(), "split_%s.refl" % nums)
            )
            si.set_experiments(
                os.path.join(self.get_working_directory(), "split_%s.expt" % nums)
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
            r = flex.reflection_table.from_file(si.get_reflections())
            if len(set(r["id"]).difference({-1})) > 1:
                raise ValueError("Only single-experiment tables expected")
            old_id = list(r.experiment_identifiers().keys())[0]
            exp_id = list(r.experiment_identifiers().values())[0]
            del r.experiment_identifiers()[old_id]
            r["id"].set_selected(r["id"] == old_id, i)
            r.experiment_identifiers()[i] = exp_id
            fname = os.path.join(self.get_working_directory(), "split_%s.refl" % nums)
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
        (
            correct_lattice,
            rerun_symmetry,
            need_to_return,
        ) = decide_correct_lattice_using_refiner(possible, refiners[0])

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

    def reindex_jiffy(self, si, pointgroup, reindex_op):
        """Add data from si and reindex, setting back in si"""
        integrater = si.get_integrater()
        integrater.set_integrater_spacegroup_number(
            Syminfo.spacegroup_name_to_number(pointgroup)
        )
        integrater.set_integrater_reindex_operator(
            reindex_op, reason="setting point group"
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
