from __future__ import absolute_import, division, print_function

import os

from dials.algorithms.refinement.restraints.restraints_parameterisation import (
    uc_phil_scope as restraints_scope,
)
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import auto_logfiler
from xia2.Schema.Interfaces.Refiner import Refiner
from xia2.Wrappers.Dials.CombineExperiments import (
    CombineExperiments as _CombineExperiments,
)
from xia2.Wrappers.Dials.Refine import Refine as _Refine
from xia2.Wrappers.Dials.Report import Report as _Report
from xia2.Wrappers.Dials.SplitExperiments import SplitExperiments


class DialsRefiner(Refiner):
    def __init__(self):
        super(DialsRefiner, self).__init__()

    # factory functions

    def CombineExperiments(self):
        combiner = _CombineExperiments()
        combiner.set_working_directory(self.get_working_directory())
        auto_logfiler(combiner)
        for idxr in self._refinr_indexers.values():
            combiner.add_experiments(idxr.get_indexer_payload("experiments_filename"))
            combiner.add_reflections(idxr.get_indexed_filename())
        return combiner

    def Refine(self):
        refine = _Refine()
        params = PhilIndex.params.dials.refine
        refine.set_phil_file(params.phil_file)
        refine.set_working_directory(self.get_working_directory())
        if PhilIndex.params.dials.fast_mode:
            # scan-static refinement in fast mode
            refine.set_scan_varying(False)
        else:
            refine.set_scan_varying(params.scan_varying)
        refine.set_reflections_per_degree(params.reflections_per_degree)
        refine.set_interval_width_degrees(params.interval_width_degrees)
        refine.set_outlier_algorithm(PhilIndex.params.dials.outlier.algorithm)
        if PhilIndex.params.dials.fix_geometry:
            refine.set_detector_fix("all")
            refine.set_beam_fix("all")
        elif PhilIndex.params.dials.fix_distance:
            refine.set_detector_fix("distance")
        refine.set_close_to_spindle_cutoff(
            PhilIndex.params.dials.close_to_spindle_cutoff
        )
        # Do joint refinement of unit cell parameters if jointly indexing multi sweeps.
        # If the user hasn't specified any options, use the defaults from dials.refine.
        if not params.restraints.tie_to_target:
            params.restraints.tie_to_target = (
                restraints_scope.extract().restraints.tie_to_target
            )
        # If the user hasn't specified any options, use the defaults from dials.refine.
        if not params.restraints.tie_to_group:
            params.restraints.tie_to_group = (
                restraints_scope.extract().restraints.tie_to_group
            )
            if PhilIndex.params.xia2.settings.multi_sweep_indexing:
                # If the user hasn't specified otherwise, use default sigmas of 0.01.
                params.restraints.tie_to_group[0].sigmas = 6 * (0.01,)
        refine.tie_to_target = params.restraints.tie_to_target
        refine.tie_to_group = params.restraints.tie_to_group

        auto_logfiler(refine, "REFINE")

        return refine

    def split_after_refinement(self):
        """
        Split the refined experiments.

        Add all the resulting experiment list/reflection table pairs to the payload.
        """
        split_experiments = SplitExperiments()
        auto_logfiler(split_experiments, "SPLIT_EXPERIMENTS")
        cwd = self.get_working_directory()
        split_experiments.set_working_directory(cwd)
        split_experiments.add_experiments(self._refinr_experiments_filename)
        split_experiments.add_reflections(self._refinr_indexed_filename)
        prefix = "{}_refined_split".format(split_experiments.get_xpid())
        split_experiments._experiments_prefix = prefix
        split_experiments._reflections_prefix = prefix
        split_experiments.run()

        num_sweeps = len(self._refinr_sweeps)
        for i, sweep in enumerate(self._refinr_sweeps):
            name = sweep._name
            root = "{pre}_{ind:0{n_dig:d}d}".format(
                pre=prefix, ind=i, n_dig=len(str(num_sweeps))
            )
            expts = os.path.join(cwd, root + ".expt")
            refls = os.path.join(cwd, root + ".refl")
            self.set_refiner_payload("{}_models.expt".format(name), expts)
            self.set_refiner_payload("{}_observations.refl".format(name), refls)

    def Report(self):
        report = _Report()
        report.set_working_directory(self.get_working_directory())
        auto_logfiler(report, "REPORT")
        return report

    def _refine_prepare(self):
        pass

    def _refine(self):
        for idxr in set(self._refinr_indexers.values()):
            experiments = idxr.get_indexer_experiment_list()

            indexed_experiments = idxr.get_indexer_payload("experiments_filename")
            indexed_reflections = idxr.get_indexer_payload("indexed_filename")

            assert len(experiments.crystals()) == 1  # currently only handle one lattice

            from dxtbx.serialize import load

            scan_static = PhilIndex.params.dials.refine.scan_static

            # Avoid doing scan-varying refinement on narrow wedges.
            start, end = experiments[0].scan.get_oscillation_range()
            total_oscillation_range = end - start

            if (
                PhilIndex.params.dials.refine.scan_varying
                and total_oscillation_range > 5
                and not PhilIndex.params.dials.fast_mode
            ):
                scan_varying = PhilIndex.params.dials.refine.scan_varying
            else:
                scan_varying = False

            if scan_static:
                refiner = self.Refine()
                refiner.set_experiments_filename(indexed_experiments)
                refiner.set_indexed_filename(indexed_reflections)
                refiner.set_scan_varying(False)
                refiner.run()
                self._refinr_experiments_filename = (
                    refiner.get_refined_experiments_filename()
                )
                self._refinr_indexed_filename = refiner.get_refined_filename()
            else:
                self._refinr_experiments_filename = indexed_experiments
                self._refinr_indexed_filename = indexed_reflections

            if scan_varying:
                refiner = self.Refine()
                refiner.set_experiments_filename(self._refinr_experiments_filename)
                refiner.set_indexed_filename(self._refinr_indexed_filename)
                if total_oscillation_range < 36:
                    refiner.set_interval_width_degrees(total_oscillation_range / 2)
                refiner.run()
                self._refinr_experiments_filename = (
                    refiner.get_refined_experiments_filename()
                )
                self._refinr_indexed_filename = refiner.get_refined_filename()

            if scan_static or scan_varying:
                FileHandler.record_log_file(
                    "%s REFINE" % idxr.get_indexer_full_name(), refiner.get_log_file()
                )
                report = self.Report()
                report.set_experiments_filename(self._refinr_experiments_filename)
                report.set_reflections_filename(self._refinr_indexed_filename)
                html_filename = os.path.join(
                    self.get_working_directory(),
                    "%i_dials.refine.report.html" % report.get_xpid(),
                )
                report.set_html_filename(html_filename)
                report.run()
                FileHandler.record_html_file(
                    "%s REFINE" % idxr.get_indexer_full_name(), html_filename
                )

            experiments = load.experiment_list(self._refinr_experiments_filename)
            self.set_refiner_payload("models.expt", self._refinr_experiments_filename)
            self.set_refiner_payload("observations.refl", self._refinr_indexed_filename)

            # this is the result of the cell refinement
            self._refinr_cell = experiments.crystals()[0].get_unit_cell().parameters()

    def _refine_finish(self):
        # For multiple-sweep joint indexing and refinement, because indexers are fairly
        # rigidly one-sweep-only, we must split the refined experiments and add the
        # individual experiment list/reflection table pairs to the payload.
        if PhilIndex.params.xia2.settings.multi_sweep_indexing:
            self.split_after_refinement()
