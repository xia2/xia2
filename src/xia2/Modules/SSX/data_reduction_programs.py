from __future__ import annotations

import functools
import logging
import math
from io import StringIO
from pathlib import Path
from typing import Dict, List, Tuple

import procrunner

from cctbx import sgtbx, uctbx
from dials.algorithms.scaling.algorithm import ScalingAlgorithm
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dials.command_line.cosym import cosym
from dials.command_line.cosym import phil_scope as cosym_phil_scope
from dials.command_line.cosym import register_default_cosym_observers
from dials.command_line.merge import generate_html_report as merge_html_report
from dials.command_line.merge import merge_data_to_mtz
from dials.command_line.merge import phil_scope as merge_phil_scope
from dials.command_line.scale import _export_unmerged_mtz
from dials.command_line.scale import phil_scope as scaling_phil_scope
from dials.command_line.scale import run_scaling
from dxtbx.model import ExperimentList
from dxtbx.serialize import load
from iotbx import phil

from xia2.Modules.SSX.reporting import statistics_output_from_scaler
from xia2.Modules.SSX.util import log_to_file, run_in_directory

xia2_logger = logging.getLogger(__name__)

FilePairDict = Dict[str, Path]  # A Dict of {"expt" : exptpath, "refl" : reflpath}
FilesDict = Dict[
    int, FilePairDict
]  # A Dict where the keys are an index, corresponding to a filepair


def cluster_all_unit_cells(
    working_directory: Path, new_data: Dict[str, List[Path]], threshold: float = 1000
) -> FilePairDict:
    """Run dials.cluster_unit_cell on all files in new_data"""
    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)

    xia2_logger.info(f"Performing unit cell clustering in {working_directory}")
    cmd = ["dials.cluster_unit_cell", "output.clusters=True", f"threshold={threshold}"]

    cmd.extend([str(i) for i in new_data["expt"]])
    cmd.extend([str(i) for i in new_data["refl"]])

    result = procrunner.run(cmd, working_directory=working_directory)
    if result.returncode or result.stderr:
        raise ValueError(
            "Unit cell clustering returned error status:\n" + str(result.stderr)
        )
    # handle fact that could be cluster_0.expt or cluster_00.expt etc
    clusters = list(working_directory.glob("cluster_*.expt"))
    str_numbers = [str(c).split("cluster_")[-1].rstrip(".expt") for c in clusters]
    str_numbers.sort(key=int)
    cluster_expt = working_directory / ("cluster_" + str_numbers[0] + ".expt")
    cluster_refl = working_directory / ("cluster_" + str_numbers[0] + ".refl")
    return {"expt": cluster_expt, "refl": cluster_refl}


def run_cosym(
    params: phil.scope_extract,
    expts: ExperimentList,
    tables: List[flex.reflection_table],
) -> Tuple[ExperimentList, List[flex.reflection_table]]:
    """Small wrapper to hide cosym run implementation."""
    cosym_instance = cosym(expts, tables, params)
    register_default_cosym_observers(cosym_instance)
    cosym_instance.run()
    return cosym_instance.experiments, cosym_instance.reflections


def merge(
    working_directory: Path,
    experiments: ExperimentList,
    reflection_table: flex.reflection_table,
    d_min: float = None,
) -> None:

    with run_in_directory(working_directory):
        logfile = "dials.merge.log"
        with log_to_file(logfile) as dials_logger:
            params = merge_phil_scope.extract()
            input_ = (
                "Input parameters:\n  reflections = scaled.refl\n"
                + "  experiments = scaled.expt\n"
            )
            if d_min:
                params.d_min = d_min
                input_ += f"  d_min = {d_min}\n"
            dials_logger.info(input_)
            mtz_file = merge_data_to_mtz(params, experiments, [reflection_table])
            dials_logger.info("\nWriting reflections to merged.mtz")
            out = StringIO()
            mtz_file.show_summary(out=out)
            dials_logger.info(out.getvalue())
            mtz_file.write("merged.mtz")
            merge_html_report(mtz_file, "dials.merge.html")


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
        + "  scaling_options.outlier_rejection = simple"
        + "  reflection_selection.intensity_choice = sum"
        + "  reflection_selection.method = intensity_ranges"
        + "  reflection_selection.Isigma_range = 2.0,0.0"
        + "  reflection_selection.min_partiality = 0.4"
    )
    return scaling_params, input_


def scale(
    working_directory: Path,
    files_to_scale: FilesDict,
    anomalous: bool = True,
    d_min: float = None,
) -> Tuple[ExperimentList, flex.reflection_table]:
    with run_in_directory(working_directory):
        logfile = "dials.scale.log"
        with log_to_file(logfile) as dials_logger:
            # Setup scaling
            input_ = "Input parameters:\n"
            experiments = ExperimentList()
            reflection_tables = []
            for file_pair in files_to_scale.values():
                expt, table = file_pair["expt"], file_pair["refl"]
                experiments.extend(load.experiment_list(expt, check_format=False))
                reflection_tables.append(flex.reflection_table.from_file(table))
                input_ += "\n".join(f"  reflections = {table}")
                input_ += "\n".join(f"  experiments = {expt}")

            params = scaling_phil_scope.extract()
            params, input_opts = _set_scaling_options_for_ssx(params)
            input_ += input_opts
            params.scaling_options.nproc = 8
            params.anomalous = anomalous
            params.output.unmerged_mtz = "scaled.mtz"
            input_ += f"  scaling_options.nproc = 8\n  anomalous = {anomalous}\n"
            input_ += "  output.unmerged_mtz = scaled.mtz\n"
            if d_min:
                params.cut_data.d_min = d_min
                input_ += f"  cut_data.d_min={d_min}\n"
            dials_logger.info(input_)
            # Run the scaling using the algorithm class to give access to scaler
            scaler = ScalingAlgorithm(params, experiments, reflection_tables)
            scaler.run()
            scaled_expts, scaled_table = scaler.finish()

            dials_logger.info("Saving scaled experiments to scaled.expt")
            scaled_expts.as_file("scaled.expt")
            dials_logger.info("Saving scaled reflections to scaled.expt")
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


def scale_cosym(
    working_directory: Path,
    files: FilePairDict,
    index: int,
    space_group: sgtbx.space_group,
    d_min: float = None,
) -> FilesDict:
    """Run prescaling followed by cosym an the expt and refl file."""
    with run_in_directory(working_directory):

        params = scaling_phil_scope.extract()
        refls = [flex.reflection_table.from_file(files["refl"])]
        expts = load.experiment_list(files["expt"], check_format=False)
        params, _ = _set_scaling_options_for_ssx(params)
        params.output.html = None
        if d_min:
            params.cut_data.d_min = d_min

        scaled_expts, table = run_scaling(params, expts, refls)

        cosym_params = cosym_phil_scope.extract()
        cosym_params.space_group = space_group
        cosym_params.output.html = f"dials.cosym.{index}.html"
        cosym_params.output.json = f"dials.cosym.{index}.json"
        if d_min:
            cosym_params.d_min = d_min
        tables = table.split_by_experiment_id()
        # now run cosym
        cosym_expts, cosym_tables = run_cosym(cosym_params, scaled_expts, tables)
        out_refl = f"processed_{index}.refl"
        out_expt = f"processed_{index}.expt"
        cosym_expts.as_file(out_expt)
        joint_refls = flex.reflection_table.concat(cosym_tables)
        joint_refls.as_file(out_refl)
        xia2_logger.info(
            f"Consistently indexed {len(cosym_expts)} crystals in data reduction batch {index+1}"
        )

    return {
        index: {
            "expt": working_directory / out_expt,
            "refl": working_directory / out_refl,
        }
    }


def reference_reindex(
    working_directory: Path,
    reference_files: FilePairDict,
    files_for_reindex: FilePairDict,
) -> FilePairDict:
    cmd = [
        "dials.reindex",
        str(files_for_reindex["expt"]),
        str(files_for_reindex["refl"]),
        f"reference.reflections={str(reference_files['refl'])}",
        f"reference.experiments={str(reference_files['expt'])}",
        f"output.reflections={str(files_for_reindex['refl'])}",
        f"output.experiments={str(files_for_reindex['expt'])}",
    ]
    result = procrunner.run(cmd, working_directory=working_directory)
    if result.returncode or result.stderr:
        raise ValueError("dials.reindex returned error status:\n" + str(result.stderr))
    return {
        "expt": files_for_reindex["expt"],
        "refl": files_for_reindex["refl"],
    }


def select_crystals_close_to(
    new_data: Dict[str, List[Path]],
    unit_cell: uctbx.unit_cell,
    abs_angle_tol: float,
    abs_length_tol: float,
) -> Tuple[List[flex.reflection_table], ExperimentList]:
    good_refls, good_expts = ([], ExperimentList([]))
    for expt, refl in zip(new_data["expt"], new_data["refl"]):
        experiments = load.experiment_list(expt, check_format=False)
        refls = flex.reflection_table.from_file(refl)
        identifiers = []
        expt_indices = []
        for i, c in enumerate(experiments.crystals()):
            if c.get_unit_cell().is_similar_to(
                unit_cell,
                absolute_angle_tolerance=abs_angle_tol,
                absolute_length_tolerance=abs_length_tol,
            ):
                identifiers.append(experiments[i].identifier)
                expt_indices.append(i)
        if len(expt_indices) == len(experiments):
            # all good
            good_refls.append(refls)
            good_expts.extend(experiments)
        else:
            sub_refls = refls.select_on_experiment_identifiers(identifiers)
            sub_refls.reset_ids()
            good_refls.append(sub_refls)
            good_expts.extend(ExperimentList([experiments[i] for i in expt_indices]))
    return good_refls, good_expts


def inspect_directories(
    new_directories_to_process: List[Path],
) -> Dict[str, List[Path]]:
    new_data: Dict[str, List[Path]] = {"expt": [], "refl": []}
    for d in new_directories_to_process:
        for file_ in list(d.glob("integrated*.expt")):
            new_data["expt"].append(file_)
        for file_ in list(d.glob("integrated*.refl")):
            new_data["refl"].append(file_)
    return new_data


def split(
    working_directory: Path,
    experiments: ExperimentList,
    reflection_table: flex.reflection_table,
    min_batch_size,
) -> FilesDict:

    data_to_reindex: FilesDict = {}
    n_batches = max(math.floor(len(experiments) / min_batch_size), 1)
    stride = len(experiments) / n_batches
    # make sure last batch has at least the batch size
    splits = [int(math.floor(i * stride)) for i in range(n_batches)]
    splits.append(len(experiments))

    template = functools.partial(
        "split_{index:0{fmt:d}d}".format, fmt=len(str(n_batches))
    )
    for i in range(len(splits) - 1):
        out_expt = working_directory / (template(index=i) + ".expt")
        out_refl = working_directory / (template(index=i) + ".refl")
        sub_expt = experiments[splits[i] : splits[i + 1]]
        sub_expt.as_file(out_expt)
        sel = reflection_table["id"] >= splits[i]
        sel &= reflection_table["id"] < splits[i + 1]
        sub_refl = reflection_table.select(sel)
        sub_refl.reset_ids()
        sub_refl.as_file(out_refl)
        data_to_reindex[i] = {"expt": out_expt, "refl": out_refl}
    return data_to_reindex
