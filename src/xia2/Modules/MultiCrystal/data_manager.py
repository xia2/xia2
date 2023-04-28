from __future__ import annotations

import copy
import logging
import math

from cctbx import miller
from dials.array_family import flex
from dials.command_line import export, merge
from dials.command_line.slice_sequence import slice_experiments, slice_reflections
from dials.report.analysis import scaled_data_as_miller_array
from dials.util.batch_handling import assign_batches_to_reflections
from dxtbx.model import ExperimentList

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self, experiments, reflections, ssx_flag=False):
        self._input_experiments = experiments
        self._input_reflections = reflections

        self._experiments = copy.deepcopy(experiments)
        self._reflections = copy.deepcopy(reflections)
        self.ids_to_identifiers_map = dict(self._reflections.experiment_identifiers())
        self.identifiers_to_ids_map = {
            value: key for key, value in self.ids_to_identifiers_map.items()
        }

        self._set_batches(ssx_flag)

    def _set_batches(self, ssx_flag):
        if not ssx_flag:
            max_batches = max(e.scan.get_image_range()[1] for e in self._experiments)
            max_batches += 10  # allow some head room
        else:
            max_batches = 1
            self.ssx_batch_dict = {}
            self.ssx_batch_list = []

        n = int(math.ceil(math.log10(max_batches)))

        for i, expt in enumerate(self._experiments):
            if not ssx_flag:
                expt.scan.set_batch_offset(i * 10**n)
                if expt.imageset:
                    # This may be a different scan instance ¯\_(ツ)_/¯
                    expt.imageset.get_scan().set_batch_offset(
                        expt.scan.get_batch_offset()
                    )
                logger.debug(
                    f"{expt.scan.get_batch_offset()} {expt.scan.get_batch_range()}"
                )

            else:
                self.ssx_batch_dict[expt] = i * 10**n
                self.ssx_batch_list.append(i * 10**n)

    @property
    def experiments(self):
        return self._experiments

    @experiments.setter
    def experiments(self, experiments):
        self._experiments = experiments

    @property
    def reflections(self):
        return self._reflections

    @reflections.setter
    def reflections(self, reflections):
        self._reflections = reflections

    def select(self, experiment_identifiers):
        self._experiments = ExperimentList(
            [
                expt
                for expt in self._experiments
                if expt.identifier in experiment_identifiers
            ]
        )
        self.reflections = self.reflections.select_on_experiment_identifiers(
            experiment_identifiers
        )
        self.reflections.reset_ids()
        self.reflections.assert_experiment_identifiers_are_consistent(self.experiments)

    def filter_dose(self, dose_min, dose_max):
        keep_expts = []
        for i, expt in enumerate(self._experiments):
            start, end = expt.scan.get_image_range()
            if (start <= dose_min <= end) or (start <= dose_max <= end):
                keep_expts.append(expt.identifier)
            else:
                logger.info(
                    f"Removing experiment {expt.identifier} (image range {start, end} does not overlap with dose range)"
                )
        if len(keep_expts):
            logger.info(
                f"Selecting {len(keep_expts)} experiments that overlap with dose range"
            )
        self.select(keep_expts)

        image_range = [
            (
                max(dose_min, expt.scan.get_image_range()[0]),
                min(dose_max, expt.scan.get_image_range()[1]),
            )
            for expt in self._experiments
        ]
        n_refl_before = self._reflections.size()
        self._experiments = slice_experiments(self._experiments, image_range)
        flex.min_max_mean_double(self._reflections["xyzobs.px.value"].parts()[2]).show()
        self._reflections = slice_reflections(self._reflections, image_range)
        flex.min_max_mean_double(self._reflections["xyzobs.px.value"].parts()[2]).show()
        logger.info(
            "%i reflections out of %i remaining after filtering for dose"
            % (self._reflections.size(), n_refl_before)
        )

    def reflections_as_miller_arrays(self, combined=False, ssx_flag=False):
        # offsets = calculate_batch_offsets(experiments)
        reflection_tables = []
        for id_ in set(self._reflections["id"]).difference({-1}):
            reflection_tables.append(
                self._reflections.select(self._reflections["id"] == id_)
            )

        if not ssx_flag:
            offsets = [expt.scan.get_batch_offset() for expt in self._experiments]
        else:
            offsets = self.ssx_batch_list

        reflection_tables = assign_batches_to_reflections(reflection_tables, offsets)

        if combined:
            # filter bad refls and negative scales
            batches = flex.int()
            scales = flex.double()

            for r in reflection_tables:
                sel = ~r.get_flags(r.flags.bad_for_scaling, all=False)
                sel &= r["inverse_scale_factor"] > 0
                batches.extend(r["batch"].select(sel))
                scales.extend(r["inverse_scale_factor"].select(sel))
            scaled_array = scaled_data_as_miller_array(
                reflection_tables, self._experiments
            )
            batch_array = miller.array(scaled_array, data=batches)
            scale_array = miller.array(scaled_array, data=scales)
            return scaled_array, batch_array, scale_array

        else:
            scaled_arrays = []
            batch_arrays = []
            scale_arrays = []
            for expt, r in zip(self._experiments, reflection_tables):
                sel = ~r.get_flags(r.flags.bad_for_scaling, all=False)
                sel &= r["inverse_scale_factor"] > 0
                batches = r["batch"].select(sel)
                scales = r["inverse_scale_factor"].select(sel)
                scaled_arrays.append(scaled_data_as_miller_array([r], [expt]))
                batch_arrays.append(miller.array(scaled_arrays[-1], data=batches))
                scale_arrays.append(miller.array(scaled_arrays[-1], data=scales))
            return scaled_arrays, batch_arrays, scale_arrays

    def reindex(self, cb_op, space_group=None):
        logger.info("Reindexing: %s" % cb_op)
        self._reflections["miller_index"] = cb_op.apply(
            self._reflections["miller_index"]
        )

        for expt in self._experiments:
            cryst_reindexed = expt.crystal.change_basis(cb_op)
            if space_group is not None:
                cryst_reindexed.set_space_group(space_group)
            expt.crystal.update(cryst_reindexed)

    def export_reflections(self, filename, d_min=None):
        reflections = self._reflections
        if d_min:
            reflections = reflections.select(reflections["d"] >= d_min)
        reflections.as_file(filename)
        return filename

    def export_experiments(self, filename):
        self._experiments.as_file(filename)
        return filename

    def export_unmerged_mtz(self, filename, d_min=None):
        params = export.phil_scope.extract()
        params.mtz.d_min = d_min
        params.mtz.hklout = filename
        params.intensity = ["scale"]
        export.export_mtz(params, self._experiments, [self._reflections])

    def export_merged_mtz(self, filename, d_min=None, r_free_params=None):
        params = merge.phil_scope.extract()
        params.d_min = d_min
        params.assess_space_group = False
        if r_free_params:
            params.r_free_flags = r_free_params
        mtz_obj = merge.merge_data_to_mtz(
            params, self._experiments, [self._reflections]
        )
        mtz_obj.write(filename)
