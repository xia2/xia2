from __future__ import annotations

import concurrent.futures
import functools
import json
import logging
import math
import os
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
from dials.report.analysis import format_statistics, table_1_stats
from dxtbx.model import ExperimentList
from dxtbx.serialize import load
from iotbx import phil

from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration import log_to_file, run_in_directory

xia2_logger = logging.getLogger(__name__)

# data reduction works on a list of directories - searches for integrated files

# also inspects the current data reduction directories to see what has been done before.

FilePairDict = Dict[str, Path]  # A Dict of {"expt" : exptpath, "refl" : reflpath}
FilesDict = Dict[
    int, FilePairDict
]  # A Dict where the keys are an index, corresponding to a filepair


class BaseDataReduction(object):
    def __init__(
        self,
        main_directory: Path,
        batch_directories: List[Path],
        params: phil.scope_extract,
    ) -> None:
        # General setup, finding which of the batch directories have already
        # been processed. Then it's up to the specific data reduction algorithms
        # as to how that information should be used.
        self._main_directory = main_directory
        self._batch_directories = batch_directories
        self._params = params

        data_reduction_dir = self._main_directory / "data_reduction"
        directories_already_processed = []
        new_to_process = []

        xia2_logger.notice(banner("Data reduction"))  # type: ignore

        if not Path.is_dir(data_reduction_dir):
            Path.mkdir(data_reduction_dir)
            new_to_process = self._batch_directories

        # if has been processed already, need to read something from the
        # data reduction dir that says it has been reindexed in a consistent
        # manner
        elif (data_reduction_dir / "data_reduction.json").is_file():
            previous = json.load((data_reduction_dir / "data_reduction.json").open())
            directories_already_processed = [
                Path(i) for i in previous["directories_processed"]
            ]

            for d in self._batch_directories:
                if d not in directories_already_processed:
                    new_to_process.append(d)
        else:
            # perhaps error in processing such that none were successfully
            # processed previously. In this case all should be reprocessed
            new_to_process = self._batch_directories

        if not (len(new_to_process) + len(directories_already_processed)) == len(
            self._batch_directories
        ):
            raise ValueError(
                f"""Error assessing new and previous directories:
                new = {new_to_process}
                previous = {directories_already_processed}
                input = {self._batch_directories}
                new + previous != input"""
            )

        self._new_directories_to_process = new_to_process
        self._directories_previously_processed = directories_already_processed
        if self._directories_previously_processed:
            dirs = "\n".join(str(i) for i in self._directories_previously_processed)
            xia2_logger.info(f"Directories previously processed: {dirs}")
        dirs = "\n".join(str(i) for i in self._new_directories_to_process)
        xia2_logger.info(f"New directories to process: {dirs}")

    def run(self) -> None:
        pass


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
        for file_ in list(d.glob("integrated_*.expt")):
            new_data["expt"].append(file_)
        for file_ in list(d.glob("integrated_*.refl")):
            new_data["refl"].append(file_)
    return new_data


def split_cluster(
    working_directory: Path,
    cluster_files: FilePairDict,
    n_in_cluster: int,
    batch_size: int,
) -> FilesDict:
    data_to_reindex: FilesDict = {}
    n_split_files = math.ceil(n_in_cluster / batch_size)
    maxindexlength = len(str(n_in_cluster - 1))

    def template(prefix, maxindexlength, extension, index):
        return f"{prefix}_{index:0{maxindexlength:d}d}.{extension}"

    # then split into chunks
    cmd = [
        "dials.split_experiments",
        str(cluster_files["expt"]),
        str(cluster_files["refl"]),
        f"chunk_size={batch_size}",
    ]
    result = procrunner.run(cmd, working_directory=working_directory)
    if result.returncode or result.stderr:
        raise ValueError(
            "dials.split_experiments returned error status:\n" + str(result.stderr)
        )
    # now get the files

    for i in range(n_split_files):
        data_to_reindex[i] = {}
        for ext_ in ("refl", "expt"):
            data_to_reindex[i][ext_] = working_directory / str(
                template(
                    index=i,
                    prefix="split",
                    maxindexlength=maxindexlength,
                    extension=ext_,
                )
            )

    # FIXME need to join the last two so that above the min threshold?
    return data_to_reindex


class SimpleDataReduction(BaseDataReduction):
    def run(
        self,
        batch_size: int = 1000,
        space_group: sgtbx.space_group = None,
        nproc: int = 1,
        anomalous: bool = True,
        cluster_threshold: float = 1000,
        d_min: float = None,
    ) -> None:

        # just some test options for now
        filter_params = {
            "absolute_angle_tolerance": 0.5,
            "absolute_length_tolerance": 0.2,
            "threshold": cluster_threshold,
        }

        data_already_reindexed: FilesDict = {}
        data_to_reindex: FilesDict = {}
        reindex_directory = self._main_directory / "data_reduction" / "reindex"

        reidx_results = reindex_directory / "reindexing_results.json"
        if reidx_results.is_file():
            previous = json.load(reidx_results.open())
            data_already_reindexed = {
                int(i): v for i, v in previous["reindexed_files"].items()
            }
            for file_pair in data_already_reindexed.values():
                assert Path(file_pair["expt"]).is_file()
                assert Path(file_pair["refl"]).is_file()

        if self._new_directories_to_process:
            new_data = inspect_directories(self._new_directories_to_process)
            filter_directory = self._main_directory / "data_reduction" / "prefilter"
            data_already_reindexed, data_to_reindex = self.filter(
                filter_directory,
                new_data,
                data_already_reindexed,
                batch_size,
                filter_params,
            )

        files_to_scale = self.reindex(
            reindex_directory,
            data_to_reindex,
            data_already_reindexed,
            space_group=space_group,
            nproc=nproc,
            d_min=d_min,
        )

        # if we get here, we have successfully prepared the new data for scaling.
        # So save this to allow reloading in future for iterative workflows.
        data_reduction_progress = {
            "directories_processed": [
                str(i)
                for i in (
                    self._directories_previously_processed
                    + self._new_directories_to_process
                )
            ]
        }
        with open(
            self._main_directory / "data_reduction" / "data_reduction.json", "w"
        ) as fp:
            json.dump(data_reduction_progress, fp)

        scale_directory = self._main_directory / "data_reduction" / "scale"
        self.scale_and_merge(
            scale_directory, files_to_scale, anomalous=anomalous, d_min=d_min
        )

    @staticmethod
    def filter(
        working_directory: Path,
        new_data: Dict[str, List[Path]],
        data_already_reindexed: FilesDict,
        batch_size: int,
        filter_params: Dict[str, float],
    ) -> Tuple[FilesDict, FilesDict]:

        data_to_reindex = {}  # a FilesDict
        current_unit_cell = 0

        if data_already_reindexed:
            cluster_results = working_directory / "cluster_results.json"
            if cluster_results.is_file():
                result = json.load(cluster_results.open())
                current_unit_cell = uctbx.unit_cell(result["unit_cell"])
                xia2_logger.info(
                    f"Using unit cell {result['unit_cell']} from previous clustering analysis"
                )

        if not current_unit_cell:
            # none previously processed (or processing failed for some reason)
            # so do clustering on all data, using a threshold.
            xia2_logger.notice(banner("Clustering"))  # type: ignore
            main_cluster_files = cluster_all_unit_cells(
                working_directory,
                new_data,
                filter_params["threshold"],
            )  # FIXME should we also consider data_already_reindexed here if processing
            # previously failed? or assert not any already reindexed?

            # save the results to a json
            cluster_expts = load.experiment_list(
                main_cluster_files["expt"],
                check_format=False,
            )
            n_in_cluster = len(cluster_expts)
            uc = determine_best_unit_cell(cluster_expts)
            result = {
                "unit_cell": [round(i, 4) for i in uc.parameters()],
                "n_in_cluster": n_in_cluster,
            }
            with open(working_directory / "cluster_results.json", "w") as fp:
                json.dump(result, fp)

            # now split into chunks
            #  Work out what the filenames will be from split_experiments
            data_to_reindex = split_cluster(
                working_directory, main_cluster_files, n_in_cluster, batch_size
            )
            return data_already_reindexed, data_to_reindex  # dicts of files

        # else going to filter some and prepare for reindexing, and note which is already reindexed.

        xia2_logger.notice(banner("Filtering"))  # type: ignore
        good_refls, good_expts = select_crystals_close_to(
            new_data,
            current_unit_cell,
            filter_params["absolute_angle_tolerance"],
            filter_params["absolute_length_tolerance"],
        )

        if len(good_expts) < batch_size:
            # we want all jobs to use at least batch_size crystals, so join on
            # to last reindexed batch
            last_batch = data_already_reindexed.pop(
                list(data_already_reindexed.keys())[-1]
            )
            good_refls.append(flex.reflection_table.from_file(last_batch["refl"]))
            good_expts.extend(load.experiment_list(last_batch["expt"]))

        joint_good_refls = flex.reflection_table.concat(good_refls)

        # FIXME write generic splitting function for this and call to dials.split_experiments?
        # now slice into batches and save
        n_batches = math.floor(len(good_expts) / batch_size)
        # make sure last batch has at least the batch size
        splits = [i * batch_size for i in range(max(1, n_batches - 1))] + [
            len(good_expts)
        ]
        n_already_reindexed_files = len(list(data_already_reindexed.keys()))

        # now split here
        template = functools.partial(
            "split_{index:0{fmt:d}d}".format, fmt=len(str(n_batches))
        )
        for i in range(len(splits) - 1):
            out_expt = working_directory / (template(index=i) + ".expt")
            out_refl = working_directory / (template(index=i) + ".refl")
            sub_expt = good_expts[splits[i] : splits[i + 1]]
            sub_expt.as_file(out_expt)
            sel = joint_good_refls["id"] >= splits[i]
            sel &= joint_good_refls["id"] < splits[i + 1]
            sub_refl = joint_good_refls.select(sel)
            sub_refl.reset_ids()
            sub_refl.as_file(out_refl)
            data_to_reindex[i + n_already_reindexed_files] = {
                "expt": out_expt,
                "refl": out_refl,
            }

        return data_already_reindexed, data_to_reindex

    @staticmethod
    def reindex(
        working_directory: Path,
        data_to_reindex: FilesDict,
        data_already_reindexed: FilesDict,
        space_group: sgtbx.space_group = None,
        nproc: int = 1,
        d_min: float = None,
    ) -> FilesDict:
        sys.stdout = open(os.devnull, "w")  # block printing from cosym

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)

        reference_files: FilePairDict = {}
        if 0 in data_already_reindexed:
            reference_files = data_already_reindexed[0]
        files_for_reference_reindex: FilesDict = {}
        reindexed_results: FilesDict = {}
        xia2_logger.notice(banner("Reindexing"))  # type: ignore
        with concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:
            cosym_futures: Dict[Any, int] = {
                pool.submit(
                    scale_cosym,
                    working_directory,
                    files,
                    index,
                    space_group,
                    d_min,
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
                    if list(result.keys()) == [0]:
                        reference_files = result[0]
                        reindexed_results[0] = {
                            "expt": result[0]["expt"],
                            "refl": result[0]["refl"],
                        }
                    else:
                        files_for_reference_reindex.update(result)

        # now do reference reindexing

        with concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:
            reidx_futures: Dict[Any, int] = {
                pool.submit(
                    reference_reindex, working_directory, reference_files, files
                ): index
                for index, files in files_for_reference_reindex.items()
            }
            for future in concurrent.futures.as_completed(reidx_futures):
                try:
                    result = future.result()
                    i = reidx_futures[future]
                except Exception as e:
                    raise ValueError(
                        f"Unsuccessful reindexing of the new data. Error:\n{e}"
                    )
                else:
                    reindexed_results[i] = {
                        "expt": result["expt"],
                        "refl": result["refl"],
                    }
                    xia2_logger.info(
                        f"Reindexed batch {i+1} using batch 1 as reference"
                    )

        files_to_scale = {**data_already_reindexed, **reindexed_results}
        output_files_to_scale = {
            k: {"expt": str(v["expt"]), "refl": str(v["refl"])}
            for k, v in files_to_scale.items()
        }

        reidx_results = working_directory / "reindexing_results.json"
        with open(reidx_results, "w") as f:
            data = {"reindexed_files": output_files_to_scale}
            json.dump(data, f)
        sys.stdout = sys.__stdout__  # restore printing
        return files_to_scale

    @staticmethod
    def scale_and_merge(
        working_directory: Path,
        files_to_scale: FilesDict,
        anomalous: bool = True,
        d_min: float = None,
    ) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)
        xia2_logger.notice(banner("Scaling & Merging"))  # type: ignore

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

                stats = format_statistics(
                    table_1_stats(
                        scaler.merging_statistics_result,
                        scaler.anom_merging_statistics_result,
                    )
                )
                xia2_logger.info(stats)

        merge(working_directory, scaled_expts, scaled_table, d_min)
