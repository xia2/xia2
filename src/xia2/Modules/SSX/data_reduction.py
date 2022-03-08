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
from typing import Dict

import procrunner

from cctbx import uctbx
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
from dxtbx.model.experiment_list import ExperimentList
from dxtbx.serialize import load

from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration import log_to_file, run_in_directory

logger = logging.getLogger(__name__)

# data reduction works on a list of directories - searches for integrated files and a "batch.json" configuration file

# also inspects the current data reduction directories to see what has been done before.


class BaseDataReduction(object):
    def __init__(self, main_directory, batch_directories, params):
        # General setup, finding which of the batch directories have already
        # been processed. Then it's up to the specific data reduction algorithms
        # as to how that information should be used.
        self._main_directory = main_directory
        self._batch_directories = batch_directories
        self._params = params

        data_reduction_dir = self._main_directory / "data_reduction"
        directories_already_processed = []
        new_to_process = []

        logger.notice(banner("Data reduction"))

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
        # if not len(new_to_process):
        #    raise ValueError("No new data found, all directories already processed")

        self._new_directories_to_process = new_to_process
        self._directories_previously_processed = directories_already_processed
        if self._directories_previously_processed:
            dirs = "\n".join(str(i) for i in self._directories_previously_processed)
            logger.info(f"Directories previously processed: {dirs}")
        dirs = "\n".join(str(i) for i in self._new_directories_to_process)
        logger.info(f"New directories to process: {dirs}")

    def run(self):
        pass


def cluster_all_unit_cells(working_directory, batch_directories, threshold=1000):

    if not Path.is_dir(working_directory):
        Path.mkdir(working_directory)

    logger.info(f"Performing unit cell clustering in {working_directory}")
    cmd = ["dials.cluster_unit_cell", "output.clusters=True", f"threshold={threshold}"]

    for d in batch_directories:
        for ext_ in (".refl", ".expt"):
            for file_ in list(d.glob("integrated_*" + ext_)):
                cmd.extend([file_])

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


def scale_cosym(
    working_directory, expt_file, refl_file, index, space_group, d_min=None
):

    with run_in_directory(working_directory):

        params = scaling_phil_scope.extract()
        refls = [flex.reflection_table.from_file(refl_file)]
        expts = load.experiment_list(expt_file, check_format=False)
        params.model = "KB"
        params.exclude_images = ""  # Bug in extract for strings
        params.output.html = None
        params.scaling_options.full_matrix = False
        params.weighting.error_model.error_model = None
        params.scaling_options.outlier_rejection = "simple"
        params.reflection_selection.intensity_choice = "sum"
        params.reflection_selection.method = "intensity_ranges"
        params.reflection_selection.Isigma_range = (2.0, 0.0)
        params.reflection_selection.min_partiality = 0.4
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
        cosym_instance = cosym(scaled_expts, tables, cosym_params)
        register_default_cosym_observers(cosym_instance)
        cosym_instance.run()
        cosym_instance.experiments.as_file(f"processed_{index}.expt")
        joint_refls = flex.reflection_table.concat(cosym_instance.reflections)
        joint_refls.as_file(f"processed_{index}.refl")
        logger.info(
            f"Consistently indexed {len(cosym_instance.experiments)} crystals in data reduction batch {index+1}"
        )

    return {
        index: {
            "expt": working_directory / f"processed_{index}.expt",
            "refl": working_directory / f"processed_{index}.refl",
        }
    }


def reference_reindex(working_directory, reference_files, files_for_reindex):
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


def select_crystals_close_to(new_directories, unit_cell, abs_angle_tol, abs_length_tol):
    good_refls = []
    good_expts = ExperimentList([])
    refl_files_ = []
    expt_files_ = []
    for d in new_directories:
        for file_ in list(d.glob("integrated_*.expt")):
            expt_files_.append(file_)
        for file_ in list(d.glob("integrated_*.refl")):
            refl_files_.append(file_)
    for expt, refl in zip(expt_files_, refl_files_):
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
    # ok so have a list of reflection tables and an ExperimentList.
    # first join all the tables together
    return good_refls, good_expts


class SimpleDataReduction(BaseDataReduction):
    def run(
        self,
        batch_size=1000,
        space_group=None,
        nproc=1,
        anomalous=True,
        cluster_threshold=1000,
        d_min=None,
    ):

        # just some test options for now
        filter_params = {
            "absolute_angle_tolerance": 0.5,
            "absolute_length_tolerance": 0.2,
            "threshold": cluster_threshold,
        }

        data_already_reindexed = {}  # a dict of expt-refl pairs
        data_to_reindex = {}
        reidx_results = (
            self._main_directory
            / "data_reduction"
            / "reindex"
            / "reindexing_results.json"
        )
        if reidx_results.is_file():
            previous = json.load(reidx_results.open())
            data_already_reindexed = {
                int(i): v for i, v in previous["reindexed_files"].items()
            }
            for file_pair in data_already_reindexed.values():
                assert Path(file_pair["expt"]).is_file()
                assert Path(file_pair["refl"]).is_file()

        if self._new_directories_to_process:
            data_already_reindexed, data_to_reindex = self.filter(
                self._main_directory,
                self._new_directories_to_process,
                data_already_reindexed,
                batch_size,
                filter_params,
            )

        files_to_scale = self.reindex(
            self._main_directory,
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
                str(i) for i in self._directories_previously_processed
            ]
            + [str(i) for i in self._new_directories_to_process]
        }
        with open(
            self._main_directory / "data_reduction" / "data_reduction.json", "w"
        ) as fp:
            json.dump(data_reduction_progress, fp)

        self.scale_and_merge(
            self._main_directory, files_to_scale, anomalous=anomalous, d_min=d_min
        )

    def filter(
        self,
        main_directory,
        new_directories_to_process,
        data_already_reindexed: Dict,
        batch_size,
        filter_params,
    ):

        data_to_reindex = {}
        current_unit_cell = 0
        if data_already_reindexed:
            cluster_results = (
                main_directory / "data_reduction" / "prefilter" / "cluster_results.json"
            )
            if cluster_results.is_file():
                result = json.load(cluster_results.open())
                current_unit_cell = uctbx.unit_cell(result["unit_cell"])
                logger.info(
                    f"Using unit cell {result['unit_cell']} from previous clustering analysis"
                )

        working_directory = main_directory / "data_reduction" / "prefilter"

        if not current_unit_cell:
            # none previously processed (or processing failed for some reason)
            # so do clustering on all data, using a threshold.
            logger.notice(banner("Clustering"))
            main_cluster_files = cluster_all_unit_cells(
                working_directory,
                new_directories_to_process,
                filter_params["threshold"],
            )
            cluster_expt = str(main_cluster_files["expt"])
            cluster_refl = str(main_cluster_files["refl"])

            # save the results to a json
            cluster_expts = load.experiment_list(cluster_expt, check_format=False)
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
            n_split_files = math.ceil(n_in_cluster / batch_size)
            maxindexlength = len(str(n_in_cluster - 1))

            def template(prefix, maxindexlength, extension, index):
                return f"{prefix}_{index:0{maxindexlength:d}d}.{extension}"

            # then split into chunks
            cmd = [
                "dials.split_experiments",
                cluster_refl,
                cluster_expt,
                f"chunk_size={batch_size}",
            ]
            result = procrunner.run(cmd, working_directory=working_directory)
            if result.returncode or result.stderr:
                raise ValueError(
                    "dials.split_experiments returned error status:\n"
                    + str(result.stderr)
                )
            # now get the files

            for i in range(n_split_files):
                data_to_reindex[i] = {"refl": None, "expt": None}
                for ext_ in ("refl", "expt"):
                    data_to_reindex[i][ext_] = working_directory / str(
                        template(
                            index=i,
                            prefix="split",
                            maxindexlength=maxindexlength,
                            extension=ext_,
                        )
                    )

            # FIXME need to join the last two so that above the min threshold.

            return data_already_reindexed, data_to_reindex  # list of files

        # else going to filter some and prepare for reindexing, and note which is already reindexed.

        logger.notice(banner("Filtering"))
        good_refls, good_expts = select_crystals_close_to(
            new_directories_to_process,
            current_unit_cell,
            filter_params["absolute_angle_tolerance"],
            filter_params["absolute_length_tolerance"],
        )

        from dials.util.multi_dataset_handling import renumber_table_id_columns

        if len(good_expts) < batch_size:
            # we want all jobs to use at least batch_size crystals, so join on
            # to last reindexed batch
            last_batch = data_already_reindexed.pop(
                list(data_already_reindexed.keys())[-1]
            )
            last_expts = load.experiment_list(last_batch["expt"])
            last_refls = flex.reflection_table.from_file(last_batch["refl"])
            good_refls.append(last_refls)
            good_expts.extend(last_expts)

        good_refls = renumber_table_id_columns(good_refls)
        overall_refls = flex.reflection_table()
        for table in good_refls:
            overall_refls.extend(table)
        good_refls = overall_refls

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
            sel = good_refls["id"] >= splits[i]
            sel &= good_refls["id"] < splits[i + 1]
            sub_refl = good_refls.select(sel)
            sub_refl.reset_ids()
            sub_refl.as_file(out_refl)
            data_to_reindex[i + n_already_reindexed_files] = {
                "expt": out_expt,
                "refl": out_refl,
            }

        return data_already_reindexed, data_to_reindex

    @staticmethod
    def reindex(
        main_directory,
        data_to_reindex,
        data_already_reindexed,
        space_group=None,
        nproc=1,
        d_min=None,
    ):
        sys.stdout = open(os.devnull, "w")  # block printing from cosym
        working_directory = main_directory / "data_reduction" / "reindex"
        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)

        if 0 in data_already_reindexed:
            reference_files = data_already_reindexed[0]
        else:
            reference_files = {"expt": None, "refl": None}
        files_for_reference_reindex = {}
        reindexed_results = {}
        logger.notice(banner("Reindexing"))
        with concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:
            futures = {
                pool.submit(
                    scale_cosym,
                    working_directory,
                    files["expt"],
                    files["refl"],
                    index,
                    space_group,
                    d_min,
                ): index
                for index, files in data_to_reindex.items()
            }
            for future in concurrent.futures.as_completed(futures):
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
                            "expt": str(result[0]["expt"]),
                            "refl": str(result[0]["refl"]),
                        }
                    else:
                        files_for_reference_reindex.update(result)

        # now do reference reindexing

        with concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:
            futures = {
                pool.submit(
                    reference_reindex, working_directory, reference_files, files
                ): index
                for index, files in files_for_reference_reindex.items()
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    i = futures[future]
                except Exception as e:
                    raise ValueError(
                        f"Unsuccessful reindexing of the new data. Error:\n{e}"
                    )
                else:
                    reindexed_results[i] = {
                        "expt": str(result["expt"]),
                        "refl": str(result["refl"]),
                    }
                    logger.info(f"Reindexed batch {i+1} using batch 1 as reference")

        files_to_scale_dict = {**data_already_reindexed, **reindexed_results}
        files_to_scale = {"expts": [], "refls": []}
        for file_pair in files_to_scale_dict.values():
            files_to_scale["expts"].append(file_pair["expt"])
            files_to_scale["refls"].append(file_pair["refl"])

        reidx_results = (
            main_directory / "data_reduction" / "reindex" / "reindexing_results.json"
        )
        with open(reidx_results, "w") as f:
            data = {"reindexed_files": files_to_scale_dict}
            json.dump(data, f)
        sys.stdout = sys.__stdout__  # restore printing
        return files_to_scale

    @staticmethod
    def scale_and_merge(main_directory, files_to_scale, anomalous=True, d_min=None):

        working_directory = main_directory / "data_reduction" / "scale"
        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)
        logger.notice(banner("Scaling & Merging"))

        with run_in_directory(working_directory):
            logfile = "dials.scale.log"
            with log_to_file(logfile) as dials_logger:
                experiments = ExperimentList()
                reflection_tables = []
                for expt in files_to_scale["expts"]:
                    experiments.extend(load.experiment_list(expt, check_format=False))
                for table in files_to_scale["refls"]:
                    reflection_tables.append(flex.reflection_table.from_file(table))

                params = scaling_phil_scope.extract()
                params.model = "KB"
                params.exclude_images = ""  # Bug in extract for strings
                params.weighting.error_model.error_model = None
                params.scaling_options.full_matrix = False
                params.scaling_options.outlier_rejection = "simple"
                params.reflection_selection.min_partiality = 0.4
                params.reflection_selection.intensity_choice = "sum"
                params.scaling_options.nproc = 8
                params.anomalous = anomalous
                params.reflection_selection.method = "intensity_ranges"
                params.reflection_selection.Isigma_range = (2.0, 0.0)
                params.output.unmerged_mtz = "scaled.mtz"
                if d_min:
                    params.cut_data.d_min = d_min

                scaler = ScalingAlgorithm(params, experiments, reflection_tables)
                scaler.run()
                scaled_expts, table = scaler.finish()

                dials_logger.info("Saving scaled experiments to scaled.expt")
                scaled_expts.as_file("scaled.expt")
                dials_logger.info("Saving scaled reflections to scaled.expt")
                table.as_file("scaled.refl")

                _export_unmerged_mtz(params, scaled_expts, table)

                n_final = len(scaled_expts)
                uc = determine_best_unit_cell(scaled_expts)
                uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
                logger.info(
                    f"{n_final} crystals scaled in space group {scaled_expts[0].crystal.get_space_group().info()}\nMedian cell: {uc_str}"
                )

                stats = format_statistics(
                    table_1_stats(
                        scaler.merging_statistics_result,
                        scaler.anom_merging_statistics_result,
                    )
                )
                logger.info(stats)

            logfile = "dials.merge.log"
            with log_to_file(logfile) as dials_logger:
                params = merge_phil_scope.extract()
                if d_min:
                    params.d_min = d_min
                mtz_file = merge_data_to_mtz(params, scaled_expts, [table])
                dials_logger.info("\nWriting reflections to merged.mtz")
                out = StringIO()
                mtz_file.show_summary(out=out)
                dials_logger.info(out.getvalue())
                mtz_file.write("merged.mtz")
                merge_html_report(mtz_file, "dials.merge.html")
