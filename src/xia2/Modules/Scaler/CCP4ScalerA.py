# An implementation of the Scaler interface using CCP4 programs and Aimless.


import copy
import logging
import math
import os
import re

from xia2.Handlers.CIF import CIF, mmCIF
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Syminfo import Syminfo
from xia2.lib.bits import is_mtz_file, nifty_power_of_ten, transpose_loggraph
from xia2.lib.SymmetryLib import sort_lattices
from xia2.Modules import MtzUtils
from xia2.Modules.Scaler.CCP4ScalerHelpers import (
    CCP4ScalerHelper,
    SweepInformationHandler,
    _prepare_pointless_hklin,
    ersatz_resolution,
    get_umat_bmat_lattice_symmetry_from_mtz,
)
from xia2.Modules.Scaler.CommonScaler import CommonScaler as Scaler
from xia2.Modules.Scaler.rebatch import rebatch
from xia2.Toolkit.AimlessSurface import (
    evaluate_1degree,
    generate_map,
    scrape_coefficients,
)
from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory

logger = logging.getLogger("xia2.Modules.Scaler.CCP4ScalerA")


class CCP4ScalerA(Scaler):
    """An implementation of the Scaler interface using CCP4 programs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._sweep_handler = None

        self._scalr_scaled_refl_files = {}
        self._wavelengths_in_order = []

        # flags to keep track of the corrections we will be applying

        model = PhilIndex.params.xia2.settings.scale.model
        self._scalr_correct_absorption = "absorption" in model
        self._scalr_correct_decay = "decay" in model
        self._scalr_corrections = True

        # useful handles...!

        self._prepared_reflections = None

        self._reference = None

        self._factory = CCP4Factory()
        self._helper = CCP4ScalerHelper()

    # overloaded from the Scaler interface... to plumb in the factory

    def to_dict(self):
        obj = super().to_dict()
        if self._sweep_handler is not None:
            obj["_sweep_handler"] = self._sweep_handler.to_dict()
        obj["_prepared_reflections"] = self._prepared_reflections
        return obj

    @classmethod
    def from_dict(cls, obj):
        return_obj = super().from_dict(obj)
        if return_obj._sweep_handler is not None:
            return_obj._sweep_handler = SweepInformationHandler.from_dict(
                return_obj._sweep_handler
            )
        return_obj._prepared_reflections = obj["_prepared_reflections"]
        return return_obj

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        self._helper.set_working_directory(working_directory)

    # this is an overload from the factory - it returns Aimless wrapper set up
    # with the desired corrections

    def _updated_aimless(self):
        """Generate a correctly configured Aimless..."""

        aimless = None

        params = PhilIndex.params.ccp4.aimless

        if not self._scalr_corrections:
            aimless = self._factory.Aimless()
        else:
            aimless = self._factory.Aimless(
                absorption_correction=self._scalr_correct_absorption,
                decay_correction=self._scalr_correct_decay,
            )

        aimless.set_mode(PhilIndex.params.xia2.settings.scale.scales)

        aimless.set_spacing(params.rotation.spacing)
        aimless.set_bfactor(brotation=params.brotation.spacing)

        if PhilIndex.params.xia2.settings.small_molecule:
            aimless.set_spacing(15.0)
            aimless.set_bfactor(
                bfactor=PhilIndex.params.xia2.settings.small_molecule_bfactor
            )

        aimless.set_surface_tie(params.surface_tie)
        aimless.set_surface_link(params.surface_link)
        if params.secondary.frame == "camera":
            secondary = "secondary"
        else:
            secondary = "absorption"
        lmax = params.secondary.lmax
        aimless.set_secondary(secondary, lmax)

        if PhilIndex.params.xia2.settings.multi_crystal:
            aimless.set_surface_link(False)

        # if profile fitting off use summation intensities
        if PhilIndex.params.xia2.settings.integration.profile_fitting:
            aimless.set_intensities(params.intensities)
        else:
            aimless.set_intensities("summation")

        return aimless

    def _pointless_indexer_jiffy(self, hklin, refiner):
        return self._helper.pointless_indexer_jiffy(hklin, refiner)

    def _pointless_indexer_multisweep(self, hklin, refiners):
        return self._helper.pointless_indexer_multisweep(hklin, refiners)

    def _scale_prepare(self):
        """Perform all of the preparation required to deliver the scaled
        data. This should sort together the reflection files, ensure that
        they are correctly indexed (via pointless) and generally tidy
        things up."""

        # acknowledge all of the programs we are about to use...

        Citations.cite("pointless")
        Citations.cite("aimless")
        Citations.cite("ccp4")

        # ---------- GATHER ----------

        self._sweep_handler = SweepInformationHandler(self._scalr_integraters)

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()

            exclude_sweep = False

            for sweep in PhilIndex.params.xia2.settings.sweep:
                if sweep.id == sname and sweep.exclude:
                    exclude_sweep = True
                    break

            if exclude_sweep:
                self._sweep_handler.remove_epoch(epoch)
                logger.debug("Excluding sweep %s", sname)
            else:
                logger.debug("%-30s %s/%s/%s", "adding data from:", xname, dname, sname)

        # gather data for all images which belonged to the parent
        # crystal - allowing for the fact that things could go wrong
        # e.g. epoch information not available, exposure times not in
        # headers etc...

        for e in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(e)
            assert is_mtz_file(si.get_reflections()), repr(si.get_reflections())

        p, x = self._sweep_handler.get_project_info()
        self._scalr_pname = p
        self._scalr_xname = x

        # verify that the lattices are consistent, calling eliminate if
        # they are not N.B. there could be corner cases here

        need_to_return = False

        multi_sweep_indexing = PhilIndex.params.xia2.settings.multi_sweep_indexing

        # START OF if more than one epoch
        if len(self._sweep_handler.get_epochs()) > 1:

            # if we have multi-sweep-indexing going on then logic says all should
            # share common lattice & UB definition => this is not used here?

            # START OF if multi_sweep indexing and not input pg
            if multi_sweep_indexing and not self._scalr_input_pointgroup:
                pointless_hklins = []

                max_batches = 0
                for epoch in self._sweep_handler.get_epochs():
                    si = self._sweep_handler.get_sweep_information(epoch)
                    hklin = si.get_reflections()

                    batches = MtzUtils.batches_from_mtz(hklin)
                    if 1 + max(batches) - min(batches) > max_batches:
                        max_batches = max(batches) - min(batches) + 1

                logger.debug("Biggest sweep has %d batches", max_batches)
                max_batches = nifty_power_of_ten(max_batches)

                counter = 0

                refiners = []

                for epoch in self._sweep_handler.get_epochs():
                    si = self._sweep_handler.get_sweep_information(epoch)
                    hklin = si.get_reflections()
                    integrater = si.get_integrater()
                    refiner = integrater.get_integrater_refiner()
                    refiners.append(refiner)

                    hklin = self._prepare_pointless_hklin(
                        hklin, si.get_integrater().get_phi_width()
                    )

                    hklout = os.path.join(
                        self.get_working_directory(),
                        "%s_%s_%s_%s_prepointless.mtz"
                        % (pname, xname, dname, si.get_sweep_name()),
                    )

                    # we will want to delete this one exit
                    FileHandler.record_temporary_file(hklout)

                    first_batch = min(si.get_batches())
                    si.set_batch_offset(counter * max_batches - first_batch + 1)

                    rebatch(
                        hklin,
                        hklout,
                        first_batch=counter * max_batches + 1,
                        pname=pname,
                        xname=xname,
                        dname=dname,
                    )

                    pointless_hklins.append(hklout)

                    # update the counter & recycle
                    counter += 1

                    # SUMMARY - have added all sweeps to pointless_hklins

                s = self._factory.Sortmtz()

                pointless_hklin = os.path.join(
                    self.get_working_directory(),
                    "%s_%s_prepointless_sorted.mtz"
                    % (self._scalr_pname, self._scalr_xname),
                )

                s.set_hklout(pointless_hklin)

                for hklin in pointless_hklins:
                    s.add_hklin(hklin)

                s.sort()

                # FIXME xia2-51 in here look at running constant scaling on the
                # pointless hklin to put the runs on the same scale. Ref=[A]

                pointless_const = os.path.join(
                    self.get_working_directory(),
                    "%s_%s_prepointless_const.mtz"
                    % (self._scalr_pname, self._scalr_xname),
                )
                FileHandler.record_temporary_file(pointless_const)

                aimless_const = self._factory.Aimless()
                aimless_const.set_hklin(pointless_hklin)
                aimless_const.set_hklout(pointless_const)
                aimless_const.const()

                pointless_const = os.path.join(
                    self.get_working_directory(),
                    "%s_%s_prepointless_const_unmerged.mtz"
                    % (self._scalr_pname, self._scalr_xname),
                )
                FileHandler.record_temporary_file(pointless_const)
                pointless_hklin = pointless_const

                # FIXME xia2-51 in here need to pass all refiners to ensure that the
                # information is passed back to all of them not just the last one...
                logger.debug(
                    "Running multisweep pointless for %d sweeps", len(refiners)
                )
                pointgroup, reindex_op, ntr, pt = self._pointless_indexer_multisweep(
                    pointless_hklin, refiners
                )

                logger.debug("X1698: %s: %s", pointgroup, reindex_op)

                lattices = [Syminfo.get_lattice(pointgroup)]

                for epoch in self._sweep_handler.get_epochs():
                    si = self._sweep_handler.get_sweep_information(epoch)
                    intgr = si.get_integrater()
                    hklin = si.get_reflections()
                    refiner = intgr.get_integrater_refiner()

                    if ntr:
                        intgr.integrater_reset_reindex_operator()
                        need_to_return = True

                # SUMMARY - added all sweeps together into an mtz, ran
                # _pointless_indexer_multisweep on this, made a list of one lattice
                # and potentially reset reindex op?
            # END OF if multi_sweep indexing and not input pg

            # START OF if not multi_sweep, or input pg given
            else:
                lattices = []

                for epoch in self._sweep_handler.get_epochs():

                    si = self._sweep_handler.get_sweep_information(epoch)
                    intgr = si.get_integrater()
                    hklin = si.get_reflections()
                    refiner = intgr.get_integrater_refiner()

                    if self._scalr_input_pointgroup:
                        pointgroup = self._scalr_input_pointgroup
                        reindex_op = "h,k,l"
                        ntr = False

                    else:
                        pointless_hklin = self._prepare_pointless_hklin(
                            hklin, si.get_integrater().get_phi_width()
                        )

                        pointgroup, reindex_op, ntr, pt = self._pointless_indexer_jiffy(
                            pointless_hklin, refiner
                        )

                        logger.debug("X1698: %s: %s", pointgroup, reindex_op)

                    lattice = Syminfo.get_lattice(pointgroup)

                    if lattice not in lattices:
                        lattices.append(lattice)

                    if ntr:
                        intgr.integrater_reset_reindex_operator()
                        need_to_return = True
                # SUMMARY do pointless_indexer on each sweep, get lattices and make a list
                # of unique lattices, potentially reset reindex op.
            # END OF if not multi_sweep, or input pg given

            # SUMMARY - still within if more than one epoch, now have a list of number
            # of lattices

            # START OF if multiple-lattices
            if len(lattices) > 1:

                # why not using pointless indexer jiffy??!

                correct_lattice = sort_lattices(lattices)[0]

                logger.info("Correct lattice asserted to be %s", correct_lattice)

                # transfer this information back to the indexers
                for epoch in self._sweep_handler.get_epochs():

                    si = self._sweep_handler.get_sweep_information(epoch)
                    refiner = si.get_integrater().get_integrater_refiner()
                    sname = si.get_sweep_name()

                    state = refiner.set_refiner_asserted_lattice(correct_lattice)

                    if state == refiner.LATTICE_CORRECT:
                        logger.info(
                            "Lattice %s ok for sweep %s", correct_lattice, sname
                        )
                    elif state == refiner.LATTICE_IMPOSSIBLE:
                        raise RuntimeError(
                            f"Lattice {correct_lattice} impossible for {sname}"
                        )
                    elif state == refiner.LATTICE_POSSIBLE:
                        logger.info(
                            "Lattice %s assigned for sweep %s", correct_lattice, sname
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
            pointless_hklins = []

            max_batches = 0
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                hklin = si.get_reflections()

                batches = MtzUtils.batches_from_mtz(hklin)
                if 1 + max(batches) - min(batches) > max_batches:
                    max_batches = max(batches) - min(batches) + 1

            logger.debug("Biggest sweep has %d batches", max_batches)
            max_batches = nifty_power_of_ten(max_batches)

            counter = 0

            refiners = []

            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)
                hklin = si.get_reflections()
                integrater = si.get_integrater()
                refiner = integrater.get_integrater_refiner()
                refiners.append(refiner)

                hklin = self._prepare_pointless_hklin(
                    hklin, si.get_integrater().get_phi_width()
                )

                hklout = os.path.join(
                    self.get_working_directory(),
                    "%s_%s_%s_%s_prepointless.mtz"
                    % (pname, xname, dname, si.get_sweep_name()),
                )

                # we will want to delete this one exit
                FileHandler.record_temporary_file(hklout)

                first_batch = min(si.get_batches())
                si.set_batch_offset(counter * max_batches - first_batch + 1)

                rebatch(
                    hklin,
                    hklout,
                    first_batch=counter * max_batches + 1,
                    pname=pname,
                    xname=xname,
                    dname=dname,
                )

                pointless_hklins.append(hklout)

                # update the counter & recycle
                counter += 1

            # FIXME related to xia2-51 - this looks very very similar to the logic
            # in [A] above - is this duplicated logic?
            s = self._factory.Sortmtz()

            pointless_hklin = os.path.join(
                self.get_working_directory(),
                "%s_%s_prepointless_sorted.mtz"
                % (self._scalr_pname, self._scalr_xname),
            )

            s.set_hklout(pointless_hklin)

            for hklin in pointless_hklins:
                s.add_hklin(hklin)

            s.sort()

            pointless_const = os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_prepointless_const.mtz",
            )
            FileHandler.record_temporary_file(pointless_const)

            aimless_const = self._factory.Aimless()
            aimless_const.set_hklin(pointless_hklin)
            aimless_const.set_hklout(pointless_const)
            aimless_const.const()

            pointless_const = os.path.join(
                self.get_working_directory(),
                "%s_%s_prepointless_const_unmerged.mtz"
                % (self._scalr_pname, self._scalr_xname),
            )
            FileHandler.record_temporary_file(pointless_const)
            pointless_hklin = pointless_const

            pointgroup, reindex_op, ntr, pt = self._pointless_indexer_multisweep(
                pointless_hklin, refiners
            )

            for epoch in self._sweep_handler.get_epochs():
                pointgroups[epoch] = pointgroup
                reindex_ops[epoch] = reindex_op
            # SUMMARY ran pointless multisweep on combined mtz and made a dict
            # of  pointgroups and reindex_ops (all same)
        # END OF if multi-sweep and not input pg

        # START OF if not mulit-sweep or pg given
        else:
            for epoch in self._sweep_handler.get_epochs():
                si = self._sweep_handler.get_sweep_information(epoch)

                hklin = si.get_reflections()

                integrater = si.get_integrater()
                refiner = integrater.get_integrater_refiner()

                if self._scalr_input_pointgroup:
                    logger.debug(
                        "Using input pointgroup: %s", self._scalr_input_pointgroup
                    )
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = "h,k,l"
                    pt = False

                else:

                    pointless_hklin = self._prepare_pointless_hklin(
                        hklin, si.get_integrater().get_phi_width()
                    )

                    pointgroup, reindex_op, ntr, pt = self._pointless_indexer_jiffy(
                        pointless_hklin, refiner
                    )

                    logger.debug("X1698: %s: %s", pointgroup, reindex_op)

                    if ntr:

                        integrater.integrater_reset_reindex_operator()
                        need_to_return = True

                if pt and not probably_twinned:
                    probably_twinned = True

                logger.debug("Pointgroup: %s (%s)", pointgroup, reindex_op)

                pointgroups[epoch] = pointgroup
                reindex_ops[epoch] = reindex_op
            # SUMMARY - for each sweep, run indexer jiffy and get reindex operators
            # and pointgroups dictionaries (could be different between sweeps)

        # END OF if not mulit-sweep or pg given

        overall_pointgroup = None

        pointgroup_set = {pointgroups[e] for e in pointgroups}

        if len(pointgroup_set) > 1 and not probably_twinned:
            raise RuntimeError(
                "non uniform pointgroups: %s" % str(list(pointgroup_set))
            )

        if len(pointgroup_set) > 1:
            logger.debug(
                "Probably twinned, pointgroups: %s",
                " ".join(p.replace(" ", "") for p in pointgroup_set),
            )
            numbers = (Syminfo.spacegroup_name_to_number(ps) for ps in pointgroup_set)
            overall_pointgroup = Syminfo.spacegroup_number_to_name(min(numbers))
            self._scalr_input_pointgroup = overall_pointgroup

            logger.info("Twinning detected, assume pointgroup %s", overall_pointgroup)

            need_to_return = True

        else:
            overall_pointgroup = pointgroup_set.pop()
        # SUMMARY - Have handled if different pointgroups & chosen an overall_pointgroup
        # which is the lowest symmetry

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
            # This will give us the reflections in the correct point group
            si.set_reflections(integrater.get_integrater_intensities())

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        # in here now optionally work through the data files which should be
        # indexed with a consistent point group, and transform the orientation
        # matrices by the lattice symmetry operations (if possible) to get a
        # consistent definition of U matrix modulo fixed rotations

        if PhilIndex.params.xia2.settings.unify_setting:
            self.unify_setting()

        if self.get_scaler_reference_reflection_file():
            self._reference = self.get_scaler_reference_reflection_file()
            logger.debug("Using HKLREF %s", self._reference)

        elif PhilIndex.params.xia2.settings.scale.reference_reflection_file:
            self._reference = (
                PhilIndex.params.xia2.settings.scale.reference_reflection_file
            )
            logger.debug("Using HKLREF %s", self._reference)

        params = PhilIndex.params
        use_brehm_diederichs = params.xia2.settings.use_brehm_diederichs
        if len(self._sweep_handler.get_epochs()) > 1 and use_brehm_diederichs:
            self.brehm_diederichs_reindexing()
        # If not Brehm-deidrichs, set reference as first sweep
        elif len(self._sweep_handler.get_epochs()) > 1 and not self._reference:

            first = self._sweep_handler.get_epochs()[0]
            si = self._sweep_handler.get_sweep_information(first)
            self._reference = si.get_reflections()

        # Now reindex to be consistent with first dataset - run pointless on each
        # dataset with reference
        if self._reference:

            md = self._factory.Mtzdump()
            md.set_hklin(self._reference)
            md.dump()

            datasets = md.get_datasets()

            # then get the unit cell, lattice etc.

            reference_lattice = Syminfo.get_lattice(md.get_spacegroup())
            reference_cell = md.get_dataset_info(datasets[0])["cell"]

            # then compute the pointgroup from this...

            # ---------- REINDEX TO CORRECT (REFERENCE) SETTING ----------

            for epoch in self._sweep_handler.get_epochs():

                # if we are working with unified UB matrix then this should not
                # be a problem here (note, *if*; *should*)

                # what about e.g. alternative P1 settings?
                # see JIRA MXSW-904
                if PhilIndex.params.xia2.settings.unify_setting:
                    continue

                pl = self._factory.Pointless()

                si = self._sweep_handler.get_sweep_information(epoch)
                hklin = si.get_reflections()

                pl.set_hklin(
                    self._prepare_pointless_hklin(
                        hklin, si.get_integrater().get_phi_width()
                    )
                )

                hklout = os.path.join(
                    self.get_working_directory(),
                    "%s_rdx2.mtz" % os.path.split(hklin)[-1][:-4],
                )

                # we will want to delete this one exit
                FileHandler.record_temporary_file(hklout)

                # now set the initial reflection set as a reference...

                pl.set_hklref(self._reference)

                # https://github.com/xia2/xia2/issues/115 - should ideally iteratively
                # construct a reference or a tree of correlations to ensure correct
                # reference setting - however if small molecule assume has been
                # multi-sweep-indexed so can ignore "fatal errors" - temporary hack
                pl.decide_pointgroup(
                    ignore_errors=PhilIndex.params.xia2.settings.small_molecule
                )

                logger.debug("Reindexing analysis of %s", pl.get_hklin())

                pointgroup = pl.get_pointgroup()
                reindex_op = pl.get_reindex_operator()

                logger.debug("Operator: %s", reindex_op)

                # apply this...

                integrater = si.get_integrater()

                integrater.set_integrater_reindex_operator(
                    reindex_op, reason="match reference"
                )
                integrater.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup)
                )
                si.set_reflections(integrater.get_integrater_intensities())

                md = self._factory.Mtzdump()
                md.set_hklin(si.get_reflections())
                md.dump()

                datasets = md.get_datasets()

                if len(datasets) > 1:
                    raise RuntimeError(
                        "more than one dataset in %s" % si.get_reflections()
                    )

                # then get the unit cell, lattice etc.

                lattice = Syminfo.get_lattice(md.get_spacegroup())
                cell = md.get_dataset_info(datasets[0])["cell"]

                if lattice != reference_lattice:
                    raise RuntimeError(
                        "lattices differ in %s and %s"
                        % (self._reference, si.get_reflections())
                    )

                logger.debug("Cell: %.2f %.2f %.2f %.2f %.2f %.2f" % cell)
                logger.debug("Ref:  %.2f %.2f %.2f %.2f %.2f %.2f" % reference_cell)

                for j in range(6):
                    if (
                        math.fabs((cell[j] - reference_cell[j]) / reference_cell[j])
                        > 0.1
                    ):
                        raise RuntimeError(
                            "unit cell parameters differ in %s and %s"
                            % (self._reference, si.get_reflections())
                        )

        # ---------- SORT TOGETHER DATA ----------

        self._sort_together_data_ccp4()

        self._scalr_resolution_limits = {}

        # store central resolution limit estimates

        batch_ranges = [
            self._sweep_handler.get_sweep_information(epoch).get_batch_range()
            for epoch in self._sweep_handler.get_epochs()
        ]

        self._resolution_limit_estimates = ersatz_resolution(
            self._prepared_reflections, batch_ranges
        )

    def _scale(self):
        "Perform all of the operations required to deliver the scaled data."

        epochs = self._sweep_handler.get_epochs()

        sc = self._updated_aimless()
        sc.set_hklin(self._prepared_reflections)
        sc.set_chef_unmerged(True)
        sc.set_new_scales_file("%s.scales" % self._scalr_xname)

        user_resolution_limits = {}

        for epoch in epochs:
            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            intgr = si.get_integrater()

            if intgr.get_integrater_user_resolution():
                dmin = intgr.get_integrater_high_resolution()

                if (dname, sname) not in user_resolution_limits:
                    user_resolution_limits[(dname, sname)] = dmin
                elif dmin < user_resolution_limits[(dname, sname)]:
                    user_resolution_limits[(dname, sname)] = dmin

            start, end = si.get_batch_range()

            if (dname, sname) in self._scalr_resolution_limits:
                resolution, _ = self._scalr_resolution_limits[(dname, sname)]
                sc.add_run(start, end, exclude=False, resolution=resolution, name=sname)
            else:
                sc.add_run(start, end, name=sname)

        sc.set_hklout(
            os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_scaled_test.mtz",
            )
        )

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        # what follows, sucks

        failover = PhilIndex.params.xia2.settings.failover
        if failover:

            try:
                sc.scale()
            except RuntimeError as e:

                es = str(e)

                if (
                    "bad batch" in es
                    or "negative scales run" in es
                    or "no observations" in es
                ):

                    # first ID the sweep from the batch no

                    batch = int(es.split()[-1])
                    epoch = self._identify_sweep_epoch(batch)
                    sweep = self._scalr_integraters[epoch].get_integrater_sweep()

                    # then remove it from my parent xcrystal

                    self.get_scaler_xcrystal().remove_sweep(sweep)

                    # then remove it from the scaler list of intergraters
                    # - this should really be a scaler interface method

                    del self._scalr_integraters[epoch]

                    # then tell the user what is happening

                    logger.info(
                        "Sweep %s gave negative scales - removing", sweep.get_name()
                    )

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

        loggraph = sc.parse_ccp4_loggraph()

        resolution_info = {}

        reflection_files = sc.get_scaled_reflection_files()

        for dataset in reflection_files:
            FileHandler.record_temporary_file(reflection_files[dataset])

        for key in loggraph:
            if "Analysis against resolution" in key:
                dataset = key.split(",")[-1].strip()
                resolution_info[dataset] = transpose_loggraph(loggraph[key])

        # check in here that there is actually some data to scale..!

        if not resolution_info:
            raise RuntimeError("no resolution info")

        highest_suggested_resolution = self.assess_resolution_limits(
            sc.get_unmerged_reflection_file(), user_resolution_limits
        )

        if not self.get_scaler_done():
            logger.debug("Returning as scaling not finished...")
            return

        batch_info = {}

        for key in loggraph:
            if "Analysis against Batch" in key:
                dataset = key.split(",")[-1].strip()
                batch_info[dataset] = transpose_loggraph(loggraph[key])

        sc = self._updated_aimless()

        FileHandler.record_log_file(
            f"{self._scalr_pname} {self._scalr_xname} aimless", sc.get_log_file()
        )

        sc.set_hklin(self._prepared_reflections)
        sc.set_new_scales_file("%s_final.scales" % self._scalr_xname)

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            start, end = si.get_batch_range()

            resolution_limit, _ = self._scalr_resolution_limits[(dname, sname)]

            sc.add_run(
                start, end, exclude=False, resolution=resolution_limit, name=xname
            )

        sc.set_hklout(
            os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_scaled.mtz",
            )
        )

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.scale()

        FileHandler.record_xml_file(
            f"{self._scalr_pname} {self._scalr_xname} aimless", sc.get_xmlout()
        )

        data = sc.get_summary()
        scales_file = sc.get_new_scales_file()
        loggraph = sc.parse_ccp4_loggraph()

        standard_deviation_info = {}

        for key in loggraph:
            if "standard deviation v. Intensity" in key:
                dataset = key.split(",")[-1].strip()
                standard_deviation_info[dataset] = transpose_loggraph(loggraph[key])

        resolution_info = {}

        for key in loggraph:
            if "Analysis against resolution" in key:
                dataset = key.split(",")[-1].strip()
                resolution_info[dataset] = transpose_loggraph(loggraph[key])

        batch_info = {}

        for key in loggraph:
            if "Analysis against Batch" in key:
                dataset = key.split(",")[-1].strip()
                batch_info[dataset] = transpose_loggraph(loggraph[key])

        # finally put all of the results "somewhere useful"

        self._scalr_statistics = data

        self._scalr_scaled_refl_files = copy.deepcopy(sc.get_scaled_reflection_files())

        sc = self._updated_aimless()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        self._wavelengths_in_order = []

        for epoch in epochs:
            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            start, end = si.get_batch_range()

            resolution_limit, _ = self._scalr_resolution_limits[(dname, sname)]

            sc.add_run(
                start, end, exclude=False, resolution=resolution_limit, name=sname
            )

            if dname not in self._wavelengths_in_order:
                self._wavelengths_in_order.append(dname)

        sc.set_hklout(
            os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_scaled.mtz",
            )
        )

        sc.set_scalepack()

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.scale()

        self._update_scaled_unit_cell()

        self._scalr_scaled_reflection_files = {}
        self._scalr_scaled_reflection_files["sca"] = {}
        self._scalr_scaled_reflection_files["sca_unmerged"] = {}
        self._scalr_scaled_reflection_files["mtz_unmerged"] = {}

        for key in self._scalr_scaled_refl_files:
            hklout = self._scalr_scaled_refl_files[key]

            scaout = "%s.sca" % hklout[:-4]
            self._scalr_scaled_reflection_files["sca"][key] = scaout
            FileHandler.record_data_file(scaout)
            scalepack = os.path.join(
                os.path.split(hklout)[0],
                os.path.split(hklout)[1]
                .replace("_scaled", "_scaled_unmerged")
                .replace(".mtz", ".sca"),
            )
            self._scalr_scaled_reflection_files["sca_unmerged"][key] = scalepack
            FileHandler.record_data_file(scalepack)
            mtz_unmerged = os.path.splitext(scalepack)[0] + ".mtz"
            self._scalr_scaled_reflection_files["mtz_unmerged"][key] = mtz_unmerged
            FileHandler.record_data_file(mtz_unmerged)

            if self._scalr_cell_esd is not None:
                # patch .mtz and overwrite unit cell information
                import xia2.Modules.Scaler.tools as tools

                override_cell = self._scalr_cell_dict.get(
                    f"{self._scalr_pname}_{self._scalr_xname}_{key}"
                )[0]
                tools.patch_mtz_unit_cell(mtz_unmerged, override_cell)
                tools.patch_mtz_unit_cell(hklout, override_cell)

            self._scalr_scaled_reflection_files["mtz_unmerged"][key] = mtz_unmerged
            FileHandler.record_data_file(mtz_unmerged)

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

        sc = self._updated_aimless()
        sc.set_hklin(self._prepared_reflections)
        sc.set_scales_file(scales_file)

        self._wavelengths_in_order = []

        for epoch in epochs:

            si = self._sweep_handler.get_sweep_information(epoch)
            pname, xname, dname = si.get_project_info()
            sname = si.get_sweep_name()
            start, end = si.get_batch_range()

            resolution_limit, _ = self._scalr_resolution_limits[(dname, sname)]

            sc.add_run(
                start, end, exclude=False, resolution=resolution_limit, name=sname
            )

            if dname not in self._wavelengths_in_order:
                self._wavelengths_in_order.append(dname)

        sc.set_hklout(
            os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_chef.mtz",
            )
        )

        sc.set_chef_unmerged(True)

        if self.get_scaler_anomalous():
            sc.set_anomalous()
        sc.scale()
        if not PhilIndex.params.dials.fast_mode:
            try:
                self._generate_absorption_map(sc)
            except Exception as e:
                # Map generation may fail for number of reasons, eg. matplotlib borken
                logger.debug("Could not generate absorption map (%s)", e)

    def _generate_absorption_map(self, scaler):
        output = scaler.get_all_output()

        aimless = "AIMLESS, CCP4"

        pattern = re.compile(" +#+ *CCP4.*#+")
        for line in output:
            if pattern.search(line):
                aimless = re.sub(r"\s\s+", ", ", line.strip("\t\n #"))
                break

        coefficients = scrape_coefficients(log=output)
        if coefficients:
            absmap = evaluate_1degree(coefficients)
            absmin, absmax = absmap.min(), absmap.max()
        else:
            absmin, absmax = 1.0, 1.0

        block = CIF.get_block("xia2")
        mmblock = mmCIF.get_block("xia2")
        block["_exptl_absorpt_correction_T_min"] = mmblock[
            "_exptl.absorpt_correction_T_min"
        ] = (
            absmin / absmax
        )  # = scaled
        block["_exptl_absorpt_correction_T_max"] = mmblock[
            "_exptl.absorpt_correction_T_max"
        ] = (
            absmax / absmax
        )  # = 1
        block["_exptl_absorpt_correction_type"] = mmblock[
            "_exptl.absorpt_correction_type"
        ] = "empirical"
        block["_exptl_absorpt_process_details"] = mmblock[
            "_exptl.absorpt_process_details"
        ] = (
            """
%s
Scaling & analysis of unmerged intensities, absorption correction using spherical harmonics
"""
            % aimless
        )

        log_directory = self._base_path / "LogFiles"
        if absmax - absmin > 0.000001:
            log_directory.mkdir(parents=True, exist_ok=True)
            mapfile = log_directory / "absorption_surface.png"
            generate_map(absmap, str(mapfile))
        else:
            logger.debug(
                "Cannot create absorption surface: map is too flat (min: %f, max: %f)",
                absmin,
                absmax,
            )

    def _identify_sweep_epoch(self, batch):
        """Identify the sweep epoch a given batch came from - N.B.
        this assumes that the data are rebatched, will raise an exception if
        more than one candidate is present."""

        epochs = []

        for epoch in self._sweep_handler.get_epochs():
            si = self._sweep_handler.get_sweep_information(epoch)
            if batch in si.get_batches():
                epochs.append(epoch)

        if len(epochs) > 1:
            raise RuntimeError("batch %d found in multiple sweeps" % batch)

        return epochs[0]

    def _prepare_pointless_hklin(self, hklin, phi_width):
        return _prepare_pointless_hklin(self.get_working_directory(), hklin, phi_width)

    def get_batch_to_dose(self):
        batch_to_dose = {}
        epoch_to_dose = {}
        for xsample in self.get_scaler_xcrystal()._samples.values():
            epoch_to_dose.update(xsample.get_epoch_to_dose())
        for e0 in self._sweep_handler._sweep_information:
            si = self._sweep_handler._sweep_information[e0]
            batch_offset = si.get_batch_offset()
            printed = False
            for b in range(si.get_batches()[0], si.get_batches()[1] + 1):
                if epoch_to_dose:
                    # when handling Eiger data this table appears to be somewhat broken
                    # see https://github.com/xia2/xia2/issues/90 - proper fix should be
                    # to work out why the epochs are not set correctly in first place...
                    if si._image_to_epoch[b - batch_offset] in epoch_to_dose:
                        if not printed:
                            logger.debug("Epoch found; all good")
                            printed = True
                        batch_to_dose[b] = epoch_to_dose[
                            si._image_to_epoch[b - batch_offset]
                        ]
                    else:
                        if not printed:
                            logger.debug("Epoch not found; using offset %f", e0)
                            printed = True
                        batch_to_dose[b] = epoch_to_dose[
                            si._image_to_epoch[b - batch_offset] - e0
                        ]
                else:
                    # backwards compatibility 2015-12-11
                    batch_to_dose[b] = b
        return batch_to_dose

    def get_UBlattsymm_from_sweep_info(self, sweep_info):
        """Return U, B, lattice symmetry from the data (i.e. mtz file)."""
        return get_umat_bmat_lattice_symmetry_from_mtz(sweep_info.get_reflections())

    def apply_reindex_operator_to_sweep_info(self, sweep_info, reindex_op, reason):
        """Apply the reindex operator to the data.

        Delegate to the integrater reindex operator method."""
        intgr = sweep_info.get_integrater()
        intgr.set_integrater_reindex_operator(reindex_op, reason=reason)
        sweep_info.set_reflections(intgr.get_integrater_intensities())

    def get_mtz_data_from_sweep_info(self, sweep_info):
        """Get the data in mtz form.

        Trivial for CCP4ScalerA, as always use the integrator to
        generate a new mtz when reindexing, so just return this."""
        return sweep_info.get_reflections()
