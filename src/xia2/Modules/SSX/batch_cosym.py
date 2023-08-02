from __future__ import annotations

import copy
import logging
import random

import numpy as np

from cctbx import sgtbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.algorithms.symmetry.cosym import CosymAnalysis
from dials.array_family import flex
from dials.command_line.symmetry import (
    apply_change_of_basis_ops,
    change_of_basis_ops_to_minimum_cell,
    eliminate_sys_absent,
)
from dials.util.filter_reflections import filtered_arrays_from_experiments_reflections
from dials.util.observer import Subject
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_definitions import FilePair

logger = logging.getLogger("dials")

import concurrent.futures


def _prepare_file_for_cosym(fp, params, best_unit_cell, index):
    expts = load.experiment_list(fp.expt, check_format=False)
    table = flex.reflection_table.from_file(fp.refl)
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
    elist, tables = apply_change_of_basis_ops(elist, tables, cb_ops)
    for j_expt in expts:
        j_expt.crystal = j_expt.crystal.change_basis(cb_ops[0])
        j_expt.crystal.set_space_group(sgtbx.space_group())

    arr = filtered_arrays_from_experiments_reflections(
        elist,
        tables,
        outlier_rejection_after_filter=False,
        partiality_threshold=params.partiality_threshold,
    )[0]
    tables[0].as_file(f"tmp{index}.refl")
    expts.as_file(f"tmp{index}.expt")

    return (index, arr.as_non_anomalous_array().merge_equivalents().array())


def _reindex_data(
    working_directory, cb_op, dataset_id, subgroup, acentric_sg, template
):

    cb_op = sgtbx.change_of_basis_op(cb_op)
    logger.debug("Applying reindexing op %s to dataset %i", cb_op.as_xyz(), dataset_id)
    expts = load.experiment_list(f"tmp{dataset_id}.expt", check_format=False)
    refls = flex.reflection_table.from_file(f"tmp{dataset_id}.refl")

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

    outexpt = template(index=dataset_id + 1) + ".expt"
    outref = template(index=dataset_id + 1) + ".refl"

    expts.as_file(working_directory / outexpt)
    refls.as_file(working_directory / outref)
    return (
        dataset_id,
        FilePair(working_directory / outexpt, working_directory / outref),
    )


class BatchCosym(Subject):
    def __init__(self, working_directory, files_for_reindex, params=None, nproc=1):
        super().__init__(events=["run_cosym", "performed_unit_cell_clustering"])
        self.working_directory = working_directory
        self.params = params
        self.nproc = nproc

        self.output_files = [None] * len(files_for_reindex)

        if params.seed is not None:
            flex.set_random_seed(params.seed)
            np.random.seed(params.seed)
            random.seed(params.seed)

        datasets = []

        all_expts = ExperimentList([])
        for fp in files_for_reindex:
            expts = load.experiment_list(fp.expt, check_format=False)
            all_expts.extend(expts)
        best_unit_cell = determine_best_unit_cell(all_expts)
        self._experiments = all_expts
        self.params.space_group = all_expts[0].crystal.get_space_group().info()

        datasets = [0] * len(files_for_reindex)

        with concurrent.futures.ProcessPoolExecutor(max_workers=self.nproc) as pool:
            futures = [
                pool.submit(_prepare_file_for_cosym, fp, params, best_unit_cell, i)
                for i, fp in enumerate(files_for_reindex)
            ]
            for future in concurrent.futures.as_completed(futures):
                i, dataset = future.result()
                datasets[i] = dataset
                FileHandler.record_temporary_file(
                    self.working_directory / f"tmp{i}.refl"
                )
                FileHandler.record_temporary_file(
                    self.working_directory / f"tmp{i}.expt"
                )

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
        unique_ids = set(self.cosym_analysis.dataset_ids)
        import functools

        template = functools.partial(
            "processed_{index:0{fmt:d}d}".format,
            fmt=len(str(len(unique_ids))),
        )

        with concurrent.futures.ProcessPoolExecutor(max_workers=self.nproc) as pool:
            futures = [
                pool.submit(
                    _reindex_data,
                    self.working_directory,
                    cb_op,
                    dataset_id,
                    subgroup,
                    acentric_sg,
                    template,
                )
                for cb_op, dataset_id in zip(reindexing_ops, unique_ids)
            ]
            for future in concurrent.futures.as_completed(futures):
                i, fp = future.result()
                self.output_files[i] = fp
