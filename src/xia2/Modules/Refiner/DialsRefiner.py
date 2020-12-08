import os

from dials.algorithms.refinement.restraints.restraints_parameterisation import (
    uc_phil_scope as restraints_scope,
)
from dials.array_family import flex
from dxtbx.model import ExperimentList
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
        super().__init__()

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
        # For multiple-sweep joint refinement, use the user's preferred restraints or
        # default to restraining using `tie_to_group` with some reasonably tight sigmas.
        if (
            PhilIndex.params.xia2.settings.multi_sweep_refinement
            and not params.restraints.tie_to_group
        ):
            params.restraints.tie_to_group = (
                restraints_scope.extract().restraints.tie_to_group
            )
            # If the user hasn't specified otherwise, use default sigmas of 0.01.
            params.restraints.tie_to_group[0].sigmas = 6 * (0.01,)
        # Set any specified restraints for joint refinement of multiple sweeps.
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
        cwd = self.get_working_directory()
        split_experiments.set_working_directory(cwd)
        auto_logfiler(split_experiments, "SPLIT_EXPERIMENTS")
        split_experiments.add_experiments(self._refinr_experiments_filename)
        split_experiments.add_reflections(self._refinr_indexed_filename)
        prefix = f"{split_experiments.get_xpid()}_refined_split"
        split_experiments._experiments_prefix = prefix
        split_experiments._reflections_prefix = prefix
        split_experiments.run()

        # Get the number of digits necessary to represent the largest sweep number.
        n_digits = len(str(len(self._refinr_sweeps) - 1))

        for i, sweep in enumerate(self._refinr_sweeps):
            name = sweep._name
            root = f"{prefix}_{i:0{n_digits:d}d}"
            expts = os.path.join(cwd, root + ".expt")
            refls = os.path.join(cwd, root + ".refl")
            self.set_refiner_payload(f"{name}_models.expt", expts)
            self.set_refiner_payload(f"{name}_observations.refl", refls)

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

            # If multiple sweeps but not doing joint refinement, get only the
            # relevant reflections.
            multi_sweep = PhilIndex.params.xia2.settings.multi_sweep_refinement
            if len(experiments) > 1 and not multi_sweep:
                xsweeps = idxr._indxr_sweeps
                assert len(xsweeps) == len(experiments)
                # Don't do joint refinement
                assert len(self._refinr_sweeps) == 1
                xsweep = self._refinr_sweeps[0]
                i = xsweeps.index(xsweep)
                experiments = experiments[i : i + 1]

                # Extract and output experiment and reflections for current sweep
                indexed_experiments = os.path.join(
                    self.get_working_directory(), "%s_indexed.expt" % xsweep.get_name()
                )
                indexed_reflections = os.path.join(
                    self.get_working_directory(), "%s_indexed.refl" % xsweep.get_name()
                )

                experiments.as_file(indexed_experiments)

                reflections = flex.reflection_table.from_file(
                    idxr.get_indexer_payload("indexed_filename")
                )
                sel = reflections["id"] == i
                assert sel.count(True) > 0
                imageset_id = reflections["imageset_id"].select(sel)
                assert imageset_id.all_eq(imageset_id[0])
                sel = reflections["imageset_id"] == imageset_id[0]
                reflections = reflections.select(sel)
                # set indexed reflections to id == 0 and imageset_id == 0
                reflections["id"].set_selected(reflections["id"] == i, 0)
                reflections["imageset_id"] = flex.int(len(reflections), 0)
                reflections.as_file(indexed_reflections)

            # currently only handle one lattice/refiner
            assert len(experiments.crystals()) == 1

            scan_static = PhilIndex.params.dials.refine.scan_static

            # Avoid doing scan-varying refinement on narrow wedges.
            scan_oscillation_ranges = []
            for experiment in experiments:
                start, end = experiment.scan.get_oscillation_range()
                scan_oscillation_ranges.append(end - start)

            min_oscillation_range = min(scan_oscillation_ranges)

            if (
                PhilIndex.params.dials.refine.scan_varying
                and min_oscillation_range > 5
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
                if min_oscillation_range < 36:
                    refiner.set_interval_width_degrees(min_oscillation_range / 2)
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

            experiments = ExperimentList.from_file(self._refinr_experiments_filename)
            self.set_refiner_payload("models.expt", self._refinr_experiments_filename)
            self.set_refiner_payload("observations.refl", self._refinr_indexed_filename)

            # this is the result of the cell refinement
            self._refinr_cell = experiments.crystals()[0].get_unit_cell().parameters()

    def _refine_finish(self):
        # For multiple-sweep joint refinement, because integraters are fairly rigidly
        # one-sweep-only, we must split the refined experiments and add the individual
        # experiment list/reflection table pairs to the payload.
        if PhilIndex.params.xia2.settings.multi_sweep_refinement:
            self.split_after_refinement()
