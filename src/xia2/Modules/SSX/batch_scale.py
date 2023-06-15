from __future__ import annotations

import itertools
import json
import logging
import time

from libtbx import Auto

from dials.algorithms.scaling.observers import (
    ScalingHTMLContextManager,
    ScalingSummaryContextManager,
)
from dials.algorithms.scaling.scale_and_filter import AnalysisResults, log_cycle_results
from dials.algorithms.scaling.scaler_factory import MultiScalerFactory, create_scaler
from dials.algorithms.scaling.scaling_library import (
    create_datastructures_for_reference_file,
    create_scaling_model,
    determine_best_unit_cell,
    merging_stats_from_scaled_array,
    scaled_data_as_miller_array,
    set_image_ranges_in_scaling_models,
)
from dials.algorithms.scaling.scaling_utilities import (
    DialsMergingStatisticsError,
    log_memory_usage,
)
from dials.algorithms.statistics.cc_half_algorithm import (
    CCHalfFromDials as deltaccscript,
)
from dials.array_family import flex
from dials.command_line.compute_delta_cchalf import phil_scope as deltacc_phil_scope
from dials.command_line.cosym import cosym
from dials.command_line.cosym import phil_scope as cosym_phil_scope
from dials.util.exclude_images import (
    exclude_image_ranges_for_scaling,
    get_valid_image_ranges,
)
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
    select_datasets_on_ids,
    update_imageset_ids,
)
import copy

from dials.algorithms.scaling.algorithm import ScalingAlgorithm

logger = logging.getLogger("dials")

# need to set up a scaling job to do scaling in addition to existing 

class BatchScale(ScalingAlgorithm):
    def __init__(self, params, experiments, reflections):
        self.scaler = None
        self.params = params
        self.input_experiments = copy.deepcopy(experiments)
        self.input_reflections = copy.deepcopy(reflections)
        self.output_refl_files = []
        self.output_expt_files = []
        self.scaled_miller_array = None
        self.merging_statistics_result = None
        self.anom_merging_statistics_result = None
        self.filtering_results = None
        self.prepare_input(experiments, reflections)
        self.create_model_and_scaler()
        logger.debug("Initialised scaling script object")
        log_memory_usage()

    def prepare_input(self, experiments, reflections):
        for r in reflections:
            r.unset_flags(flex.bool(r.size(), True), r.flags.scaled)

        #### Perform any non-batch cutting of the datasets, including the target dataset
        best_unit_cell = self.params.reflection_selection.best_unit_cell
        if best_unit_cell is None:
            from dxtbx.model import ExperimentList
            all_expts = ExperimentList([])
            new_expts = ExperimentList([])
            for e in experiments:
                all_expts.extend(e)
                new_expts.append(e[0])
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
            reflection["intensity.sum.value"] /= reflection["inverse_scale_factor"]
            reflection["intensity.sum.variance"] /= (reflection["inverse_scale_factor"]**2)
            del reflection["inverse_scale_factor"]

        if self.params.scaling_options.reference:
            # Set a suitable d_min in the case when we might have a model file
            d_min_for_structure_model = 2.0
            if self.params.cut_data.d_min not in (None, Auto):
                d_min_for_structure_model = self.params.cut_data.d_min
            expt, reflection_table = create_datastructures_for_reference_file(
                experiments,
                self.params.scaling_options.reference,
                self.params.anomalous,
                d_min=d_min_for_structure_model,
                k_sol=self.params.scaling_options.reference_model.k_sol,
                b_sol=self.params.scaling_options.reference_model.b_sol,
            )
            new_expts.append(expt)
            reflections.append(reflection_table)
        
        for m in new_expts.scaling_models():
            del m
        self.experiments = new_expts
        self.reflections = reflections
        for i, (e, t) in enumerate(zip(self.experiments, self.reflections)):
            print(e, t, i)
            for k in list(t.experiment_identifiers().keys()):
                del t.experiment_identifiers()[k]
            t["id"] = flex.int(t.size(), i)
            print(e.identifier)
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
        for inp, scaled in zip(self.input_reflections, self.reflections):
            inp["inverse_scale_factor"] *= scaled["inverse_scale_factor"]
            inp["inverse_scale_factor_variance"] += scaled["inverse_scale_factor_variance"]
            flags = scaled.get_flags(scaled.flags.scaled)
            inp.unset_flags(flex.bool(inp.size(), True), inp.flags.scaled)
            inp.set_flags(flags, inp.flags.scaled)
            sel = (
                inp["inverse_scale_factor"]
                < self.params.cut_data.small_scale_cutoff
            )
            inp.set_flags(sel, inp.flags.excluded_for_scaling)
        for inp, scaled in zip(self.input_experiments, self.experiments):
            scale = scaled.scaling_model.components["scale"].parameters[0]
            B = scaled.scaling_model.components["decay"].parameters[0]
            for expt in inp:
                expt.scaling_model.components["scale"].parameters[0] *= scale
                expt.scaling_model.components["decay"].parameters[0] += B

    def export(self):
        """Output the datafiles for cosym.

        This includes the cosym.json, reflections and experiments files."""
        import functools
        template = functools.partial(
            "scaled_{index:0{fmt:d}d}".format,
            fmt=len(str(len(self.input_experiments))),
        )
        for i, (expts, refls) in enumerate(
            zip(self.input_experiments, self.input_reflections)
        ):
            fname = template(index=i)
            logger.info(f"Saving reindexed reflections to {fname}.refl")
            refls.as_file(f"{fname}.refl")
            self.output_refl_files.append(f"{fname}.refl")
            logger.info(f"Saving reindexed experiments to {fname}.expt")
            expts.as_file(f"{fname}.expt")
            self.output_expt_files.append(f"{fname}.expt")
        return self.output_expt_files, self.output_refl_files