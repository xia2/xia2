# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import functools
import logging
import math
import os
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import procrunner

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
from xia2.Modules.SSX.reporting import (
    condensed_unit_cell_info,
    statistics_output_from_scaler,
)
from xia2.Modules.SSX.util import log_to_file, run_in_directory

xia2_logger = logging.getLogger(__name__)


@dataclass(eq=False)
class FilePair:
    expt: Path
    refl: Path

    def check(self):
        if not self.expt.is_file():
            raise FileNotFoundError(f"File {self.expt} does not exist")
        if not self.refl.is_file():
            raise FileNotFoundError(f"File {self.refl} does not exist")

    def validate(self):
        expt = load.experiment_list(self.expt, check_format=False)
        refls = flex.reflection_table.from_file(self.refl)
        refls.assert_experiment_identifiers_are_consistent(expt)

    def __eq__(self, other):
        if self.expt == other.expt and self.refl == other.refl:
            return True
        return False


FilesDict = Dict[int, FilePair]
# FilesDict: A dict where the keys are an index, corresponding to a filepair


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


def determine_best_unit_cell_from_crystals(
    crystals_dicts: List[CrystalsDict],
) -> uctbx.unit_cell:
    """Set the median unit cell as the best cell, for consistent d-values across
    experiments."""
    uc_params = [flex.double() for i in range(6)]
    for crystals_dict in crystals_dicts:
        for v in crystals_dict.values():
            for c in v.crystals:
                unit_cell = c.get_recalculated_unit_cell() or c.get_unit_cell()
                for i, p in enumerate(unit_cell.parameters()):
                    uc_params[i].append(p)
    best_unit_cell = uctbx.unit_cell(parameters=[flex.median(p) for p in uc_params])
    return best_unit_cell


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
    best_unit_cell: Optional[uctbx.unit_cell] = None,
) -> None:

    with run_in_directory(working_directory):
        logfile = "dials.merge.log"
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
            dials_logger.info("\nWriting reflections to merged.mtz")
            out = StringIO()
            mtz_file.show_summary(out=out)
            dials_logger.info(out.getvalue())
            mtz_file.write("merged.mtz")
            merge_html_report(mtz_file, "dials.merge.html")
    xia2_logger.info(f"Merged mtz file: {working_directory / 'merged.mtz'}")


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


def scale_against_model(
    working_directory: Path,
    files: FilePair,
    index: int,
    model: Path,
    anomalous: bool = True,
    d_min: float = None,
    best_unit_cell: Optional[uctbx.unit_cell] = None,
) -> FilesDict:
    with run_in_directory(working_directory):
        logfile = f"dials.scale.{index}.log"
        with log_to_file(logfile) as dials_logger:
            # Setup scaling
            input_ = "Input parameters:\n"
            expts = load.experiment_list(files.expt, check_format=False)
            table = flex.reflection_table.from_file(files.refl)
            input_ += f"  reflections = {files.refl}\n"
            input_ += f"  experiments = {files.expt}\n"
            params = scaling_phil_scope.extract()
            params, input_opts = _set_scaling_options_for_ssx(params)
            input_ += input_opts
            params.anomalous = anomalous
            params.scaling_options.target_model = str(model)
            params.scaling_options.only_target = True
            params.scaling_options.small_scale_cutoff = 1e-9
            input_ += (
                f"  anomalous = {anomalous}\n  scaling_options.target_model = {model}\n"
                + "  small_scale_cutoff=1e-9\n"
            )
            input_ += "  scaling_options.only_target = True\n"
            params.output.html = f"dials.scale.{index}.html"
            input_ += f"  output.html = dials.scale.{index}.html\n"
            if d_min:
                params.cut_data.d_min = d_min
                input_ += f"  cut_data.d_min = {d_min}\n"
            if best_unit_cell:
                params.reflection_selection.best_unit_cell = best_unit_cell
                input_ += f"  reflection_selection.best_unit_cell = {best_unit_cell.parameters()}\n"
            dials_logger.info(input_)
            # Run the scaling using the algorithm class to give access to scaler
            scaler = ScalingAlgorithm(params, expts, [table])
            scaler.run()
            scaled_expts, scaled_table = scaler.finish()
            out_expt = f"scaled_{index}.expt"
            out_refl = f"scaled_{index}.refl"

            dials_logger.info(f"Saving scaled experiments to {out_expt}")
            scaled_expts.as_file(out_expt)
            dials_logger.info(f"Saving scaled reflections to {out_refl}")
            scaled_table.as_file(out_refl)

    return {index: FilePair(working_directory / out_expt, working_directory / out_refl)}


def scale(
    working_directory: Path,
    files_to_scale: FilesDict,
    anomalous: bool = True,
    d_min: float = None,
    best_unit_cell: Optional[uctbx.unit_cell] = None,
) -> Tuple[ExperimentList, flex.reflection_table]:
    with run_in_directory(working_directory):
        logfile = "dials.scale.log"
        with log_to_file(logfile) as dials_logger, record_step("dials.scale"):
            # Setup scaling
            input_ = "Input parameters:\n"
            experiments = ExperimentList()
            reflection_tables = []
            for file_pair in files_to_scale.values():
                experiments.extend(
                    load.experiment_list(file_pair.expt, check_format=False)
                )
                reflection_tables.append(
                    flex.reflection_table.from_file(file_pair.refl)
                )
                input_ += f"  reflections = {file_pair.refl}\n"
                input_ += f"  experiments = {file_pair.expt}\n"

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
            if best_unit_cell:
                params.reflection_selection.best_unit_cell = best_unit_cell
                input_ += f"  reflection_selection.best_unit_cell = {best_unit_cell}"
            dials_logger.info(input_)
            # Run the scaling using the algorithm class to give access to scaler
            scaler = ScalingAlgorithm(params, experiments, reflection_tables)
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


def scale_cosym(
    working_directory: Path,
    files: FilePair,
    index: int,
    space_group: sgtbx.space_group,
    d_min: float = None,
) -> FilesDict:
    """Run prescaling followed by cosym an the expt and refl file."""
    with run_in_directory(working_directory):

        with record_step("dials.scale"):

            params = scaling_phil_scope.extract()
            refls = [flex.reflection_table.from_file(files.refl)]
            expts = load.experiment_list(files.expt, check_format=False)
            params, _ = _set_scaling_options_for_ssx(params)
            params.output.html = None
            if d_min:
                params.cut_data.d_min = d_min

            scaled_expts, table = run_scaling(params, expts, refls)
        logfile = f"dials.cosym.{index}.log"
        with record_step("dials.cosym"), log_to_file(logfile):
            cosym_params = cosym_phil_scope.extract()
            cosym_params.space_group = space_group
            cosym_params.output.html = f"dials.cosym.{index}.html"
            cosym_params.output.json = f"dials.cosym.{index}.json"
            cosym_params.min_i_mean_over_sigma_mean = 2
            cosym_params.unit_cell_clustering.threshold = None
            # cosym_params.cc_star_threshold = 0.1
            # cosym_params.angular_separation_threshold = 5
            cosym_params.lattice_symmetry_max_delta = 1
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

    return {index: FilePair(working_directory / out_expt, working_directory / out_refl)}


def reference_reindex(
    working_directory: Path,
    reference_files: FilePair,
    files_for_reindex: FilePair,
    index: int,
) -> FilePair:
    cmd = [
        "dials.reindex",
        str(files_for_reindex.expt),
        str(files_for_reindex.refl),
        f"reference.reflections={str(reference_files.refl)}",
        f"reference.experiments={str(reference_files.expt)}",
        f"output.reflections={str(files_for_reindex.refl)}",
        f"output.experiments={str(files_for_reindex.expt)}",
    ]
    logfile = f"dials.reindex.{index}.log"
    with log_to_file(logfile), record_step("dials.reindex"):
        result = procrunner.run(cmd, working_directory=working_directory)
        if result.returncode or result.stderr:
            raise ValueError(
                "dials.reindex returned error status:\n" + str(result.stderr)
            )
    return files_for_reindex


def cosym_reindex(
    working_directory: Path,
    files_for_reindex: FilesDict,
    d_min: float = None,
):
    from dials.command_line.cosym import phil_scope as cosym_scope

    from xia2.Modules.SSX.batch_cosym import batch_cosym_analysis

    expts = []
    refls = []
    params = cosym_scope.extract()

    logfile = "dials.cosym_reindex.log"
    for filepair in files_for_reindex.values():
        expts.append(load.experiment_list(filepair.expt, check_format=False))
        refls.append(flex.reflection_table.from_file(filepair.refl))
    params.space_group = expts[0][0].crystal.get_space_group().info()
    params.lattice_symmetry_max_delta = 1
    if d_min:
        params.d_min = d_min
    with run_in_directory(working_directory), log_to_file(logfile), record_step(
        "cosym_reindex"
    ):
        batch_cosym_analysis(expts, refls, params)


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
