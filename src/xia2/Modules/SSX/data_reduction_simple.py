from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from cctbx import sgtbx, uctbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dxtbx.serialize import load

from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction import (
    cluster_all_unit_cells,
    inspect_directories,
    merge,
    reference_reindex,
    scale,
    scale_cosym,
    select_crystals_close_to,
    split,
)
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction

xia2_logger = logging.getLogger(__name__)

FilePairDict = Dict[str, Path]  # A Dict of {"expt" : exptpath, "refl" : reflpath}
FilesDict = Dict[
    int, FilePairDict
]  # A Dict where the keys are an index, corresponding to a filepair


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
        """
        A simple workflow for data reduction. First filter the input data, either
        by clustering on unit cells, or comparing against a previous cell. Then
        reindex data in batches, using cosym, followed by scaling and merging.
        """

        # just some test options for now
        filter_params = {
            "absolute_angle_tolerance": 0.5,
            "absolute_length_tolerance": 0.2,
            "threshold": cluster_threshold,
        }

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
                int(i): {
                    "expt": Path(v["expt"]),
                    "refl": Path(v["refl"]),
                }
                for i, v in previous["reindexed_files"].items()
            }
            for file_pair in data_already_reindexed.values():
                assert all(v.is_file() for v in file_pair.values())

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
                data_to_reindex = self.filter_on_unit_cell_clustering(
                    filter_wd,
                    new_data,
                    batch_size,
                    filter_params,
                )
            else:
                data_already_reindexed, data_to_reindex = self.filter_on_previous_cell(
                    filter_wd,
                    new_data,
                    data_already_reindexed,
                    batch_size,
                    filter_params,
                    current_unit_cell,
                )

        files_to_scale = self.reindex(
            reindex_wd,
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
        with open(data_reduction_wd / "data_reduction.json", "w") as fp:
            json.dump(data_reduction_progress, fp)

        self.scale_and_merge(scale_wd, files_to_scale, anomalous=anomalous, d_min=d_min)

    @staticmethod
    def filter_on_unit_cell_clustering(
        working_directory: Path,
        new_data: Dict[str, List[Path]],
        batch_size: int,
        filter_params: Dict[str, float],
    ) -> FilesDict:

        """
        Filter the integrated data using dials.cluster_unit_cell. Takes the
        largest cluster found and splits it into batches for reindexing.
        """
        xia2_logger.notice(banner("Clustering"))  # type: ignore
        main_cluster_files = cluster_all_unit_cells(
            working_directory,
            new_data,
            filter_params["threshold"],
        )

        # save the results to a json
        cluster_expts = load.experiment_list(
            main_cluster_files["expt"],
            check_format=False,
        )
        cluster_refls = flex.reflection_table.from_file(main_cluster_files["refl"])
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
        new_data: Dict[str, List[Path]],
        data_already_reindexed: FilesDict,
        batch_size: int,
        filter_params: Dict[str, float],
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
        space_group: sgtbx.space_group = None,
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
        scaled_expts, scaled_table = scale(
            working_directory, files_to_scale, anomalous, d_min
        )
        merge(working_directory, scaled_expts, scaled_table, d_min)
