from __future__ import annotations

import copy
import logging
import random

import numpy as np

from cctbx import sgtbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.algorithms.symmetry.cosym import CosymAnalysis
from dials.array_family import flex
from dials.command_line.symmetry import change_of_basis_ops_to_minimum_cell
from dials.util.filter_reflections import filtered_arrays_from_experiments_reflections
from dxtbx.model import ExperimentList

logger = logging.getLogger("dials")


def batch_cosym_analysis(input_experiments, input_reflections, params):

    if params.seed is not None:
        flex.set_random_seed(params.seed)
        np.random.seed(params.seed)
        random.seed(params.seed)

    datasets = []

    all_expts = ExperimentList([])
    for expts in input_experiments:
        all_expts.extend(expts)
    best_unit_cell = determine_best_unit_cell(all_expts)

    def array_from_refl_expts(refls, expts):
        wavelength = np.mean([expt.beam.get_wavelength() for expt in expts])
        expt = copy.deepcopy(expts[0])
        expt.beam.set_wavelength(wavelength)
        expt.crystal.set_unit_cell(best_unit_cell)
        cb_ops = change_of_basis_ops_to_minimum_cell(
            ExperimentList([expt]),
            5.0,
            relative_length_tolerance=0.05,
            absolute_angle_tolerance=2.0,
        )
        refls["miller_index"] = cb_ops[0].apply(refls["miller_index"])
        for experiment in expts:
            experiment.crystal = experiment.crystal.change_basis(cb_ops[0])
            experiment.crystal.set_space_group(sgtbx.space_group())
        expt.crystal = expt.crystal.change_basis(cb_ops[0])
        expt.crystal.set_space_group(sgtbx.space_group())
        arr = filtered_arrays_from_experiments_reflections(
            [expt],
            [refls],
            outlier_rejection_after_filter=False,
            partiality_threshold=0.4,
        )
        return arr

    for refls, expts in zip(input_reflections, input_experiments):
        datasets.extend(array_from_refl_expts(refls, expts))

    datasets = [
        ma.as_non_anomalous_array().merge_equivalents().array() for ma in datasets
    ]

    cosym_analysis = CosymAnalysis(datasets, params)
    cosym_analysis.run()
    reindexing_ops = cosym_analysis.reindexing_ops
    datasets_ = list(set(cosym_analysis.dataset_ids))

    # Log reindexing operators
    logger.info("Reindexing operators:")
    for cb_op in set(reindexing_ops):
        datasets = [d for d, o in zip(datasets_, reindexing_ops) if o == cb_op]
        logger.info(f"{cb_op}: {datasets}")

    subgroup = cosym_analysis.best_subgroup
    if subgroup:
        acentric_sg = (
            subgroup["best_subsym"].space_group().build_derived_acentric_group()
        )
    unique_ids = set(cosym_analysis.dataset_ids)
    for i, (cb_op, dataset_id) in enumerate(zip(reindexing_ops, unique_ids)):
        cb_op = sgtbx.change_of_basis_op(cb_op)
        logger.debug(
            "Applying reindexing op %s to dataset %i", cb_op.as_xyz(), dataset_id
        )
        expts = input_experiments[dataset_id]
        refls = input_reflections[dataset_id]
        for expt in expts:
            expt.crystal = expt.crystal.change_basis(cb_op)
        if subgroup is not None:
            cb_op = subgroup["cb_op_inp_best"] * cb_op
            for expt in expts:
                expt.crystal = expt.crystal.change_basis(cb_op)
                expt.crystal.set_space_group(acentric_sg)
        else:
            for expt in expts:
                expt.crystal = expt.crystal.change_basis(cb_op)
        for expt in expts:
            expt.crystal.set_unit_cell(
                expt.crystal.get_space_group().average_unit_cell(
                    expt.crystal.get_unit_cell()
                )
            )
        refls["miller_index"] = cb_op.apply(refls["miller_index"])
        expts.as_file(f"processed_{i}.expt")
        refls.as_file(f"processed_{i}.refl")
