# -*- coding: utf-8 -*-
from __future__ import annotations

import concurrent.futures
import copy
import functools
import logging
import math
import os
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import iotbx.phil
from cctbx import crystal, sgtbx, uctbx
from dials.algorithms.scaling.algorithm import ScalingAlgorithm
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dials.command_line.cluster_unit_cell import do_cluster_analysis
from dials.command_line.cluster_unit_cell import phil_scope as cluster_phil_scope
from dials.command_line.cosym import cosym
from dials.command_line.cosym import phil_scope as cosym_phil_scope
from dials.command_line.cosym import register_default_cosym_observers
from dials.command_line.merge import generate_html_report as merge_html_report
from dials.command_line.merge import merge_data_to_mtz
from dials.command_line.merge import phil_scope as merge_phil_scope
from dials.command_line.scale import _export_unmerged_mtz
from dials.command_line.scale import phil_scope as scaling_phil_scope
from dials.command_line.scale import run_scaling
from dxtbx.model import Crystal, ExperimentList
from dxtbx.serialize import load
from iotbx import phil

from xia2.Driver.timing import record_step
from xia2.Modules.SSX.data_reduction_base import FilePair, FilesDict, ReductionParams
from xia2.Modules.SSX.reporting import (
    condensed_unit_cell_info,
    statistics_output_from_scaler,
)
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
    xia2_logger.info(f"Found {n} new integrated crystals")
    return data


def filter_(
    working_directory: Path,
    integrated_data: list[FilePair],
    reduction_params: ReductionParams,
) -> Tuple[FilesDict, uctbx.unit_cell, sgtbx.space_group_info]:

    crystals_data = load_crystal_data_from_new_expts(integrated_data)
    space_group = check_consistent_space_group(crystals_data)
    good_crystals_data = filter_new_data(
        working_directory, crystals_data, reduction_params
    )
    if not any(v.crystals for v in good_crystals_data.values()):
        raise ValueError("No crystals remain after filtering")

    new_files_to_process = split_filtered_data(
        working_directory,
        integrated_data,
        good_crystals_data,
        reduction_params.batch_size,
    )
    best_unit_cell = determine_best_unit_cell_from_crystals(good_crystals_data)
    return new_files_to_process, best_unit_cell, space_group


def assess_for_indexing_ambiguities(
    space_group: sgtbx.space_group_info, unit_cell: uctbx.unit_cell
) -> bool:
    # if lattice symmetry higher than space group symmetry, then need to
    # assess for indexing ambiguity.
    cs = crystal.symmetry(unit_cell=unit_cell, space_group=sgtbx.space_group())
    # Get cell reduction operator
    cb_op_inp_minimum = cs.change_of_basis_op_to_minimum_cell()
    # New symmetry object with changed basis
    minimum_symmetry = cs.change_basis(cb_op_inp_minimum)

    # Get highest symmetry compatible with lattice
    lattice_group = sgtbx.lattice_symmetry_group(
        minimum_symmetry.unit_cell(),
        max_delta=5,
        enforce_max_delta_for_generated_two_folds=True,
    )
    need_to_assess = lattice_group.order_z() > space_group.group().order_z()
    human_readable = {True: "yes", False: "no"}
    xia2_logger.info(
        "Indexing ambiguity assessment:\n"
        f"  Lattice group: {str(lattice_group.info())}, Space group: {str(space_group)}\n"
        f"  Potential indexing ambiguities: {human_readable[need_to_assess]}"
    )
    return need_to_assess


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
    sys.stdout = open(os.devnull, "w")  # block printing from cluster_uc

    with run_in_directory(working_directory):
        with record_step("dials.cluster_unit_cell"), log_to_file(
            "dials.cluster_unit_cell.log"
        ):
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
    experiments: ExperimentList,
    reflection_table: flex.reflection_table,
    d_min: float = None,
    best_unit_cell: Optional[uctbx.unit_cell] = None,
    suffix: Optional[str] = None,
) -> None:
    filename = "merged" + (suffix if suffix else "") + ".mtz"
    logfile = "dials.merge" + (suffix if suffix else "") + ".log"
    html_file = "dials.merge" + (suffix if suffix else "") + ".html"
    with run_in_directory(working_directory):
        with log_to_file(logfile) as dials_logger, record_step("dials.merge"):
            params = merge_phil_scope.extract()
            input_ = (
                "Input parameters:\n  reflections = scaled.refl\n"
                + "  experiments = scaled.expt\n"
            )
            if d_min:
                params.d_min = d_min
                input_ += f"  d_min = {d_min}\n"
            if best_unit_cell:
                params.best_unit_cell = best_unit_cell
                input_ += f"  best_unit_cell = {best_unit_cell.parameters()}"
            dials_logger.info(input_)
            mtz_file = merge_data_to_mtz(params, experiments, [reflection_table])
            dials_logger.info(f"\nWriting reflections to {filename}")
            out = StringIO()
            mtz_file.show_summary(out=out)
            dials_logger.info(out.getvalue())
            mtz_file.write(filename)
            merge_html_report(mtz_file, html_file)
    xia2_logger.info(f"Merged mtz file: {working_directory / filename}")


def _set_scaling_options_for_ssx(
    scaling_params: phil.scope_extract,
) -> Tuple[phil.scope_extract, str]:
    scaling_params.model = "KB"
    scaling_params.exclude_images = ""  # Bug in extract for strings
    scaling_params.scaling_options.full_matrix = False
    scaling_params.weighting.error_model.error_model = None
    scaling_params.scaling_options.outlier_rejection = "simple"
    scaling_params.reflection_selection.intensity_choice = "sum"
    scaling_params.reflection_selection.method = "intensity_ranges"
    scaling_params.reflection_selection.Isigma_range = (2.0, 0.0)
    scaling_params.reflection_selection.min_partiality = 0.4
    input_ = (
        "  model = KB\n  scaling_options.full_matrix = False\n"
        + "  weighting.error_model.error_model = None\n"
        + "  scaling_options.outlier_rejection = simple\n"
        + "  reflection_selection.intensity_choice = sum\n"
        + "  reflection_selection.method = intensity_ranges\n"
        + "  reflection_selection.Isigma_range = 2.0,0.0\n"
        + "  reflection_selection.min_partiality = 0.4\n"
    )
    return scaling_params, input_


def _extract_scaling_params(reduction_params):
    # scaling options for scaling without a model
    xia2_phil = f"""
        model=KB
        scaling_options.full_matrix=False
        weighting.error_model.error_model=None
        scaling_options.outlier_rejection=simple
        reflection_selection.intensity_choice=sum
        reflection_selection.method=intensity_ranges
        reflection_selection.Isigma_range=2.0,0.0
        reflection_selection.min_partiality=0.4
        scaling_options.nproc=8
        anomalous={reduction_params.anomalous}
        output.unmerged_mtz=scaled.mtz
    """
    if reduction_params.d_min:
        xia2_phil += f"\ncut_data.d_min={reduction_params.d_min}"
    if reduction_params.central_unit_cell:
        vals = ",".join(
            str(round(p, 4)) for p in reduction_params.central_unit_cell.parameters()
        )
        xia2_phil += f"\nreflection_selection.best_unit_cell={vals}"
    working_phil = scaling_phil_scope.fetch(sources=[iotbx.phil.parse(xia2_phil)])
    diff_phil = scaling_phil_scope.fetch_diff(source=working_phil)
    params = working_phil.extract()
    return params, diff_phil


def _extract_scaling_params_for_prescale(reduction_params):

    xia2_phil = f"""
        model=KB
        scaling_options.full_matrix=False
        weighting.error_model.error_model=None
        scaling_options.outlier_rejection=simple
        reflection_selection.intensity_choice=sum
        reflection_selection.method=intensity_ranges
        reflection_selection.Isigma_range=2.0,0.0
        reflection_selection.min_partiality=0.4
        anomalous={reduction_params.anomalous}
        output.html=None
    """
    if reduction_params.d_min:
        xia2_phil += f"\ncut_data.d_min={reduction_params.d_min}"
    if reduction_params.central_unit_cell:
        vals = ",".join(
            str(round(p, 4)) for p in reduction_params.central_unit_cell.parameters()
        )
        xia2_phil += f"\nreflection_selection.best_unit_cell={vals}"
    working_phil = scaling_phil_scope.fetch(sources=[iotbx.phil.parse(xia2_phil)])
    diff_phil = scaling_phil_scope.fetch_diff(source=working_phil)
    params = working_phil.extract()
    return params, diff_phil


def _extract_scaling_params_for_scale_against_model(reduction_params, index):
    xia2_phil = f"""
        model=KB
        scaling_options.full_matrix=False
        weighting.error_model.error_model=None
        scaling_options.outlier_rejection=simple
        reflection_selection.intensity_choice=sum
        reflection_selection.method=intensity_ranges
        reflection_selection.Isigma_range=2.0,0.0
        reflection_selection.min_partiality=0.4
        anomalous={reduction_params.anomalous}
        output.experiments=scaled_{index}.expt
        output.reflections=scaled_{index}.refl
        output.html=dials.scale.{index}.html
        scaling_options.target_model={str(reduction_params.model)}
        scaling_options.only_target=True
        cut_data.small_scale_cutoff=1e-9
    """
    if reduction_params.d_min:
        xia2_phil += f"\ncut_data.d_min={reduction_params.d_min}"
    if reduction_params.central_unit_cell:
        vals = ",".join(
            str(round(p, 4)) for p in reduction_params.central_unit_cell.parameters()
        )
        xia2_phil += f"\nreflection_selection.best_unit_cell={vals}"
    working_phil = scaling_phil_scope.fetch(sources=[iotbx.phil.parse(xia2_phil)])
    diff_phil = scaling_phil_scope.fetch_diff(source=working_phil)
    params = working_phil.extract()
    return params, diff_phil


def scale_against_model(
    working_directory: Path,
    files: FilePair,
    index: int,
    reduction_params,
) -> FilesDict:
    with run_in_directory(working_directory), log_to_file(
        f"dials.scale.{index}.log"
    ) as dials_logger:
        # Setup scaling
        expts = load.experiment_list(files.expt, check_format=False)
        table = flex.reflection_table.from_file(files.refl)
        params, diff_phil = _extract_scaling_params_for_scale_against_model(
            reduction_params, index
        )
        dials_logger.info(
            "The following parameters have been modified:\n"
            + f"input.experiments = {files.expt}\n"
            + f"input.reflections = {files.refl}\n"
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

    return {
        index: FilePair(
            working_directory / params.output.experiments,
            working_directory / params.output.reflections,
        )
    }


def scale(
    working_directory: Path,
    files_to_scale: List[FilePair],
    reduction_params: ReductionParams,
) -> Tuple[ExperimentList, flex.reflection_table]:

    with run_in_directory(working_directory), log_to_file(
        "dials.scale.log"
    ) as dials_logger, record_step("dials.scale"):
        # Setup scaling
        input_ = ""
        expts = ExperimentList()
        tables = []
        for fp in files_to_scale:
            expts.extend(load.experiment_list(fp.expt, check_format=False))
            tables.append(flex.reflection_table.from_file(fp.refl))
            input_ += f"reflections = {fp.refl}\nexperiments = {fp.expt}\n"

        params, diff_phil = _extract_scaling_params(reduction_params)
        dials_logger.info(
            "The following parameters have been modified:\n"
            + input_
            + f"{diff_phil.as_str()}"
        )

        # Run the scaling using the algorithm class to give access to scaler
        scaler = ScalingAlgorithm(params, expts, tables)
        scaler.run()
        scaled_expts, scaled_table = scaler.finish()

        dials_logger.info("Saving scaled experiments to scaled.expt")
        scaled_expts.as_file("scaled.expt")
        dials_logger.info("Saving scaled reflections to scaled.refl")
        scaled_table.as_file("scaled.refl")

        _export_unmerged_mtz(params, scaled_expts, scaled_table)

        n_final = len(scaled_expts)
        uc = determine_best_unit_cell(scaled_expts)
        uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
        xia2_logger.info(
            f"{n_final} crystals scaled in space group {scaled_expts[0].crystal.get_space_group().info()}\nMedian cell: {uc_str}"
        )
        xia2_logger.info(statistics_output_from_scaler(scaler))

    return scaled_expts, scaled_table


def _extract_cosym_params(reduction_params, index):
    xia2_phil = f"""
        space_group={reduction_params.space_group}
        output.html=dials.cosym.{index}.html
        output.json=dials.cosym.{index}.json
        output.reflections=processed_{index}.refl
        output.experiments=processed_{index}.expt
    """
    if reduction_params.d_min:
        xia2_phil += f"\nd_min={reduction_params.d_min}"
    extra_defaults = """
        min_i_mean_over_sigma_mean=2
        unit_cell_clustering.threshold=None
        lattice_symmetry_max_delta=1
    """
    if reduction_params.cosym_phil:
        itpr = cosym_phil_scope.command_line_argument_interpreter()
        try:
            user_phil = itpr.process(args=[os.fspath(reduction_params.cosym_phil)])[0]
            working_phil = cosym_phil_scope.fetch(
                sources=[
                    iotbx.phil.parse(extra_defaults),
                    user_phil,
                    iotbx.phil.parse(xia2_phil),
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
                    iotbx.phil.parse(extra_defaults),
                    iotbx.phil.parse(xia2_phil),
                ]
            )
    else:
        working_phil = cosym_phil_scope.fetch(
            sources=[
                iotbx.phil.parse(extra_defaults),
                iotbx.phil.parse(xia2_phil),
            ]
        )
    diff_phil = cosym_phil_scope.fetch_diff(source=working_phil)
    cosym_params = working_phil.extract()
    return cosym_params, diff_phil


def scale_cosym(
    working_directory: Path,
    files: FilePair,
    index: int,
    reduction_params,
) -> FilesDict:
    """Run prescaling followed by cosym an the expt and refl file."""
    with run_in_directory(working_directory):

        logfile = f"dials.scale.{index}.log"
        with record_step("dials.scale"), log_to_file(logfile) as dials_logger:
            refls = [flex.reflection_table.from_file(files.refl)]
            expts = load.experiment_list(files.expt, check_format=False)
            params, diff_phil = _extract_scaling_params_for_prescale(reduction_params)
            dials_logger.info(
                "The following parameters have been modified:\n"
                + f"reflections = {files.refl}\n"
                + f"experiments = {files.expt}\n"
                + f"{diff_phil.as_str()}"
            )
            scaled_expts, table = run_scaling(params, expts, refls)

        logfile = f"dials.cosym.{index}.log"
        with record_step("dials.cosym"), log_to_file(logfile) as dials_logger:
            cosym_params, diff_phil = _extract_cosym_params(reduction_params, index)
            dials_logger.info(
                "The following parameters have been modified:\n"
                + f"{diff_phil.as_str()}"
            )
            # cosym_params.cc_star_threshold = 0.1
            # cosym_params.angular_separation_threshold = 5

            tables = table.split_by_experiment_id()
            # now run cosym
            cosym_instance = cosym(scaled_expts, tables, cosym_params)
            register_default_cosym_observers(cosym_instance)
            cosym_instance.run()
            cosym_instance.experiments.as_file(cosym_params.output.experiments)
            joint_refls = flex.reflection_table.concat(cosym_instance.reflections)
            joint_refls.as_file(cosym_params.output.reflections)
            xia2_logger.info(
                f"Consistently indexed {len(cosym_instance.experiments)} crystals in data reduction batch {index+1}"
            )

    return {
        index: FilePair(
            working_directory / cosym_params.output.experiments,
            working_directory / cosym_params.output.reflections,
        )
    }


def cosym_reindex(
    working_directory: Path,
    files_for_reindex: List[FilePair],
    d_min: float = None,
) -> List[FilePair]:
    from dials.command_line.cosym import phil_scope as cosym_scope

    from xia2.Modules.SSX.batch_cosym import BatchCosym

    expts = []
    refls = []
    params = cosym_scope.extract()

    logfile = "dials.cosym_reindex.log"
    for filepair in files_for_reindex:
        expts.append(load.experiment_list(filepair.expt, check_format=False))
        refls.append(flex.reflection_table.from_file(filepair.refl))
    params.space_group = expts[0][0].crystal.get_space_group().info()
    params.lattice_symmetry_max_delta = 1
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
    outfiles = []
    for expt, refl in zip(
        cosym_instance._output_expt_files, cosym_instance._output_refl_files
    ):
        outfiles.append(FilePair(working_directory / expt, working_directory / refl))
    return outfiles


def parallel_cosym(
    working_directory: Path,
    data_to_reindex: FilesDict,
    reduction_params,
    nproc: int = 1,
) -> FilesDict:
    """
    Runs dials.scale + dials.cosym on each batch to resolve indexing
    ambiguities. If there is more than one batch, the dials.cosym is run
    again to make sure all batches are consistently indexed.
    """

    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)

    with open(os.devnull, "w") as devnull:
        sys.stdout = devnull  # block printing from cosym

        reindexed_results: FilesDict = {}

        with record_step(
            "dials.scale/dials.cosym (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:

            cosym_futures: Dict[Any, int] = {
                pool.submit(
                    scale_cosym,
                    working_directory,
                    files,
                    index,
                    reduction_params,
                ): index
                for index, files in data_to_reindex.items()
            }
            for future in concurrent.futures.as_completed(cosym_futures):
                try:
                    result = future.result()
                except Exception as e:
                    raise ValueError(
                        f"Unsuccessful scaling and symmetry analysis of the new data. Error:\n{e}"
                    )
                else:
                    reindexed_results.update(result)

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


def split_filtered_data(
    working_directory: Path,
    new_data: List[FilePair],
    good_crystals_data: CrystalsDict,
    min_batch_size: int,
    offset: int = 0,
) -> FilesDict:
    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)
    with record_step("splitting"):
        data_to_reindex: FilesDict = {}
        n_cryst = sum(len(v.identifiers) for v in good_crystals_data.values())
        n_batches = max(math.floor(n_cryst / min_batch_size), 1)
        stride = n_cryst / n_batches
        # make sure last batch has at least the batch size
        splits = [int(math.floor(i * stride)) for i in range(n_batches)]
        splits.append(n_cryst)
        template = functools.partial(
            "split_{index:0{fmt:d}d}".format, fmt=len(str(n_batches + offset))
        )
        leftover_expts = ExperimentList([])
        leftover_refls: List[flex.reflection_table] = []
        n_batch_output = 0
        n_required = splits[1] - splits[0]
        for file_pair in new_data:
            expts = load.experiment_list(file_pair.expt, check_format=False)
            refls = flex.reflection_table.from_file(file_pair.refl)
            good_crystals_this = good_crystals_data[str(file_pair.expt)]
            good_identifiers = good_crystals_this.identifiers
            if not good_crystals_this.keep_all_original:
                expts.select_on_experiment_identifiers(good_identifiers)
                refls = refls.select_on_experiment_identifiers(good_identifiers)
            refls.reset_ids()
            leftover_expts.extend(expts)
            leftover_refls.append(refls)
            while len(leftover_expts) >= n_required:
                sub_expt = leftover_expts[0:n_required]
                if len(leftover_refls) > 1:
                    leftover_refls = [flex.reflection_table.concat(leftover_refls)]
                # concat guarantees that ids are ordered 0...n-1
                sub_refl = leftover_refls[0].select(
                    leftover_refls[0]["id"] < n_required
                )
                leftover_refls = [
                    leftover_refls[0].select(leftover_refls[0]["id"] >= n_required)
                ]
                leftover_refls[0].reset_ids()
                sub_refl.reset_ids()  # necessary?
                leftover_expts = leftover_expts[n_required:]
                out_expt = working_directory / (
                    template(index=n_batch_output + offset) + ".expt"
                )
                out_refl = working_directory / (
                    template(index=n_batch_output + offset) + ".refl"
                )
                sub_expt.as_file(out_expt)
                sub_refl.as_file(out_refl)
                data_to_reindex[n_batch_output + offset] = FilePair(out_expt, out_refl)
                n_batch_output += 1
                if n_batch_output == len(splits) - 1:
                    break
                n_required = splits[n_batch_output + 1] - splits[n_batch_output]
        assert n_batch_output == len(splits) - 1
        assert not len(leftover_expts)
        assert len(leftover_refls) == 1
        assert leftover_refls[0].size() == 0
    return data_to_reindex
