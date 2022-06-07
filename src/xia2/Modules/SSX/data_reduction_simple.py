from __future__ import annotations

import concurrent.futures
import copy
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import iotbx.phil
from cctbx import crystal, sgtbx, uctbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (  # reference_reindex,
    CrystalsData,
    CrystalsDict,
    FilePair,
    FilesDict,
    cosym_reindex,
    determine_best_unit_cell_from_crystals,
    load_crystal_data_from_new_expts,
    merge,
    run_uc_cluster,
    scale,
    scale_against_model,
    scale_cosym,
    select_crystals_close_to,
    split_filtered_data,
)
from xia2.Modules.SSX.reporting import statistics_output_from_scaled_files

xia2_logger = logging.getLogger(__name__)


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
    central_unit_cell: Optional[uctbx.unit_cell] = None
    model: Optional[Path] = None

    @classmethod
    def from_phil(cls, params: iotbx.phil.scope_extract):
        """Construct from xia2.cli.ssx phil_scope."""
        model = None
        if params.scaling.model:
            model = Path(params.scaling.model).resolve()
        if params.clustering.central_unit_cell and params.clustering.threshold:
            raise ValueError(
                "Only one of clustering.central_unit_cell and clustering.threshold can be specified"
            )
        return cls(
            params.symmetry.space_group,
            params.batch_size,
            params.nproc,
            params.d_min,
            params.scaling.anomalous,
            params.clustering.threshold,
            params.clustering.absolute_angle_tolerance,
            params.clustering.absolute_length_tolerance,
            params.clustering.central_unit_cell,
            model,
        )


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


class SimpleDataReduction(BaseDataReduction):
    def _load_previously_prepared(self, reindex_results: Path) -> FilesDict:
        with reindex_results.open(mode="r") as f:
            previous = json.load(f)
        data_already_reindexed = {
            int(i): FilePair(Path(v["expt"]), Path(v["refl"]))
            for i, v in previous["reindexed_files"].items()
        }
        for file_pair in data_already_reindexed.values():
            file_pair.check()
        return data_already_reindexed

    def _load_filtering_results(
        self, filter_results: Path
    ) -> Tuple[uctbx.unit_cell, sgtbx.space_group_info]:
        with filter_results.open(mode="r") as f:
            result = json.load(f)
        best_unit_cell = uctbx.unit_cell(result["best_unit_cell"])
        current_sg = sgtbx.space_group_info(number=result["space_group"])
        return best_unit_cell, current_sg

    def _save_reindexing_results(self, reindex_wd, files_to_scale):
        output_files_to_scale = {
            k: {"expt": str(v.expt), "refl": str(v.refl)}
            for k, v in files_to_scale.items()
        }
        if not Path.is_dir(reindex_wd):
            Path.mkdir(reindex_wd)
        reidx_results = reindex_wd / "reindexing_results.json"
        data = {"reindexed_files": output_files_to_scale}
        with reidx_results.open(mode="w") as f:
            json.dump(data, f, indent=2)

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

        # see if we have any data that has been marked as successfully reindexed.
        reidx_results = reindex_wd / "reindexing_results.json"
        if reidx_results.is_file():
            data_already_reindexed = self._load_previously_prepared(reidx_results)

        previous_best_unit_cell = None
        previous_space_group = None
        new_best_unit_cell = None
        new_space_group = None
        filter_results = filter_wd / "filter_results.json"
        if filter_results.is_file():
            (
                previous_best_unit_cell,
                previous_space_group,
            ) = self._load_filtering_results(filter_results)

        # First filter any new data
        if self.new_to_process:
            xia2_logger.notice(banner("Filtering"))  # type: ignore
            crystals_data = load_crystal_data_from_new_expts(self.new_to_process)
            new_space_group = check_consistent_space_group(crystals_data)

            good_crystals_data = self.filter_new_data(
                filter_wd, crystals_data, previous_best_unit_cell, reduction_params
            )
            if not any(v.crystals for v in good_crystals_data.values()):
                raise ValueError("No crystals remain after filtering")

            if (
                previous_best_unit_cell and previous_space_group
            ):  # i.e. if previous data reduction
                if (
                    new_space_group.type().number()
                    != previous_space_group.type().number()
                ):
                    raise ValueError(
                        "Previous input data was not in same space group as new data:\n"
                        f"{previous_space_group.type().number()} != {new_space_group.type().number()}"
                    )
                # we want all jobs to use at least batch_size crystals, so join on
                # to last reindexed batch until this has been satisfied
                n_cryst = sum(len(v.identifiers) for v in good_crystals_data.values())
                while n_cryst < reduction_params.batch_size:
                    already_reidx_keys = list(data_already_reindexed.keys())
                    if not already_reidx_keys:
                        break
                    last_batch = data_already_reindexed.pop(already_reidx_keys[-1])
                    last_expts = load.experiment_list(
                        last_batch.expt, check_format=False
                    )
                    # copy to avoid keeping reference to expt list
                    good_crystals_data[str(last_batch.expt)] = CrystalsData(
                        identifiers=copy.deepcopy(last_expts.identifiers()),
                        crystals=copy.deepcopy(last_expts.crystals()),
                        keep_all_original=True,
                    )
                    self.new_to_process.append(last_batch)
                    n_cryst += len(last_expts)

            # current_sg = new_sg
            # Split the data, with an offset so that they keys of
            # data_to_reindex don't clash with data_already_reindexed
            n_already_reindexed_files = len(list(data_already_reindexed.keys()))
            # ^ will be 0 if no previous reduction.

            # Now split the data into batches for reindexing/scaling
            data_to_reindex = split_filtered_data(
                filter_wd,
                self.new_to_process,
                good_crystals_data,
                reduction_params.batch_size,
                offset=n_already_reindexed_files,
            )
            # Make a crystals_data object with all data for writing out
            # an updated best unit cell.
            for file_pair in data_already_reindexed.values():
                expts = load.experiment_list(file_pair.expt, check_format=False)
                good_crystals_data[str(file_pair.expt)] = CrystalsData(
                    crystals=copy.deepcopy(expts.crystals()),
                    identifiers=[],
                )
            new_best_unit_cell = self._write_unit_cells_to_json(
                filter_wd, good_crystals_data
            )

        else:
            # new_best_unit_cell = previous_best_unit_cell
            if not (previous_best_unit_cell and previous_space_group):
                raise ValueError(
                    "Error in intepreting new and previous processing results"
                )
            new_best_unit_cell = previous_best_unit_cell
            new_space_group = previous_space_group

        # Use the space group from integration if not explicity specified.
        if not reduction_params.space_group:
            reduction_params.space_group = new_space_group
            xia2_logger.info(f"Using space group: {str(new_space_group)}")

        # Now check if we need to reindex due to indexing ambiguities
        if data_to_reindex:
            sym_requires_reindex = assess_for_indexing_ambiguities(
                reduction_params.space_group, new_best_unit_cell
            )
            if sym_requires_reindex:
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

        self._save_reindexing_results(reindex_wd, files_to_scale)

        # if we get here, we have successfully prepared the new data for scaling.
        # So save this to allow reloading in future for iterative workflows.
        self._save_as_prepared()

        # Finally scale and merge the data.
        if reduction_params.model:
            self.scale_and_merge_using_model(
                scale_wd,
                files_to_scale,
                anomalous=reduction_params.anomalous,
                d_min=reduction_params.d_min,
                model=reduction_params.model,
                nproc=reduction_params.nproc,
                best_unit_cell=new_best_unit_cell,
            )
        else:
            self.scale_and_merge(
                scale_wd,
                files_to_scale,
                anomalous=reduction_params.anomalous,
                d_min=reduction_params.d_min,
                best_unit_cell=new_best_unit_cell,
            )

    @staticmethod
    def filter_new_data(
        working_directory: Path,
        crystals_data: dict,
        best_unit_cell: uctbx.unit_cell,
        reduction_params: SimpleReductionParams,
    ) -> CrystalsDict:

        if not best_unit_cell:  # i.e. no previous data reduction
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
                new_best_unit_cell = determine_best_unit_cell_from_crystals(
                    crystals_data
                )
                good_crystals_data = select_crystals_close_to(
                    crystals_data,
                    new_best_unit_cell,
                    reduction_params.absolute_angle_tolerance,
                    reduction_params.absolute_length_tolerance,
                )
            else:  # join all data for splitting
                good_crystals_data = crystals_data
                xia2_logger.info("No unit cell filtering applied")

        else:
            xia2_logger.info("Using cell parameters from previous clustering analysis")
            if (
                reduction_params.absolute_angle_tolerance
                and reduction_params.absolute_length_tolerance
            ):
                good_crystals_data = select_crystals_close_to(
                    crystals_data,
                    best_unit_cell,
                    reduction_params.absolute_angle_tolerance,
                    reduction_params.absolute_length_tolerance,
                )
            else:
                good_crystals_data = crystals_data
                xia2_logger.info("No unit cell filtering applied")

        return good_crystals_data

    @staticmethod
    def _write_unit_cells_to_json(
        working_directory: Path,
        crystals_dict: CrystalsDict,
    ) -> uctbx.unit_cell:
        # now write out the best cell
        new_best_unit_cell = determine_best_unit_cell_from_crystals(crystals_dict)
        all_ucs = []
        for v in crystals_dict.values():
            all_ucs.extend([c.get_unit_cell().parameters() for c in v.crystals])
        sg = v.crystals[0].get_space_group().type().number()
        n_cryst = len(all_ucs)
        result = {
            "best_unit_cell": [round(i, 4) for i in new_best_unit_cell.parameters()],
            "n_cryst": n_cryst,
            "unit_cells": all_ucs,
            "space_group": sg,
        }
        with (working_directory / "filter_results.json").open(mode="w") as fp:
            json.dump(result, fp, indent=2)
        return new_best_unit_cell

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
        ambiguities. If there is more than one batch, the dials.cosym is run
        again to make sure all batches are consistently indexed.
        """
        sys.stdout = open(os.devnull, "w")  # block printing from cosym

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)

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
                    reindexed_results.update(result)

        # now do reference reindexing
        files_to_scale = {**data_already_reindexed, **reindexed_results}
        if len(files_to_scale) > 1:
            cosym_reindex(working_directory, files_to_scale, d_min)

        sys.stdout = sys.__stdout__  # restore printing
        return files_to_scale

    @staticmethod
    def scale_and_merge(
        working_directory: Path,
        files_to_scale: FilesDict,
        anomalous: bool = True,
        d_min: float = None,
        best_unit_cell: Optional[uctbx.unit_cell] = None,
    ) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)
        xia2_logger.notice(banner("Scaling"))  # type: ignore
        scaled_expts, scaled_table = scale(
            working_directory,
            files_to_scale,
            anomalous,
            d_min,
            best_unit_cell,
        )
        xia2_logger.notice(banner("Merging"))  # type: ignore
        merge(working_directory, scaled_expts, scaled_table, d_min)

    @staticmethod
    def scale_and_merge_using_model(
        working_directory: Path,
        files_to_scale: FilesDict,
        anomalous: bool = True,
        d_min: float = None,
        model: Path = None,
        nproc: int = 1,
        best_unit_cell: Optional[uctbx.unit_cell] = None,
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
                    best_unit_cell,
                ): index
                for index, files in files_to_scale.items()
            }
            for future in concurrent.futures.as_completed(scale_futures):
                try:
                    result = future.result()
                    i = scale_futures[future]
                except Exception as e:
                    xia2_logger.warning(f"Unsuccessful scaling of group. Error:\n{e}")
                else:
                    xia2_logger.info(f"Completed scaling of group {i+1}")
                    scaled_results.update(result)

        xia2_logger.notice(banner("Merging"))  # type: ignore
        with record_step("joining for merge"):
            scaled_expts = ExperimentList([])
            scaled_tables = []
            # For merging (a simple program), we don't require much data in the
            # reflection table. So to avoid a large memory spike, just keep the
            # values we know we need for merging and to report statistics
            # first 6 in keep are required in merge, the rest will potentially
            #  be used for filter_reflections call in merge
            keep = [
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
            for file_pair in scaled_results.values():
                scaled_expts.extend(
                    load.experiment_list(file_pair.expt, check_format=False)
                )
                table = flex.reflection_table.from_file(file_pair.refl)
                for k in list(table.keys()):
                    if k not in keep:
                        del table[k]
                scaled_tables.append(table)
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

        merge(working_directory, scaled_expts, scaled_table, d_min, best_unit_cell)
