from __future__ import annotations

import logging

from dials.algorithms.scaling.algorithm import ScalingAlgorithm
from dials.algorithms.scaling.scaler_factory import create_scaler
from dials.algorithms.scaling.scaling_library import (
    create_datastructures_for_reference_file,
    create_scaling_model,
    determine_best_unit_cell,
)
from dials.algorithms.scaling.scaling_utilities import log_memory_usage
from dials.array_family import flex
from dxtbx.model import ExperimentList
from libtbx import Auto

logger = logging.getLogger("dials")

# need to set up a scaling job to do scaling in addition to existing


class BatchScale(ScalingAlgorithm):
    def __init__(self, params, experiments, reflections):
        self.scaler = None
        self.params = params
        self.input_experiments = experiments
        self.input_reflections = reflections
        self.output_refl_files = []
        self.output_expt_files = []
        self.scaled_miller_array = None
        self.merging_statistics_result = None
        self.anom_merging_statistics_result = None
        self.filtering_results = None
        self.original_identifiers_map = {}
        self.prepare_input(experiments, reflections)
        self.create_model_and_scaler()
        logger.debug("Initialised scaling script object")
        log_memory_usage()

    def prepare_input(self, experiments, reflections):
        for r in reflections:
            r.unset_flags(flex.bool(r.size(), True), r.flags.scaled)

        #### Perform any non-batch cutting of the datasets, including the target dataset
        best_unit_cell = self.params.reflection_selection.best_unit_cell

        new_expts = ExperimentList([])
        for e in experiments:
            new_expts.append(e[0])  # single expt per elist
        if best_unit_cell is None:
            all_expts = ExperimentList([])
            for e in experiments:
                all_expts.extend(e)
            best_unit_cell = determine_best_unit_cell(all_expts)
        for reflection in reflections:
            if self.params.cut_data.d_min or self.params.cut_data.d_max:
                d = best_unit_cell.d(reflection["miller_index"])
                if self.params.cut_data.d_min:
                    sel = d < self.params.cut_data.d_min
                    reflection.set_flags(sel, reflection.flags.user_excluded_in_scaling)
                if self.params.cut_data.d_max:
                    sel = d > self.params.cut_data.d_max
                    reflection.set_flags(sel, reflection.flags.user_excluded_in_scaling)
            if self.params.cut_data.partiality_cutoff and "partiality" in reflection:
                reflection.set_flags(
                    reflection["partiality"] < self.params.cut_data.partiality_cutoff,
                    reflection.flags.user_excluded_in_scaling,
                )
            # need to scale intensities
            reflection["intensity.sum.value.original"] = reflection[
                "intensity.sum.value"
            ]
            reflection["intensity.sum.variance.original"] = reflection[
                "intensity.sum.variance"
            ]
            reflection["intensity.scale.value.original"] = reflection[
                "intensity.scale.value"
            ]
            reflection["intensity.scale.variance.original"] = reflection[
                "intensity.scale.variance"
            ]
            reflection["inverse_scale_factor.original"] = reflection[
                "inverse_scale_factor"
            ]
            reflection["intensity.sum.value"] /= reflection["inverse_scale_factor"]
            reflection["intensity.sum.variance"] /= (
                reflection["inverse_scale_factor"] ** 2
            )
            reflection["id.original"] = reflection["id"]
            del reflection["inverse_scale_factor"]
        for m in new_expts.scaling_models():
            del m
        if self.params.scaling_options.reference:
            # Set a suitable d_min in the case when we might have a model file
            d_min_for_structure_model = 2.0
            if self.params.cut_data.d_min not in (None, Auto):
                d_min_for_structure_model = self.params.cut_data.d_min
            expt, reflection_table = create_datastructures_for_reference_file(
                experiments[0],
                self.params.scaling_options.reference,
                self.params.anomalous,
                d_min=d_min_for_structure_model,
                k_sol=self.params.scaling_options.reference_model.k_sol,
                b_sol=self.params.scaling_options.reference_model.b_sol,
            )
            new_expts.append(expt)
            reflections.append(reflection_table)

        self.experiments = new_expts
        self.reflections = reflections

        for i, (e, t) in enumerate(zip(self.experiments, self.reflections)):
            self.original_identifiers_map[i] = {}
            for k in list(t.experiment_identifiers().keys()):
                self.original_identifiers_map[i][k] = t.experiment_identifiers()[k]
                del t.experiment_identifiers()[k]
            t["id"] = flex.int(t.size(), i)
            t.experiment_identifiers()[i] = e.identifier

    def create_model_and_scaler(self):
        """Create the scaling models and scaler."""

        self.experiments = create_scaling_model(
            self.params, self.experiments, self.reflections
        )
        logger.info("\nScaling models have been initialised for all experiments.")
        logger.info("%s%s%s", "\n", "=" * 80, "\n")

        self.scaler = create_scaler(self.params, self.experiments, self.reflections)

    def finish(self):
        # now copy results to original data
        self.scaler._set_outliers()
        assert self.input_reflections[0] is self.reflections[0]
        for i, inp in enumerate(self.input_reflections):
            del inp.experiment_identifiers()[i]
            for k, v in self.original_identifiers_map[i].items():
                inp.experiment_identifiers()[k] = v
            inp["inverse_scale_factor"] *= inp["inverse_scale_factor.original"]
            inp["intensity.sum.value"] = inp["intensity.sum.value.original"]
            inp["intensity.sum.variance"] = inp["intensity.sum.variance.original"]
            inp["intensity.scale.value"] = inp["intensity.scale.value.original"]
            inp["intensity.scale.variance"] = inp["intensity.scale.variance.original"]
            inp["id"] = inp["id.original"]
            del inp["intensity.sum.variance.original"]
            del inp["intensity.sum.value.original"]
            del inp["inverse_scale_factor.original"]
            del inp["intensity.scale.value.original"]
            del inp["intensity.scale.variance.original"]
            del inp["id.original"]

        for inp, scaled in zip(self.input_experiments, self.experiments):
            scale = scaled.scaling_model.components["scale"].parameters[0]
            B = scaled.scaling_model.components["decay"].parameters[0]
            for expt in inp:
                expt.scaling_model.components["scale"].parameters[0] *= scale
                expt.scaling_model.components["decay"].parameters[0] += B

    def export(self):
        """Output the datafiles"""
        import functools

        template = functools.partial(
            "scaled_{index:0{fmt:d}d}".format,
            fmt=len(str(len(self.input_experiments))),
        )
        for i, (expts, refls) in enumerate(
            zip(self.input_experiments, self.input_reflections)
        ):
            fname = template(index=i + 1)
            logger.info(f"Saving scaled reflections to {fname}.refl")
            refls.as_file(f"{fname}.refl")
            self.output_refl_files.append(f"{fname}.refl")
            logger.info(f"Saving scaled experiments to {fname}.expt")
            expts.as_file(f"{fname}.expt")
            self.output_expt_files.append(f"{fname}.expt")
        return self.output_expt_files, self.output_refl_files
