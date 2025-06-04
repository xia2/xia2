from __future__ import annotations

import copy
import logging
import math

import iotbx.phil
from cctbx import miller, sgtbx
from dials.array_family import flex
from dials.command_line import export, merge
from dials.command_line.slice_sequence import slice_experiments, slice_reflections
from dials.report.analysis import scaled_data_as_miller_array
from dials.util.batch_handling import (
    assign_batches_to_reflections,
    calculate_batch_offsets,
)
from dials.util.export_mtz import WavelengthGroup, match_wavelengths
from dxtbx.model import ExperimentList

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self, experiments: ExperimentList, reflections: flex.reflection_table):
        self._input_experiments = experiments
        self._input_reflections = reflections

        self._experiments = copy.deepcopy(experiments)
        self._reflections = copy.deepcopy(reflections)
        self.ids_to_identifiers_map = dict(self._reflections.experiment_identifiers())
        self.identifiers_to_ids_map = {
            value: key for key, value in self.ids_to_identifiers_map.items()
        }
        self.wavelengths: dict[
            float, WavelengthGroup
        ] = {}  # map of wl to wavelength group.
        self.batch_offset_list: list[int] = []

        if all(e.scan is None for e in self._experiments):
            self.all_stills = True
        elif all(e.scan is not None for e in self._experiments):
            self.all_stills = False
        else:
            raise ValueError(
                "cannot mix stills and rotation data for multi crystal analysis"
            )

        self._set_batches()

    def _set_batches(self) -> None:
        if not self.all_stills:
            self.batch_offset_list = calculate_batch_offsets(self._experiments)
        else:
            self.batch_offset_list = list(range(len(self._experiments)))

    @property
    def experiments(self) -> ExperimentList:
        return self._experiments

    @experiments.setter
    def experiments(self, experiments) -> None:
        self._experiments = experiments

    @property
    def reflections(self) -> flex.reflection_table:
        return self._reflections

    @reflections.setter
    def reflections(self, reflections) -> None:
        self._reflections = reflections

    def select(self, experiment_identifiers: list[str]) -> None:
        self.batch_offset_list = [
            i
            for (i, expt) in zip(self.batch_offset_list, self._experiments)
            if expt.identifier in experiment_identifiers
        ]
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

    def filter_dose(self, dose_min: float, dose_max: float) -> None:
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

    def reflections_as_miller_arrays(self, combined: bool = False):
        reflection_tables = []
        for id_ in set(self._reflections["id"]).difference({-1}):
            reflection_tables.append(
                self._reflections.select(self._reflections["id"] == id_)
            )

        reflection_tables = assign_batches_to_reflections(
            reflection_tables, self.batch_offset_list
        )

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

    def reindex(
        self,
        cb_op: sgtbx.change_of_basis_op,
        space_group: sgtbx.space_group | None = None,
    ) -> None:
        logger.info("Reindexing: %s" % cb_op)
        self._reflections["miller_index"] = cb_op.apply(
            self._reflections["miller_index"]
        )

        for expt in self._experiments:
            cryst_reindexed = expt.crystal.change_basis(cb_op)
            if space_group is not None:
                cryst_reindexed.set_space_group(space_group)
            expt.crystal.update(cryst_reindexed)

    def split_by_wavelength(self, wavelength_tolerance: float) -> None:
        if (
            not self.wavelengths
        ):  # don't want this to update after filtering/clustering etc
            self.wavelengths = match_wavelengths(self.experiments, wavelength_tolerance)

        self.data_split_by_wl: dict[
            float, dict
        ] = {}  # do want to update this based on current data

        for wl in sorted(self.wavelengths.keys()):
            new_exps = copy.deepcopy(self.experiments)
            new_exps.select_on_experiment_identifiers(self.wavelengths[wl].identifiers)
            new_refls = self.reflections.select_on_experiment_identifiers(
                new_exps.identifiers()
            )
            self.data_split_by_wl[wl] = {"expt": new_exps, "refl": new_refls}

    def export_unmerged_wave_mtz(
        self, wl: float, prefix: str, d_min: float, wavelength_tolerance: float
    ) -> str | None:
        data = self.data_split_by_wl[wl]
        nn = len(self.wavelengths)
        fmt = "%%0%dd" % (math.log10(nn) + 1)
        index = sorted(self.wavelengths.keys()).index(wl)
        params = export.phil_scope.extract()
        params.mtz.d_min = d_min
        params.mtz.hklout = f"{prefix}_WAVE{fmt % (index + 1)}.mtz"
        params.mtz.wavelength_tolerance = wavelength_tolerance
        expt_to_export = copy.deepcopy(data["expt"])
        params.intensity = ["scale"]
        if data["expt"]:  # When is this not the case?
            export.export_mtz(params, expt_to_export, [data["refl"]])
            return params.mtz.hklout
        return None

    def export_unmerged_wave_mmcif(self, wl: float, prefix: str, d_min: float) -> None:
        data = self.data_split_by_wl[wl]
        nn = len(self.wavelengths)
        fmt = "%%0%dd" % (math.log10(nn) + 1)
        index = sorted(self.wavelengths.keys()).index(wl)
        params = export.phil_scope.extract()
        params.mtz.d_min = d_min
        params.mmcif.hklout = f"{prefix}_WAVE{fmt % (index + 1)}.mmcif"
        expt_to_export = copy.deepcopy(data["expt"])
        params.intensity = ["scale"]
        if data["expt"]:
            export.export_mmcif(params, expt_to_export, [data["refl"]])

    def export_merged_wave_mtz(
        self,
        wl: float,
        prefix: str,
        d_min: float | None = None,
        r_free_params: iotbx.phil.scope_extract | None = None,
        wavelength_tolerance: float | None = None,
    ):
        data = self.data_split_by_wl[wl]
        nn = len(self.wavelengths)
        fmt = "%%0%dd" % (math.log10(nn) + 1)
        index = sorted(self.wavelengths.keys()).index(wl)

        params = merge.phil_scope.extract()
        params.d_min = d_min
        params.assess_space_group = False
        params.wavelength_tolerance = wavelength_tolerance
        if r_free_params:
            params.r_free_flags = r_free_params
        filename = f"{prefix}_WAVE{fmt % (index + 1)}.mtz"
        if data["expt"]:
            mtz_obj = merge.merge_data_to_mtz(params, data["expt"], [data["refl"]])
            mtz_obj.write_to_file(filename)
            return filename
        return None

    def export_reflections(self, filename: str, d_min: float | None = None) -> str:
        reflections = self._reflections
        if d_min:
            reflections = reflections.select(reflections["d"] >= d_min)
        reflections.as_file(filename)
        return filename

    def export_experiments(self, filename: str) -> str:
        self._experiments.as_file(filename)
        return filename

    def export_unmerged_mtz(
        self,
        filename: str,
        d_min: float | None = None,
        wavelength_tolerance: float = 0.0001,
    ) -> None:
        params = export.phil_scope.extract()
        expt_to_export = copy.deepcopy(self._experiments)
        params.mtz.d_min = d_min
        params.mtz.hklout = filename
        params.mtz.wavelength_tolerance = wavelength_tolerance
        params.intensity = ["scale"]
        export.export_mtz(params, expt_to_export, [self._reflections])

    def export_unmerged_mmcif(self, filename: str, d_min: float | None = None) -> None:
        params = export.phil_scope.extract()
        expt_to_export = copy.deepcopy(self._experiments)
        params.mtz.d_min = d_min
        params.mmcif.hklout = filename
        params.intensity = ["scale"]
        export.export_mmcif(params, expt_to_export, [self._reflections])

    def export_merged_mtz(
        self,
        filename: str,
        d_min: float | None = None,
        r_free_params: iotbx.phil.scope_extract | None = None,
        wavelength_tolerance: float = 0.0001,
    ) -> None:
        params = merge.phil_scope.extract()
        params.d_min = d_min
        params.assess_space_group = False
        params.wavelength_tolerance = wavelength_tolerance
        if r_free_params:
            params.r_free_flags = r_free_params
        mtz_obj = merge.merge_data_to_mtz(
            params, self._experiments, [self._reflections]
        )
        mtz_obj.write_to_file(filename)
