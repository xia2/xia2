from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import iotbx.phil
from cctbx import sgtbx, uctbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    FilePair,
    cluster_all_unit_cells,
    inspect_directories,
    merge,
    reference_reindex,
    scale,
    scale_against_model,
    scale_cosym,
    select_crystals_close_to,
    split,
)
from xia2.Modules.SSX.reporting import statistics_output_from_scaled_files

xia2_logger = logging.getLogger(__name__)

FilesDict = Dict[
    int, FilePair
]  # A Dict where the keys are an index, corresponding to a filepair


@dataclass
class SimpleReductionParams:
    space_group: sgtbx.space_group
    batch_size: int = 1000
    nproc: int = 1
    d_min: Optional[float] = None
    anomalous: bool = False
    cluster_threshold: float = 1000.0
    absolute_angle_tolerance: float = 0.5
    absolute_length_tolerance: float = 0.2
    model: Optional[Path] = None

    @classmethod
    def from_phil(cls, params: iotbx.phil.scope_extract):
        """Construct from xia2.cli.ssx phil_scope."""
        model = None
        if params.scaling.model:
            model = Path(params.scaling.model).resolve()
        return cls(
            params.space_group,
            params.batch_size,
            params.nproc,
            params.d_min,
            params.scaling.anomalous,
            params.clustering.threshold,
            model=model,
        )


class SimpleDataReduction(BaseDataReduction):
    def run(self, reduction_params: SimpleReductionParams) -> None:
        """
        A simple workflow for data reduction. First filter the input data, either
        by clustering on unit cells, or comparing against a previous cell. Then
        reindex data in batches, using cosym, followed by scaling and merging.
        """

        data_already_reindexed: FilesDict = {}
        data_to_reindex: FilesDict = {}

        data_reduction_wd = self._main_directory / "data_reduction"
        filter_wd = data_reduction_wd / "prefilter"
        reindex_wd = data_reduction_wd / "reindex"
        scale_wd = data_reduction_wd / "scale"

        reidx_results = reindex_wd / "reindexing_results.json"
        if reidx_results.is_file():
            previous = json.load(reidx_results.open())
            data_already_reindexed = {
                int(i): FilePair(Path(v["expt"]), Path(v["refl"]))
                for i, v in previous["reindexed_files"].items()
            }
            for file_pair in data_already_reindexed.values():
                assert file_pair.check()

        if self._new_directories_to_process:
            new_data = inspect_directories(self._new_directories_to_process)
            current_unit_cell = None
            if data_already_reindexed:
                cluster_results = filter_wd / "cluster_results.json"
                if cluster_results.is_file():
                    result = json.load(cluster_results.open())
                    current_unit_cell = uctbx.unit_cell(result["unit_cell"])
                    xia2_logger.info(
                        f"Using unit cell {result['unit_cell']} from previous clustering analysis"
                    )

            if not current_unit_cell:
                if reduction_params.cluster_threshold:
                    data_to_reindex = self.filter_on_unit_cell_clustering(
                        filter_wd,
                        new_data,
                        reduction_params.batch_size,
                        reduction_params.cluster_threshold,
                    )
                else:
                    # handle splitting into directories
                    tables = []
                    experiments = ExperimentList([])
                    for file_pair in new_data.values():
                        tables.append(flex.reflection_table.from_file(file_pair.refl))
                        experiments.extend(
                            load.experiment_list(file_pair.expt, check_format=False)
                        )
                    table = flex.reflection_table.concat(tables)

                    data_to_reindex = split(
                        filter_wd, experiments, table, reduction_params.batch_size
                    )
            else:
                data_already_reindexed, data_to_reindex = self.filter_on_previous_cell(
                    filter_wd,
                    new_data,
                    data_already_reindexed,
                    reduction_params.batch_size,
                    reduction_params.absolute_angle_tolerance,
                    reduction_params.absolute_length_tolerance,
                    current_unit_cell,
                )
        point_group = reduction_params.space_group.group().point_group_type()
        if point_group in ["1", "2", "m", "mm2", "3", "3m", "4", "4mm", "6", "6mm"]:
            files_to_scale = self.reindex(
                reindex_wd,
                data_to_reindex,
                data_already_reindexed,
                space_group=reduction_params.space_group,
                nproc=reduction_params.nproc,
                d_min=reduction_params.d_min,
            )
        else:
            files_to_scale = {**data_already_reindexed, **data_to_reindex}

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
        with open(data_reduction_wd / "data_reduction.json", "w") as fp:
            json.dump(data_reduction_progress, fp)

        if reduction_params.model:
            self.scale_and_merge_using_model(
                scale_wd,
                files_to_scale,
                anomalous=reduction_params.anomalous,
                d_min=reduction_params.d_min,
                model=reduction_params.model,
                nproc=reduction_params.nproc,
            )
        else:
            self.scale_and_merge(
                scale_wd,
                files_to_scale,
                anomalous=reduction_params.anomalous,
                d_min=reduction_params.d_min,
            )

    @staticmethod
    def filter_on_unit_cell_clustering(
        working_directory: Path,
        new_data: FilesDict,
        batch_size: int,
        threshold: float,
    ) -> FilesDict:

        """
        Filter the integrated data using dials.cluster_unit_cell. Takes the
        largest cluster found and splits it into batches for reindexing.
        """
        xia2_logger.notice(banner("Clustering"))  # type: ignore
        main_cluster_files = cluster_all_unit_cells(
            working_directory,
            new_data,
            threshold,
        )

        # save the results to a json
        cluster_expts = load.experiment_list(
            main_cluster_files.expt,
            check_format=False,
        )
        cluster_refls = flex.reflection_table.from_file(main_cluster_files.refl)
        n_in_cluster = len(cluster_expts)
        uc = determine_best_unit_cell(cluster_expts)
        result = {
            "unit_cell": [round(i, 4) for i in uc.parameters()],
            "n_in_cluster": n_in_cluster,
        }
        with open(working_directory / "cluster_results.json", "w") as fp:
            json.dump(result, fp)

        data_to_reindex = split(
            working_directory, cluster_expts, cluster_refls, batch_size
        )

        return data_to_reindex

    @staticmethod
    def filter_on_previous_cell(
        working_directory: Path,
        new_data: FilesDict,
        data_already_reindexed: FilesDict,
        batch_size: int,
        absolute_angle_tolerance: float,
        absolute_length_tolerance: float,
        previous_unit_cell: uctbx.unit_cell,
    ) -> Tuple[FilesDict, FilesDict]:
        """
        Filter unit cells close to the previous cell. Then split the data
        into batches ready for reindexing.
        """

        # else going to filter some and prepare for reindexing, and note which is already reindexed.
        data_to_reindex: FilesDict = {}
        xia2_logger.notice(banner("Filtering"))  # type: ignore
        good_refls, good_expts = select_crystals_close_to(
            new_data,
            previous_unit_cell,
            absolute_angle_tolerance,
            absolute_length_tolerance,
        )

        if len(good_expts) < batch_size:
            # we want all jobs to use at least batch_size crystals, so join on
            # to last reindexed batch
            last_batch = data_already_reindexed.pop(
                list(data_already_reindexed.keys())[-1]
            )
            good_refls.append(flex.reflection_table.from_file(last_batch.refl))
            good_expts.extend(load.experiment_list(last_batch.expt))

        joint_good_refls = flex.reflection_table.concat(good_refls)

        n_already_reindexed_files = len(list(data_already_reindexed.keys()))

        data_to_reindex = split(
            working_directory, good_expts, joint_good_refls, batch_size
        )
        # offset keys by n_already_reindexed_files
        for k in sorted(data_to_reindex.keys(), reverse=True):
            data_to_reindex[k + n_already_reindexed_files] = data_to_reindex.pop(k)
        return data_already_reindexed, data_to_reindex

    @staticmethod
    def reindex(
        working_directory: Path,
        data_to_reindex: FilesDict,
        data_already_reindexed: FilesDict,
        space_group: sgtbx.space_group,
        nproc: int = 1,
        d_min: float = None,
    ) -> FilesDict:
        """
        Runs dials.scale + dials.cosym on each batch to resolve indexing
        ambiguities. If there is more than one batch, the first batch is used
        as a reference, and dials.reindex is used to reindex the other batches
        against this reference.
        """
        sys.stdout = open(os.devnull, "w")  # block printing from cosym

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)

        if 0 in data_already_reindexed:
            reference_files = data_already_reindexed[0]
        else:
            assert 0 in data_to_reindex  # make sure we have something that will
            # become the reference file.
        files_for_reference_reindex: FilesDict = {}
        reindexed_results: FilesDict = {}
        xia2_logger.notice(banner("Reindexing"))  # type: ignore
        with record_step(
            "dials.scale/dials.cosym (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:
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
                        reindexed_results[0] = result[0]
                    else:
                        files_for_reference_reindex.update(result)

        # now do reference reindexing
        with record_step(
            "dials.reindex (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:
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
                    reindexed_results[i] = result
                    xia2_logger.info(
                        f"Reindexed batch {i+1} using batch 1 as reference"
                    )

        files_to_scale = {**data_already_reindexed, **reindexed_results}
        output_files_to_scale = {
            k: {"expt": str(v.expt), "refl": str(v.refl)}
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
        scaled_expts, scaled_table = scale(
            working_directory, files_to_scale, anomalous, d_min
        )
        merge(working_directory, scaled_expts, scaled_table, d_min)

    @staticmethod
    def scale_and_merge_using_model(
        working_directory: Path,
        files_to_scale: FilesDict,
        anomalous: bool = True,
        d_min: float = None,
        model: Path = None,
        nproc: int = 1,
    ) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)
        xia2_logger.notice(banner("Scaling using model"))  # type: ignore

        scaled_results: FilesDict = {}
        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(max_workers=nproc) as pool:
            scale_futures: Dict[Any, int] = {
                pool.submit(
                    scale_against_model,
                    working_directory,
                    files,
                    index,
                    model,
                    anomalous,
                    d_min,
                ): index
                for index, files in files_to_scale.items()
            }
            for future in concurrent.futures.as_completed(scale_futures):
                try:
                    result = future.result()
                except Exception as e:
                    raise ValueError(f"Unsuccessful scaling of group. Error:\n{e}")
                else:
                    scaled_results.update(result)

        xia2_logger.notice(banner("Merging"))  # type: ignore
        scaled_expts = ExperimentList([])
        scaled_tables = []
        for file_pair in scaled_results.values():
            scaled_expts.extend(
                load.experiment_list(file_pair.expt, check_format=False)
            )
            scaled_tables.append(flex.reflection_table.from_file(file_pair.refl))
        scaled_table = flex.reflection_table.concat(scaled_tables)

        n_final = len(scaled_expts)
        uc = determine_best_unit_cell(scaled_expts)
        uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
        xia2_logger.info(
            f"{n_final} crystals scaled in space group {scaled_expts[0].crystal.get_space_group().info()}\nMedian cell: {uc_str}"
        )
        xia2_logger.info(
            statistics_output_from_scaled_files(scaled_expts, scaled_table, uc)
        )

        merge(working_directory, scaled_expts, scaled_table, d_min)
