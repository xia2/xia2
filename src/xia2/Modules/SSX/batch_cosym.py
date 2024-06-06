from __future__ import annotations

import copy
import logging
import random

import numpy as np
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.algorithms.symmetry.cosym import CosymAnalysis, extract_reference_intensities
from dials.array_family import flex
from dials.command_line.symmetry import (
    apply_change_of_basis_ops,
    change_of_basis_ops_to_minimum_cell,
    eliminate_sys_absent,
)
from dials.util.filter_reflections import filtered_arrays_from_experiments_reflections
from dials.util.observer import Subject

from cctbx import sgtbx
from dxtbx.model import ExperimentList

logger = logging.getLogger("dials")


class BatchCosym(Subject):
    def __init__(self, experiments, reflections, params=None):
        super().__init__(events=["run_cosym", "performed_unit_cell_clustering"])
        self.params = params
        self.input_experiments = experiments
        self.input_reflections = reflections
        # self._experiments = None
        self._reflections = None
        self._output_expt_files = []
        self._output_refl_files = []

        if params.seed is not None:
            flex.set_random_seed(params.seed)
            np.random.seed(params.seed)
            random.seed(params.seed)

        datasets = []

        all_expts = ExperimentList([])
        for expts in experiments:
            all_expts.extend(expts)
        best_unit_cell = determine_best_unit_cell(all_expts)
        self._experiments = all_expts

        for i, (table, expts) in enumerate(
            zip(self.input_reflections, self.input_experiments)
        ):
            wavelength = np.mean([expt.beam.get_wavelength() for expt in expts])
            expt = copy.deepcopy(expts[0])
            expt.beam.set_wavelength(wavelength)
            expt.crystal.set_unit_cell(best_unit_cell)
            elist = ExperimentList([expt])
            cb_ops = change_of_basis_ops_to_minimum_cell(
                elist,
                params.lattice_symmetry_max_delta,
                params.relative_length_tolerance,
                params.absolute_angle_tolerance,
            )
            tables = eliminate_sys_absent(elist, [table])
            self.input_reflections[i] = tables[0]
            elist, tables = apply_change_of_basis_ops(elist, tables, cb_ops)
            self.input_reflections[i] = tables[0]
            for j_expt in self.input_experiments[i]:
                j_expt.crystal = j_expt.crystal.change_basis(cb_ops[0])
                j_expt.crystal.set_space_group(sgtbx.space_group())

            arr = filtered_arrays_from_experiments_reflections(
                elist,
                tables,
                outlier_rejection_after_filter=False,
                partiality_threshold=params.partiality_threshold,
            )
            datasets.extend(arr)

        datasets = [
            ma.as_non_anomalous_array().merge_equivalents().array() for ma in datasets
        ]

        if self.params.reference:
            reference_intensities, _ = extract_reference_intensities(
                params, wavelength=wavelength
            )
            datasets.append(reference_intensities)
            self.cosym_analysis = CosymAnalysis(
                datasets, self.params, seed_dataset=len(datasets) - 1
            )
        else:
            self.cosym_analysis = CosymAnalysis(datasets, params)

    @Subject.notify_event(event="run_cosym")
    def run(self):
        self.cosym_analysis.run()
        reindexing_ops = self.cosym_analysis.reindexing_ops
        datasets_ = list(set(self.cosym_analysis.dataset_ids))

        # Log reindexing operators
        logger.info("Reindexing operators:")
        for cb_op in set(reindexing_ops):
            datasets = [d for d, o in zip(datasets_, reindexing_ops) if o == cb_op]
            logger.info(f"{cb_op}: {datasets}")

        # now apply reindexing ops
        subgroup = self.cosym_analysis.best_subgroup
        if subgroup:
            acentric_sg = (
                subgroup["best_subsym"].space_group().build_derived_acentric_group()
            )
        if self.params.reference:
            unique_ids = sorted(set(self.cosym_analysis.dataset_ids))[:-1]
            reindexing_ops = reindexing_ops[:-1]
        else:
            unique_ids = set(self.cosym_analysis.dataset_ids)
        for i, (cb_op, dataset_id) in enumerate(zip(reindexing_ops, unique_ids)):
            cb_op = sgtbx.change_of_basis_op(cb_op)
            logger.debug(
                "Applying reindexing op %s to dataset %i", cb_op.as_xyz(), dataset_id
            )
            expts = self.input_experiments[dataset_id]
            refls = self.input_reflections[dataset_id]
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
            self._output_expt_files.append(f"processed_{i}.expt")
            self._output_refl_files.append(f"processed_{i}.refl")
