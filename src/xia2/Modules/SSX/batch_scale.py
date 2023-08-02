from __future__ import annotations

import concurrent.futures
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
from dxtbx.serialize import load
from libtbx import Auto

from xia2.Modules.SSX.data_reduction_definitions import FilePair

logger = logging.getLogger("dials")

# need to set up a scaling job to do scaling in addition to existing


def _finish_individual(working_directory, index, fp, new_refl, new_expt, template):
    table = flex.reflection_table.from_file(fp.refl)
    table["inverse_scale_factor"] *= new_refl["inverse_scale_factor"]
    table.unset_flags(flex.bool(table.size(), True), table.flags.scaled)
    table.set_flags(new_refl.get_flags(new_refl.flags.scaled), table.flags.scaled)
    table.unset_flags(
        flex.bool(table.size(), True), table.flags.user_excluded_in_scaling
    )
    table.set_flags(
        new_refl.get_flags(new_refl.flags.user_excluded_in_scaling),
        table.flags.user_excluded_in_scaling,
    )
    table.unset_flags(flex.bool(table.size(), True), table.flags.outlier_in_scaling)
    table.set_flags(
        new_refl.get_flags(new_refl.flags.outlier_in_scaling),
        table.flags.outlier_in_scaling,
    )

    scale = new_expt.scaling_model.components["scale"].parameters[0]
    B = new_expt.scaling_model.components["decay"].parameters[0]
    input_expt = load.experiment_list(fp.expt, check_format=False)
    for expt in input_expt:
        expt.scaling_model.components["scale"].parameters[0] *= scale
        expt.scaling_model.components["decay"].parameters[0] += B
    fname = template(index=index + 1)
    logger.info(f"Saving scaled reflections to {fname}.refl")
    table.as_file(working_directory / f"{fname}.refl")
    logger.info(f"Saving scaled experiments to {fname}.expt")
    input_expt.as_file(working_directory / f"{fname}.expt")
    return (
        index,
        FilePair(
            working_directory / f"{fname}.expt", working_directory / f"{fname}.refl"
        ),
    )


def _prepare_single_input(fp, best_unit_cell, params, index):

    table = flex.reflection_table.from_file(fp.refl)
    table.unset_flags(flex.bool(table.size(), True), table.flags.scaled)

    #### Perform any non-batch cutting of the datasets, including the target dataset

    if params.cut_data.d_min or params.cut_data.d_max:
        d = best_unit_cell.d(table["miller_index"])
        if params.cut_data.d_min:
            sel = d < params.cut_data.d_min
            table.set_flags(sel, table.flags.user_excluded_in_scaling)
        if params.cut_data.d_max:
            sel = d > params.cut_data.d_max
            table.set_flags(sel, table.flags.user_excluded_in_scaling)
    if params.cut_data.partiality_cutoff and "partiality" in table:
        table.set_flags(
            table["partiality"] < params.cut_data.partiality_cutoff,
            table.flags.user_excluded_in_scaling,
        )
    table["intensity.sum.value"] /= table["inverse_scale_factor"]
    table["intensity.sum.variance"] /= table["inverse_scale_factor"] ** 2
    del table["inverse_scale_factor"]

    return (index, table)


class BatchScale(ScalingAlgorithm):
    def __init__(self, working_directory, params, files_to_scale, nproc):
        self.scaler = None
        self.params = params
        self.nproc = nproc
        self.input_files = files_to_scale
        self.working_directory = working_directory
        self.outfiles = [None] * len(self.input_files)
        self.scaled_miller_array = None
        self.merging_statistics_result = None
        self.anom_merging_statistics_result = None
        self.filtering_results = None
        self.prepare_input(files_to_scale)
        self.create_model_and_scaler()
        logger.debug("Initialised scaling script object")
        log_memory_usage()

    def prepare_input(self, files_to_scale):

        best_unit_cell = self.params.reflection_selection.best_unit_cell
        reflections = [None] * len(files_to_scale)
        new_expts = ExperimentList([])
        if best_unit_cell is None:
            all_expts = ExperimentList([])
            for fp in files_to_scale:
                all_expts.extend(load.experiment_list(fp.expt, check_format=False))
            best_unit_cell = determine_best_unit_cell(all_expts)
        for fp in files_to_scale:
            new_expts.append(
                load.experiment_list(fp.expt, check_format=False)[0]
            )  # single expt per elist

        with concurrent.futures.ProcessPoolExecutor(max_workers=self.nproc) as pool:
            futures = [
                pool.submit(_prepare_single_input, fp, best_unit_cell, self.params, i)
                for i, fp in enumerate(files_to_scale)
            ]
            for future in concurrent.futures.as_completed(futures):
                i, table = future.result()
                reflections[i] = table

        for m in new_expts.scaling_models():
            del m
        if self.params.scaling_options.reference:
            # Set a suitable d_min in the case when we might have a model file
            d_min_for_structure_model = 2.0
            if self.params.cut_data.d_min not in (None, Auto):
                d_min_for_structure_model = self.params.cut_data.d_min
            expt, reflection_table = create_datastructures_for_reference_file(
                new_expts[0],
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
            for k in list(t.experiment_identifiers().keys()):
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
        # now apply scale factors to original data
        self.scaler._set_outliers()
        import functools

        template = functools.partial(
            "scaledinbatch_{index:0{fmt:d}d}".format,
            fmt=len(str(len(self.input_files))),
        )
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.nproc) as pool:
            futures = [
                pool.submit(
                    _finish_individual,
                    self.working_directory,
                    i,
                    fp,
                    new_refl,
                    new_expt,
                    template,
                )
                for i, (fp, new_refl, new_expt) in enumerate(
                    zip(self.input_files, self.reflections, self.experiments)
                )
            ]
            for future in concurrent.futures.as_completed(futures):
                i, fpout = future.result()
                self.outfiles[i] = fpout
