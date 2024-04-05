# -*- coding: utf-8 -*-
from __future__ import annotations

import concurrent.futures
import copy
import functools
import json
import logging
import math
import os
import random
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from cctbx import crystal, miller, sgtbx, uctbx
from dials.algorithms.merging.merge import (
    merge_scaled_array_to_mtz_with_report_collection,
)
from dials.algorithms.merging.reporting import generate_html_report as merge_html_report
from dials.algorithms.scaling.algorithm import ScalingAlgorithm
from dials.array_family import flex
from dials.command_line.cluster_unit_cell import do_cluster_analysis
from dials.command_line.cluster_unit_cell import phil_scope as cluster_phil_scope
from dials.command_line.cosym import cosym
from dials.command_line.cosym import phil_scope as cosym_phil_scope
from dials.command_line.cosym import register_default_cosym_observers
from dials.command_line.merge import phil_scope as merge_phil_scope
from dials.command_line.scale import phil_scope as scaling_phil_scope
from dials.util.resolution_analysis import resolution_cc_half
from dxtbx.model import Crystal, ExperimentList
from dxtbx.serialize import load
from iotbx.phil import parse

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.batch_cosym import BatchCosym
from xia2.Modules.SSX.data_reduction_definitions import FilePair, ReductionParams
from xia2.Modules.SSX.reporting import condensed_unit_cell_info
from xia2.Modules.SSX.util import log_to_file, run_in_directory

xia2_logger = logging.getLogger(__name__)


@dataclass(eq=False)
class CrystalsData:
    # Holds dxtbx.model.crystal data for an experimentlist, for use in filtering
    identifiers: List[str]
    crystals: List[Crystal]
    keep_all_original: bool = True
    lattice_ids: List[int] = field(default_factory=list)


CrystalsDict = Dict[str, CrystalsData]
# CrystalsDict: stores crystal data contained in each expt file, for use in
# filtering without needing to keep expt files open.


def load_crystal_data_from_new_expts(new_data: List[FilePair]) -> CrystalsDict:
    data: CrystalsDict = {}
    n = 0
    for file_pair in new_data:
        new_expts = load.experiment_list(file_pair.expt, check_format=False)
        if new_expts:
            # copy to avoid need to keep expt file open
            data[str(file_pair.expt)] = CrystalsData(
                copy.deepcopy(new_expts.identifiers()),
                copy.deepcopy(new_expts.crystals()),
            )
            n += len(new_expts)
        else:
            xia2_logger.warning(f"No crystals found in {str(file_pair.expt)}")
            data[str(file_pair.expt)] = CrystalsData([], [])
    xia2_logger.info(f"Found {n} integrated crystals")
    return data


def filter_(
    working_directory: Path,
    integrated_data: list[FilePair],
    reduction_params: ReductionParams,
) -> Tuple[CrystalsDict, uctbx.unit_cell, sgtbx.space_group_info]:

    crystals_data = load_crystal_data_from_new_expts(integrated_data)
    if not any(v.crystals for v in crystals_data.values()):
        raise ValueError(
            "No integrated images in integrated datafiles, processing finished."
        )
    space_group = check_consistent_space_group(crystals_data)
    good_crystals_data = filter_new_data(
        working_directory, crystals_data, reduction_params
    )
    if not any(v.crystals for v in good_crystals_data.values()):
        raise ValueError("No crystals remain after filtering, processing finished.")
    best_unit_cell = determine_best_unit_cell_from_crystals(good_crystals_data)
    return good_crystals_data, best_unit_cell, space_group


def split_integrated_data(
    good_crystals_data, integrated_data, reduction_params
) -> List[ProcessingBatch]:
    new_batches_to_process = split_filtered_data(
        integrated_data,
        good_crystals_data,
        reduction_params.batch_size,
    )
    return new_batches_to_process


def assess_for_indexing_ambiguities(
    space_group: sgtbx.space_group_info,
    unit_cell: uctbx.unit_cell,
    max_delta: float = 0.5,
) -> bool:

    # first test for 'true' indexing ambiguities - where the space group symmetry
    # is lower than the lattice symmetry
    cs = crystal.symmetry(unit_cell=unit_cell, space_group=sgtbx.space_group())
    # Get cell reduction operator
    cb_op_inp_minimum = cs.change_of_basis_op_to_minimum_cell()
    # New symmetry object with changed basis
    minimum_symmetry = cs.change_basis(cb_op_inp_minimum)

    # Get the exact lattice symmetry
    exact_lattice_group = sgtbx.lattice_symmetry_group(
        minimum_symmetry.unit_cell(),
        max_delta=0,
        enforce_max_delta_for_generated_two_folds=True,
    )
    need_to_assess_1 = exact_lattice_group.order_p() > space_group.group().order_p()
    human_readable = {True: "yes", False: "no"}

    # now test for accidental ambiguities due to lattice parameters being close to a higher symmetry
    # Get highest symmetry compatible with lattice
    potential_lattice_group = sgtbx.lattice_symmetry_group(
        minimum_symmetry.unit_cell(),
        max_delta=max_delta,
        enforce_max_delta_for_generated_two_folds=True,
    )
    need_to_assess_2 = potential_lattice_group.order_p() > exact_lattice_group.order_p()
    xia2_logger.info(
        "Indexing ambiguity assessment:\n"
        f"  Space group: {str(space_group)}\n"
        f"  Lattice group: {str(exact_lattice_group.info())}\n"
        f"  Highest symmetry lattice group (within tolerance): {str(potential_lattice_group.info())}\n"
        f"  Indexing ambiguities due to symmetry: {human_readable[need_to_assess_1]}\n"
        f"  Potential misindexing due to similar lattice parameters: {human_readable[need_to_assess_2]}"
    )
    return need_to_assess_1 or need_to_assess_2


def check_consistent_space_group(crystals_dict: CrystalsDict) -> sgtbx.space_group_info:
    # check all space groups are the same and return that group
    sgs = set()
    for v in crystals_dict.values():
        sgs.update({c.get_space_group().type().number() for c in v.crystals})
    if len(sgs) > 1:
        sg_nos = ",".join(str(i) for i in sgs)
        raise ValueError(
            f"Multiple space groups found, numbers: {sg_nos}\n"
            "All integrated data must be in the same space group"
        )
    return sgtbx.space_group_info(number=list(sgs)[0])


def determine_best_unit_cell_from_crystals(
    crystals_dict: CrystalsDict,
) -> uctbx.unit_cell:
    """Set the median unit cell as the best cell, for consistent d-values across
    experiments."""
    uc_params = [flex.double() for i in range(6)]
    for v in crystals_dict.values():
        for c in v.crystals:
            unit_cell = c.get_recalculated_unit_cell() or c.get_unit_cell()
            for i, p in enumerate(unit_cell.parameters()):
                uc_params[i].append(p)
    best_unit_cell = uctbx.unit_cell(parameters=[flex.median(p) for p in uc_params])
    return best_unit_cell


def filter_new_data(
    working_directory: Path,
    crystals_data: dict,
    reduction_params: ReductionParams,
) -> CrystalsDict:
    if reduction_params.cluster_threshold:
        good_crystals_data = run_uc_cluster(
            working_directory,
            crystals_data,
            reduction_params.cluster_threshold,
        )
    elif reduction_params.central_unit_cell:
        new_best_unit_cell = reduction_params.central_unit_cell
        good_crystals_data = select_crystals_close_to(
            crystals_data,
            new_best_unit_cell,
            reduction_params.absolute_angle_tolerance,
            reduction_params.absolute_length_tolerance,
        )
    elif (
        reduction_params.absolute_angle_tolerance
        and reduction_params.absolute_length_tolerance
    ):
        # calculate the median unit cell
        new_best_unit_cell = determine_best_unit_cell_from_crystals(crystals_data)
        good_crystals_data = select_crystals_close_to(
            crystals_data,
            new_best_unit_cell,
            reduction_params.absolute_angle_tolerance,
            reduction_params.absolute_length_tolerance,
        )
    else:  # join all data for splitting
        good_crystals_data = crystals_data
        xia2_logger.info("No unit cell filtering applied")

    return good_crystals_data


def run_uc_cluster(
    working_directory: Path, crystals_dict: CrystalsDict, threshold: float = 1000
) -> CrystalsDict:
    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)

    with open(os.devnull, "w") as devnull, run_in_directory(
        working_directory
    ), record_step("dials.cluster_unit_cell"), log_to_file(
        "dials.cluster_unit_cell.log"
    ):
        sys.stdout = devnull  # block printing from cluster_uc

        # first extract the params and set the threshold
        params = cluster_phil_scope.extract()
        params.threshold = threshold
        # Now create the crystal symmetries, and keep track of the ids
        crystal_symmetries = []
        n_tot = 0
        for k, v in crystals_dict.items():
            symmetries = [
                crystal.symmetry(
                    unit_cell=c.get_unit_cell(),
                    space_group=c.get_space_group(),
                )
                for c in v.crystals
            ]
            crystal_symmetries.extend(symmetries)
            n_this = len(symmetries)
            ids = list(range(n_tot, n_tot + n_this))
            n_tot += n_this
            crystals_dict[k].lattice_ids = ids
        # run the main work function of dials.cluster_unit_cell
        clusters = do_cluster_analysis(crystal_symmetries, params)
        clusters.sort(key=lambda x: len(x), reverse=True)
        main_cluster = clusters[0]
        xia2_logger.info(condensed_unit_cell_info(clusters))
        xia2_logger.info(
            f"Selecting {len(main_cluster)} crystals from the largest cluster"
        )
        main_ids = set(main_cluster.lattice_ids)
        # Work out which subset of the input data corresponds to the main cluster
        good_crystals_data: CrystalsDict = {}
        for k, v in crystals_dict.items():
            ids_this = set(v.lattice_ids).intersection(main_ids)
            if len(ids_this) < len(v.lattice_ids):
                identifiers = []
                crystals = []
                for i, id_ in enumerate(v.lattice_ids):
                    if id_ in ids_this:
                        identifiers.append(v.identifiers[i])
                        crystals.append(v.crystals[i])
                good_crystals_data[k] = CrystalsData(
                    identifiers=identifiers,
                    crystals=crystals,
                    keep_all_original=False,
                )
            else:
                good_crystals_data[k] = crystals_dict[k]
    sys.stdout = sys.__stdout__  # restore printing
    return good_crystals_data


def merge(
    working_directory: Path,
    scaled_array: miller.array,
    experiments: ExperimentList,
    d_min: float = None,
    best_unit_cell: Optional[uctbx.unit_cell] = None,
    partiality_threshold: float = 0.25,
    name: str = "",
) -> MergeResult:
    logfile = "dials.merge.log"
    filename = "merged.mtz"
    html_file = "dials.merge.html"
    json_file = "dials.merge.json"
    if name and name != "merged":
        logfile = f"dials.merge.{name}.log"
        filename = f"{name}.mtz"
        html_file = f"dials.merge.{name}.html"
        json_file = f"dials.merge.{name}.json"
    with run_in_directory(working_directory), log_to_file(
        logfile
    ) as dials_logger, record_step("dials.merge"):
        params = merge_phil_scope.extract()
        params.output.additional_stats = True
        input_ = "Input parameters:\n"
        if d_min:
            params.d_min = d_min
            input_ += f"  d_min = {d_min}\n"
        if best_unit_cell:
            params.best_unit_cell = best_unit_cell
            input_ += f"  best_unit_cell = {best_unit_cell.parameters()}\n"
        params.partiality_threshold = partiality_threshold
        input_ += f"  partiality_threshold = {partiality_threshold}"
        params.assess_space_group = False
        params.combine_partials = False

        dials_logger.info(input_)
        mtz_file, json_data = merge_scaled_array_to_mtz_with_report_collection(
            params,
            experiments,
            scaled_array,
            applied_d_min=d_min,
        )
        # mtz_file, json_data = merge_data_to_mtz_with_report_collection(
        #    params, experiments, [reflection_table]
        # )
        dials_logger.info(f"\nWriting reflections to {filename}")
        out = StringIO()
        mtz_file.show_summary(out=out)
        dials_logger.info(out.getvalue())
        mtz_file.write(filename)
        with open(json_file, "w") as f:
            json.dump(json_data, f, indent=2)
        merge_html_report(json_data, html_file)
        result = MergeResult(
            working_directory / filename,
            working_directory / logfile,
            working_directory / json_file,
            working_directory / html_file,
            name=name,
        )
        wlkey = list(json_data.keys())[0]
        try:
            table_1_stats = json_data[wlkey]["table_1_stats"]
        except KeyError:
            table_1_stats = ""
        result.summary = (
            (
                f"Merged {len(experiments)} crystals in {', '.join(name.split('.'))}\n"
                if name != "merged"
                else ""
            )
            + f"Merged mtz file: {filename}\n"
            + f"{table_1_stats}"
        )

    return result


scaled_cols_to_keep = [
    "miller_index",
    "inverse_scale_factor",
    "intensity.scale.value",
    "intensity.scale.variance",
    "flags",
    "id",
    "partiality",
    "partial_id",
    "d",
    "qe",
    "dqe",
    "lp",
]


def trim_table_for_merge(table):
    for k in list(table.keys()):
        if k not in scaled_cols_to_keep:
            del table[k]


def _wrap_extend_expts(first_elist, second_elist):
    try:
        first_elist.extend(second_elist)
    except RuntimeError as e:
        raise ValueError(
            "Unable to combine experiments, check for datafiles containing duplicate experiments.\n"
            + f"  Specific error message encountered:\n  {e}"
        )


@dataclass
class MergeResult:
    merge_file: Path
    logfile: Path
    jsonfile: Optional[Path] = None
    htmlfile: Optional[Path] = None
    summary: str = ""
    table_1_stats: str = ""
    name: str = ""


def _extract_scaling_params(reduction_params):
    # scaling options for scaling without a reference
    extra_defaults = """
        model=KB
        scaling_options.full_matrix=False
        weighting.error_model.reset_error_model=True
        scaling_options.outlier_rejection=simple
        scaling_options.outlier_zmax=4.0
        reflection_selection.intensity_choice=sum
        reflection_selection.method=intensity_ranges
        reflection_selection.Isigma_range=2.0,0.0
        output.additional_stats=True
        scaling_options.nproc=8
    """
    xia2_phil = f"""
        anomalous={reduction_params.anomalous}
        reflection_selection.min_partiality={reduction_params.partiality_threshold}
        cut_data.partiality_cutoff={reduction_params.partiality_threshold}
    """
    if reduction_params.d_min:
        xia2_phil += f"\ncut_data.d_min={reduction_params.d_min}"
    if reduction_params.central_unit_cell:
        vals = ",".join(
            str(round(p, 4)) for p in reduction_params.central_unit_cell.parameters()
        )
        xia2_phil += f"\nreflection_selection.best_unit_cell={vals}"

    if reduction_params.scaling_phil:
        itpr = scaling_phil_scope.command_line_argument_interpreter()
        try:
            user_phil = itpr.process(args=[os.fspath(reduction_params.scaling_phil)])[0]
            working_phil = scaling_phil_scope.fetch(
                sources=[
                    parse(extra_defaults),
                    user_phil,
                    parse(xia2_phil),
                ]
            )
            # Note, the order above makes the xia2_phil take precedent
            # over the user phil, which takes precedent over the extra defaults
        except Exception as e:
            xia2_logger.warning(
                f"Unable to interpret {reduction_params.scaling_phil} as a scaling phil file. Error:\n{e}"
            )
            working_phil = scaling_phil_scope.fetch(
                sources=[
                    parse(extra_defaults),
                    parse(xia2_phil),
                ]
            )
    else:
        working_phil = scaling_phil_scope.fetch(
            sources=[
                parse(extra_defaults),
                parse(xia2_phil),
            ]
        )
    diff_phil = scaling_phil_scope.fetch_diff(source=working_phil)
    params = working_phil.extract()
    return params, diff_phil


def _extract_scaling_params_for_scale_against_reference(reduction_params, name):
    extra_defaults = """
        model=KB
        scaling_options.full_matrix=False
        weighting.error_model.reset_error_model=True
        scaling_options.outlier_rejection=simple
        scaling_options.outlier_zmax=4.0
        reflection_selection.intensity_choice=sum
        reflection_selection.method=intensity_ranges
        reflection_selection.Isigma_range=2.0,0.0
        output.additional_stats=True
        cut_data.small_scale_cutoff=1e-9
    """
    xia2_phil = f"""
        anomalous={reduction_params.anomalous}
        reflection_selection.min_partiality={reduction_params.partiality_threshold}
        cut_data.partiality_cutoff={reduction_params.partiality_threshold}
        output.experiments={name}.expt
        output.reflections={name}.refl
        output.html=dials.scale.{name}.html
        scaling_options.reference={str(reduction_params.reference)}
        scaling_options.reference_model.k_sol={reduction_params.reference_ksol}
        scaling_options.reference_model.b_sol={reduction_params.reference_bsol}
    """
    if reduction_params.d_min:
        xia2_phil += f"\ncut_data.d_min={reduction_params.d_min}"
    if reduction_params.central_unit_cell:
        vals = ",".join(
            str(round(p, 4)) for p in reduction_params.central_unit_cell.parameters()
        )
        xia2_phil += f"\nreflection_selection.best_unit_cell={vals}"

    if reduction_params.scaling_phil:
        itpr = scaling_phil_scope.command_line_argument_interpreter()
        try:
            user_phil = itpr.process(args=[os.fspath(reduction_params.scaling_phil)])[0]
            working_phil = scaling_phil_scope.fetch(
                sources=[
                    parse(extra_defaults),
                    user_phil,
                    parse(xia2_phil),
                ]
            )
            # Note, the order above makes the xia2_phil take precedent
            # over the user phil, which takes precedent over the extra defaults
        except Exception as e:
            xia2_logger.warning(
                f"Unable to interpret {reduction_params.scaling_phil} as a scaling phil file. Error:\n{e}"
            )
            working_phil = scaling_phil_scope.fetch(
                sources=[
                    parse(extra_defaults),
                    parse(xia2_phil),
                ]
            )
    else:
        working_phil = scaling_phil_scope.fetch(
            sources=[
                parse(extra_defaults),
                parse(xia2_phil),
            ]
        )
    diff_phil = scaling_phil_scope.fetch_diff(source=working_phil)
    params = working_phil.extract()
    return params, diff_phil


@dataclass
class ProgramResult:
    exptfile: Path
    reflfile: Path
    logfile: Path
    htmlfile: Optional[Path]
    jsonfile: Optional[Path]
    resolutionlimit: Optional[float] = None


def scale_against_reference(
    working_directory: Path,
    batch: ProcessingBatch,
    reduction_params,
    name="",
) -> ProgramResult:
    logfile = f"dials.scale.{name}.log"
    with run_in_directory(working_directory), log_to_file(logfile) as dials_logger:
        # Setup scaling
        # expts = load.experiment_list(files.expt, check_format=False)
        # table = flex.reflection_table.from_file(files.refl)
        expts, table = combined_files_for_batch(batch)
        params, diff_phil = _extract_scaling_params_for_scale_against_reference(
            reduction_params, name
        )
        dials_logger.info(
            "The following parameters have been modified:\n"
            # + f"input.experiments = {files.expt}\n"
            # + f"input.reflections = {files.refl}\n"
            + f"{diff_phil.as_str()}"
        )
        # Run the scaling using the algorithm class to give access to scaler
        scaler = ScalingAlgorithm(params, expts, [table])
        scaler.run()
        scaled_expts, scaled_table = scaler.finish()

        dials_logger.info(f"Saving scaled experiments to {params.output.experiments}")
        scaled_expts.as_file(params.output.experiments)
        dials_logger.info(f"Saving scaled reflections to {params.output.reflections}")
        scaled_table.as_file(params.output.reflections)

    return ProgramResult(
        working_directory / params.output.experiments,
        working_directory / params.output.reflections,
        working_directory / logfile,
        None,
        None,
    )


def scale_parallel_batches(
    working_directory, batches: List[ProcessingBatch], reduction_params
) -> Tuple[List[ProcessingBatch], List[float]]:
    # scale multiple batches in parallel
    scaled_results = [ProcessingBatch() for _ in range(len(batches))]
    d_mins = []
    batch_template = functools.partial(
        "batch{index:0{maxindexlength:d}d}".format,
        maxindexlength=len(str(len(batches))),
    )
    jobs = {f"{batch_template(index=i+1)}": fp for i, fp in enumerate(batches)}
    # xia2_logger.notice(banner("Scaling"))  # type: ignore
    with record_step("dials.scale (parallel)"), concurrent.futures.ProcessPoolExecutor(
        max_workers=min(reduction_params.nproc, len(batches))
    ) as pool:
        scale_futures: Dict[Any, int] = {
            pool.submit(
                scale_on_batches,
                working_directory,
                [batch],
                reduction_params,
                name,
            ): i
            for i, (name, batch) in enumerate(jobs.items())
        }
        for future in concurrent.futures.as_completed(scale_futures):
            try:
                result = future.result()
                idx = scale_futures[future]
            except Exception as e:
                xia2_logger.warning(f"Unsuccessful scaling of group. Error:\n{e}")
            else:
                xia2_logger.info(f"Completed scaling of data reduction batch {idx+1}")
                scaled_results[idx].add_filepair(
                    FilePair(result.exptfile, result.reflfile)
                )
                FileHandler.record_log_file(
                    result.logfile.name.rstrip(".log"), result.logfile
                )
                d_mins.append(result.resolutionlimit)

    if not scaled_results:
        raise ValueError("No groups successfully scaled")
    return scaled_results, d_mins


def scale_on_batches(
    working_directory: Path,
    batches_to_scale: List[ProcessingBatch],
    reduction_params: ReductionParams,
    name="",
) -> ProgramResult:
    logfile = "dials.scale.log"
    if name:
        logfile = f"dials.scale.{name}.log"
    with run_in_directory(working_directory), log_to_file(
        logfile
    ) as dials_logger, record_step("dials.scale"):
        # Setup scaling
        input_ = ""

        all_expts = ExperimentList([])
        tables = []
        for batch in batches_to_scale:
            for fp in batch.filepairs:
                table = flex.reflection_table.from_file(fp.refl)
                expts = load.experiment_list(fp.expt, check_format=False)
                if fp in batch.filepair_to_good_identifiers:
                    ids = batch.filepair_to_good_identifiers[fp]
                    if len(ids) < len(expts):
                        expts.select_on_experiment_identifiers(list(ids))
                        table = table.select_on_experiment_identifiers(list(ids))
                        table.reset_ids()
                all_expts.extend(expts)
                tables.append(table)
        expts = all_expts

        params, diff_phil = _extract_scaling_params(reduction_params)
        dials_logger.info(
            "The following parameters have been modified:\n"
            + input_
            + f"{diff_phil.as_str()}"
        )

        # Run the scaling using the algorithm class to give access to scaler
        scaler = ScalingAlgorithm(params, expts, tables)
        scaler.run()
        try:
            d_min = resolution_cc_half(
                scaler.merging_statistics_result, limit=0.3
            ).d_min
        except RuntimeError:
            d_min = None
        scaled_expts, scaled_table = scaler.finish()
        if name:
            out_expt = f"scaled.{name}.expt"
            out_refl = f"scaled.{name}.refl"
        else:
            out_expt = "scaled.expt"
            out_refl = "scaled.refl"

        dials_logger.info(f"Saving scaled experiments to {out_expt}")
        scaled_expts.as_file(out_expt)
        dials_logger.info(f"Saving scaled reflections to {out_refl}")
        scaled_table.as_file(out_refl)

    return ProgramResult(
        working_directory / out_expt,
        working_directory / out_refl,
        working_directory / logfile,
        None,
        None,
        d_min,
    )


def _extract_cosym_params(reduction_params, index):
    xia2_phil = f"""
        space_group={reduction_params.space_group}
        output.html=dials.cosym.{index}.html
        output.json=dials.cosym.{index}.json
        output.reflections=processed_{index}.refl
        output.experiments=processed_{index}.expt
    """
    # if reduction_params.reference:
    #    xia2_phil += f"\nreference={reduction_params.reference}"
    #    xia2_phil += f"\nreference_model.k_sol={reduction_params.reference_ksol}"
    #    xia2_phil += f"\nreference_model.b_sol={reduction_params.reference_bsol}"
    extra_defaults = f"""
        min_i_mean_over_sigma_mean=0.5
        unit_cell_clustering.threshold=None
        lattice_symmetry_max_delta={reduction_params.lattice_symmetry_max_delta}
        partiality_threshold={reduction_params.partiality_threshold}
        cc_weights=sigma
        weights=standard_error
    """
    if reduction_params.d_min:
        # note - allow user phil to override the overall xia2 d_min - might
        # not want to use full resolution range for symmetry analysis
        extra_defaults += f"\nd_min={reduction_params.d_min}"
    if reduction_params.cosym_phil:
        itpr = cosym_phil_scope.command_line_argument_interpreter()
        try:
            user_phil = itpr.process(args=[os.fspath(reduction_params.cosym_phil)])[0]
            working_phil = cosym_phil_scope.fetch(
                sources=[
                    parse(extra_defaults),
                    user_phil,
                    parse(xia2_phil),
                ]
            )
            # Note, the order above makes the xia2_phil take precedent
            # over the user phil, which takes precedent over the extra defaults
        except Exception as e:
            xia2_logger.warning(
                f"Unable to interpret {reduction_params.cosym_phil} as a cosym phil file. Error:\n{e}"
            )
            working_phil = cosym_phil_scope.fetch(
                sources=[
                    parse(extra_defaults),
                    parse(xia2_phil),
                ]
            )
    else:
        working_phil = cosym_phil_scope.fetch(
            sources=[
                parse(extra_defaults),
                parse(xia2_phil),
            ]
        )
    diff_phil = cosym_phil_scope.fetch_diff(source=working_phil)
    cosym_params = working_phil.extract()
    return cosym_params, diff_phil


def combined_files_for_batch(batch):
    all_expts = ExperimentList([])
    tables = []
    for fp in batch.filepairs:
        table = flex.reflection_table.from_file(fp.refl)
        expts = load.experiment_list(fp.expt, check_format=False)
        if fp in batch.filepair_to_good_identifiers:
            ids = batch.filepair_to_good_identifiers[fp]
            if len(ids) < len(expts):
                expts.select_on_experiment_identifiers(list(ids))
                table = table.select_on_experiment_identifiers(list(ids))
                table.reset_ids()
        all_expts.extend(expts)
        tables.append(table)
    if len(tables) > 1:
        table = flex.reflection_table.concat(tables)
        table.reset_ids()
    else:
        table = tables[0]
    expts = all_expts
    return expts, table


def individual_cosym(
    working_directory: Path,
    batch: ProcessingBatch,
    index: int,
    reduction_params,
) -> ProgramResult:
    """Run  cosym an the expt and refl file."""
    logfile = f"dials.cosym.{index}.log"
    with run_in_directory(working_directory), record_step("dials.cosym"), log_to_file(
        logfile
    ) as dials_logger:
        cosym_params, diff_phil = _extract_cosym_params(reduction_params, index)
        dials_logger.info(
            "The following parameters have been modified:\n"
            # + f"input.experiments = {files.expt}\n"
            # + f"input.reflections = {files.refl}\n"
            + f"{diff_phil.as_str()}"
        )
        # cosym_params.cc_star_threshold = 0.1
        # cosym_params.angular_separation_threshold = 5
        expts, table = combined_files_for_batch(batch)

        tables = table.split_by_experiment_id()
        # now run cosym
        if cosym_params.seed is not None:
            flex.set_random_seed(cosym_params.seed)
            np.random.seed(cosym_params.seed)
            random.seed(cosym_params.seed)
        cosym_instance = cosym(expts, tables, cosym_params)
        register_default_cosym_observers(cosym_instance)
        cosym_instance.run()
        cosym_instance.experiments.as_file(cosym_params.output.experiments)
        joint_refls = flex.reflection_table.concat(cosym_instance.reflections)
        joint_refls.as_file(cosym_params.output.reflections)
        xia2_logger.info(
            f"Consistently indexed {len(cosym_instance.experiments)} crystals in data reduction batch {index+1}"
        )

    return ProgramResult(
        working_directory / cosym_params.output.experiments,
        working_directory / cosym_params.output.reflections,
        working_directory / logfile,
        working_directory / cosym_params.output.html,
        working_directory / cosym_params.output.json,
    )


def scale_reindex_single(
    working_directory: Path,
    batch_for_reindex: ProcessingBatch,
    reduction_params: ReductionParams,
) -> List[ProcessingBatch]:
    assert (
        reduction_params.reference
    )  # this should only be called if we have a reference
    scaleresult = scale_on_batches(
        working_directory,
        [batch_for_reindex],
        reduction_params,
        "batch1",
    )
    logfile = "dials.reindex.log"
    with run_in_directory(working_directory), log_to_file(logfile), record_step(
        "dials.reindex"
    ):
        expts = load.experiment_list(scaleresult.exptfile, check_format=False)
        refls = flex.reflection_table.from_file(scaleresult.reflfile)
        space_group = reduction_params.space_group.group()
        wavelength = np.mean([expt.beam.get_wavelength() for expt in expts])
        from dials.util.reference import intensities_from_reference_file
        from dials.util.reindex import change_of_basis_op_against_reference

        reference_miller_set = intensities_from_reference_file(
            os.fspath(reduction_params.reference), wavelength=wavelength
        )
        change_of_basis_op = change_of_basis_op_against_reference(
            expts, [refls], reference_miller_set
        )
        for expt in expts:
            expt.crystal = expt.crystal.change_basis(change_of_basis_op)
            expt.crystal.set_space_group(space_group)

        exptfileout = "processed_0.expt"
        reflfileout = "processed_0.refl"
        expts.as_file(exptfileout)

        refls["miller_index"] = change_of_basis_op.apply(refls["miller_index"])
        refls.as_file(reflfileout)
    xia2_logger.info("Reindexed against reference file")
    outbatch = ProcessingBatch()
    outbatch.add_filepair(
        FilePair(working_directory / exptfileout, working_directory / reflfileout)
    )
    return [outbatch]


def cosym_reindex(
    working_directory: Path,
    batches_for_reindex: List[ProcessingBatch],
    d_min: float = None,
    max_delta: float = 0.5,
    partiality_threshold: float = 0.2,
    reference=None,
) -> List[ProcessingBatch]:
    from dials.command_line.cosym import phil_scope as cosym_scope

    expts = []
    refls = []
    params = cosym_scope.extract()

    logfile = "dials.cosym_reindex.log"
    for batch in batches_for_reindex:
        for filepair in batch.filepairs:
            expts.append(load.experiment_list(filepair.expt, check_format=False))
            refls.append(flex.reflection_table.from_file(filepair.refl))
    params.space_group = expts[0][0].crystal.get_space_group().info()
    params.lattice_symmetry_max_delta = max_delta
    params.partiality_threshold = partiality_threshold
    params.min_i_mean_over_sigma_mean = 0.5
    params.cc_weights = "sigma"
    params.weights = "standard_error"
    if reference:
        params.reference = os.fspath(reference)
    if d_min:
        params.d_min = d_min

    with open(os.devnull, "w") as devnull, run_in_directory(
        working_directory
    ), log_to_file(logfile), record_step("cosym_reindex"):
        sys.stdout = devnull  # block printing from cosym
        cosym_instance = BatchCosym(expts, refls, params)
        register_default_cosym_observers(cosym_instance)
        cosym_instance.run()
    sys.stdout = sys.__stdout__
    FileHandler.record_log_file(logfile.rstrip(".log"), working_directory / logfile)
    FileHandler.record_html_file("dials.cosym", working_directory / "dials.cosym.html")
    outfiles = []
    for expt, refl in zip(
        cosym_instance._output_expt_files, cosym_instance._output_refl_files
    ):
        outbatch = ProcessingBatch()
        outbatch.add_filepair(
            FilePair(working_directory / expt, working_directory / refl)
        )
        outfiles.append(outbatch)
    return outfiles


def parallel_cosym(
    working_directory: Path,
    data_to_reindex: List[ProcessingBatch],
    reduction_params,
    nproc: int = 1,
) -> List[ProcessingBatch]:
    """Run dials.cosym on each batch to resolve indexing ambiguities."""

    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)

    reindexed_results = [ProcessingBatch() for _ in range(len(data_to_reindex))]

    with open(os.devnull, "w") as devnull:
        sys.stdout = devnull  # block printing from cosym

        with record_step(
            "dials.cosym (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:

            cosym_futures: dict[Any, int] = {
                pool.submit(
                    individual_cosym,
                    working_directory,
                    batch,
                    index,
                    reduction_params,
                ): index
                for index, batch in enumerate(data_to_reindex)
            }
            for future in concurrent.futures.as_completed(cosym_futures):
                idx = cosym_futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    raise ValueError(
                        f"Unsuccessful scaling and symmetry analysis of the new data. Error:\n{e}"
                    )
                else:
                    reindexed_results[idx].add_filepair(
                        FilePair(result.exptfile, result.reflfile)
                    )
                    FileHandler.record_log_file(
                        result.logfile.name.rstrip(".log"), result.logfile
                    )
                    FileHandler.record_html_file(
                        result.htmlfile.name.rstrip(".html"), result.htmlfile
                    )

    sys.stdout = sys.__stdout__  # restore printing
    return reindexed_results


def select_crystals_close_to(
    crystals_dict: CrystalsDict,
    unit_cell: uctbx.unit_cell,
    abs_angle_tol: float,
    abs_length_tol: float,
) -> CrystalsDict:
    good_crystals_data: CrystalsDict = {}
    with record_step("select based on unit cell"):
        n_input = 0
        n_good = 0
        for file_, data in crystals_dict.items():
            identifiers = data.identifiers
            n = len(identifiers)
            n_input += n
            ids = []
            for i, c in enumerate(data.crystals):
                if c.get_unit_cell().is_similar_to(
                    unit_cell,
                    absolute_angle_tolerance=abs_angle_tol,
                    absolute_length_tolerance=abs_length_tol,
                ):
                    ids.append(i)
            n_this = len(ids)
            if n_this == n:
                good_crystals_data[file_] = CrystalsData(
                    identifiers=identifiers,
                    crystals=data.crystals,
                    keep_all_original=True,
                )
            else:
                good_crystals_data[file_] = CrystalsData(
                    identifiers=[identifiers[i] for i in ids],
                    crystals=[data.crystals[i] for i in ids],
                    keep_all_original=False,
                )
            n_good += n_this
        uc_string = ", ".join(f"{i:.2f}" for i in unit_cell.parameters())
        xia2_logger.info(
            "Unit cell filtering:\n"
            f"  Selected {n_good} crystals consistent with cell parameters\n  {uc_string},\n"
            "  and tolerances of"
            + " \u00b1"
            + f"{abs_length_tol}"
            + "\u212b &"
            + " \u00b1"
            + f"{abs_angle_tol}"
            + "\u00b0"
        )
    return good_crystals_data


class ProcessingBatch(object):
    #  unit of file input for a processing job. Consisting of one or more filepairs,
    # optionally with additional subsets of identifiers for selecting data out
    # of those files.

    def __init__(self):
        self.filepairs = []
        self.filepair_to_good_identifiers = {}

    def add_filepair(self, fp, identifiers=None):
        self.filepairs.append(fp)
        if identifiers:
            assert fp not in self.filepair_to_good_identifiers
            self.filepair_to_good_identifiers[fp] = identifiers


def split_filtered_data(
    new_data: List[FilePair],
    good_crystals_data: CrystalsDict,
    min_batch_size: int,
) -> List[ProcessingBatch]:

    n_cryst = sum(len(v.identifiers) for v in good_crystals_data.values())
    n_batches = max(math.floor(n_cryst / min_batch_size), 1)
    batches = [ProcessingBatch() for _ in range(n_batches)]

    stride = n_cryst / n_batches
    # make sure last batch has at least the batch size
    splits = [int(math.floor(i * stride)) for i in range(n_batches)]
    splits.append(n_cryst)

    n_leftover = 0
    n_batch_output = 0
    n_required = splits[1] - splits[0]
    current_fps = []
    current_identifier_lists = []
    for file_pair in new_data:
        good_crystals_this = good_crystals_data[str(file_pair.expt)]
        if not good_crystals_this.crystals:
            continue
        good_identifiers = good_crystals_this.identifiers
        n_leftover += len(good_identifiers)
        current_fps.append(file_pair)
        current_identifier_lists.append(good_identifiers)

        while n_leftover >= n_required:

            last_fp = current_fps.pop()
            ids = current_identifier_lists.pop()
            if n_required == n_leftover:
                sub_ids_last = ids
                sub_ids_last_leftover = flex.std_string([])
            else:
                sub_ids_last = ids[: (n_required - n_leftover)]
                sub_ids_last_leftover = ids[(n_required - n_leftover) :]

            for fp, ids in zip(current_fps, current_identifier_lists):
                batches[n_batch_output].add_filepair(fp, ids)
            batches[n_batch_output].add_filepair(last_fp, sub_ids_last)
            if len(sub_ids_last_leftover):
                current_fps = [last_fp]
                current_identifier_lists = [sub_ids_last_leftover]
            else:
                current_fps = []
                current_identifier_lists = []
            n_batch_output += 1
            n_leftover -= n_required
            if n_batch_output == len(splits) - 1:
                break
            n_required = splits[n_batch_output + 1] - splits[n_batch_output]
    assert n_batch_output == len(splits) - 1
    assert not n_leftover

    return batches


def prepare_scaled_array(
    filelist: List[FilePair], best_unit_cell: uctbx.unit_cell
) -> Tuple[miller.array, ExperimentList]:
    """
    Loads a list of reflection tables and experiment lists, creates a miller
    array and concatenates into a combined miller array and experiment list.
    """
    scaled_array = None
    joint_expts: ExperimentList = ExperimentList()
    for fp in filelist:
        expts = load.experiment_list(fp.expt, check_format=False)
        table = flex.reflection_table.from_file(fp.refl)
        # now make the miller array
        miller_set = miller.set(
            crystal_symmetry=crystal.symmetry(
                unit_cell=best_unit_cell,
                space_group=expts[0].crystal.get_space_group(),
                assert_is_compatible_unit_cell=False,
            ),
            indices=table["miller_index"],
            anomalous_flag=False,
        )
        i_obs: miller.array = miller.array(
            miller_set,
            data=table["intensity"],
        )
        i_obs.set_observation_type_xray_intensity()
        i_obs.set_sigmas(table["sigma"])
        if scaled_array is None:
            scaled_array = i_obs
            joint_expts = expts
        else:
            scaled_array = scaled_array.concatenate(i_obs)
            joint_expts.extend(expts)
    if not scaled_array:
        raise RuntimeError("No file list given to prepare_scaled_array")
    scaled_array.set_observation_type_xray_intensity()

    return scaled_array, joint_expts
