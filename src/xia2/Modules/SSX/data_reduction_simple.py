from __future__ import annotations

import concurrent.futures
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

from cctbx import crystal, sgtbx, uctbx
from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_base import (
    BaseDataReduction,
    FilePair,
    FilesDict,
    ReductionParams,
)
from xia2.Modules.SSX.data_reduction_programs import (
    CrystalsDict,
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


def get_reducer(reduction_params: ReductionParams) -> Type[BaseDataReduction]:
    if reduction_params.model:
        return DataReductionWithPDBModel
    else:
        return SimpleDataReduction


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


def _filter(working_directory, integrated_data, reduction_params):

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


class SimpleDataReduction(BaseDataReduction):

    _no_input_error_msg = (
        "No input integrated data, or previously processed scale directories\n"
        + "have been found in the input. Please provide at least some integrated data or\n"
        + "a directory of data previously scaled with xia2.ssx/xia2.ssx_reduce\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated data files.\n"
        + " - Use processed_directory= to specify /data_reduction/scale directories of\n"
        + "   data previously processed in a similar manner (without a PDB model as reference)."
    )

    def _run_only_previously_scaled(self):
        # ok, so want to check all consistent sg, do batch reindex if
        # necessary and then scale

        data_reduction_wd = self._main_directory / "data_reduction"
        reindex_wd = data_reduction_wd / "reindex"
        scale_wd = data_reduction_wd / "scale"

        crystals_data = load_crystal_data_from_new_expts(self._previously_scaled_data)
        space_group = check_consistent_space_group(crystals_data)
        best_unit_cell = determine_best_unit_cell_from_crystals(crystals_data)

        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group, best_unit_cell
        )
        if sym_requires_reindex and len(self._previously_scaled_data) > 1:
            files_to_scale = cosym_reindex(
                reindex_wd, self._previously_scaled_data, self._reduction_params.d_min
            )
            xia2_logger.info("Consistently reindexed batches of previously scaled data")
        else:
            files_to_scale = self._previously_scaled_data
        self.scale_and_merge(scale_wd, files_to_scale, self._reduction_params)

    def run(self) -> None:
        """
        A simple workflow for data reduction. First filter the input data, either
        by clustering on unit cells, or comparing against a previous cell. Then
        reindex data in batches, using cosym, followed by scaling and merging.
        """

        data_reduction_wd = self._main_directory / "data_reduction"
        filter_wd = data_reduction_wd / "prefilter"
        reindex_wd = data_reduction_wd / "reindex"
        scale_wd = data_reduction_wd / "scale"

        if not self._integrated_data:
            self._run_only_previously_scaled()
            return

        # first filter the data.
        xia2_logger.notice(banner("Filtering"))  # type: ignore
        new_files_to_process, best_unit_cell, space_group = _filter(
            filter_wd, self._integrated_data, self._reduction_params
        )

        # ok so now need to reindex
        # Use the space group from integration if not explicity specified.
        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group, best_unit_cell
        )
        if sym_requires_reindex:
            # First do parallel reindexing of each batch
            reindexed_new_files = list(
                self.reindex(
                    reindex_wd,
                    new_files_to_process,
                    self._reduction_params,
                    nproc=self._reduction_params.nproc,
                ).values()
            )
            # At this point, add in any previously scaled data.
            files_to_scale = reindexed_new_files + self._previously_scaled_data
            if len(files_to_scale) > 1:
                # Reindex all batches together.
                files_to_scale = cosym_reindex(
                    reindex_wd, files_to_scale, self._reduction_params.d_min
                )
                if self._previously_scaled_data:
                    xia2_logger.info(
                        "Consistently reindexed all batches, including previously scaled data"
                    )
                else:
                    xia2_logger.info(
                        f"Consistently reindexed {len(reindexed_new_files)} batches"
                    )
        else:
            # Now add in any previously scaled data for scaling all together.
            files_to_scale = (
                list(new_files_to_process.values()) + self._previously_scaled_data
            )

        self.scale_and_merge(scale_wd, files_to_scale, self._reduction_params)

    @staticmethod
    def reindex(
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

    def scale_and_merge(
        self,
        working_directory: Path,
        files_to_scale: List[FilePair],
        reduction_params: ReductionParams,
    ) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)
        xia2_logger.notice(banner("Scaling"))  # type: ignore
        scaled_expts, scaled_table = scale(
            working_directory,
            files_to_scale,
            reduction_params,
        )
        xia2_logger.notice(banner("Merging"))  # type: ignore
        merge(
            working_directory,
            scaled_expts,
            scaled_table,
            reduction_params.d_min,
            reduction_params.central_unit_cell,
        )


def _wrap_extend_expts(first_elist, second_elist):
    try:
        first_elist.extend(second_elist)
    except RuntimeError as e:
        raise ValueError(
            "Unable to combine experiments, check for datafiles containing duplicate experiments.\n"
            + f"  Specific error message encountered:\n  {e}"
        )


class DataReductionWithPDBModel(BaseDataReduction):

    _no_input_error_msg = (
        "No input integrated data, or previously processed scale directories\n"
        + "have been found in the input. Please provide at least some integrated data or\n"
        + "a directory of data previously scaled with xia2.ssx/xia2.ssx_reduce\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated data files.\n"
        + " - Use processed_directory= to specify /data_reduction/scale directories of\n"
        + "   data previously processed with the same PDB model as reference."
    )

    def _combine_previously_scaled(self):
        scaled_expts = ExperimentList([])
        scaled_tables = []
        for file_pair in self._previously_scaled_data:
            prev_expts = load.experiment_list(file_pair.expt, check_format=False)
            _wrap_extend_expts(scaled_expts, prev_expts)
            table = flex.reflection_table.from_file(file_pair.refl)
            for k in list(table.keys()):
                if k not in scaled_cols_to_keep:
                    del table[k]
            scaled_tables.append(table)
        return scaled_expts, scaled_tables

    def _run_only_previously_scaled(self, working_directory):
        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)
        scaled_expts, scaled_tables = self._combine_previously_scaled()
        scaled_table = flex.reflection_table.concat(scaled_tables)
        n_final = len(scaled_expts)
        uc = determine_best_unit_cell(scaled_expts)
        uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
        xia2_logger.info(
            f"{n_final} crystals scaled in space group {scaled_expts[0].crystal.get_space_group().info()}\nMedian cell: {uc_str}"
        )
        xia2_logger.info("Summary statistics for combined previously scaled data")
        xia2_logger.info(
            statistics_output_from_scaled_files(scaled_expts, scaled_table, uc)
        )
        merge(
            working_directory,
            scaled_expts,
            scaled_table,
            self._reduction_params.d_min,
            uc,
            suffix="_all",
        )

    def run(self):

        # processing steps are filter, reindex and the scale.

        # If we have a reindexing strategy that uses the target model as a reference,
        # then know all are consistent. Else, we might need to do batch-based reindexing

        # scaling data can be done in batches, then can merge with prev scaled
        # to get overall stats

        # note that it is possible that there is no new data to process and we
        # just want to merge existing data.
        filter_wd = self._data_reduction_wd / "prefilter"
        reindex_wd = self._data_reduction_wd / "reindex"
        scale_wd = self._data_reduction_wd / "scale"

        if not self._integrated_data:
            self._run_only_previously_scaled(scale_wd)
            return

        # first filter the data.
        xia2_logger.notice(banner("Filtering"))  # type: ignore
        new_files_to_process, best_unit_cell, space_group = _filter(
            filter_wd, self._integrated_data, self._reduction_params
        )

        # ok so now need to reindex
        # Use the space group from integration if not explicity specified.
        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group, best_unit_cell
        )
        if sym_requires_reindex:
            # ideally - reindex each dataset against target, so don't need to
            # do anything with
            # on each batch - reindex internally to be consistent
            # then reindex against pdb model.
            # then scale
            ##FIXME need to implement this
            assert 0
            data_already_reindexed = {}
            files_to_scale = self.reindex(
                reindex_wd,
                new_files_to_process,
                data_already_reindexed,
                self._reduction_params,
                nproc=self._reduction_params.nproc,
            )
            # then scale against target
        else:
            # just scale in batches against target
            # Finally scale and merge the data.
            files_to_scale = new_files_to_process
            self._reduction_params.central_unit_cell = best_unit_cell

        self.scale_and_merge(scale_wd, files_to_scale, self._reduction_params)

    def scale_and_merge(
        self,
        working_directory: Path,
        files_to_scale: FilesDict,
        reduction_params: ReductionParams,
    ) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(working_directory):
            Path.mkdir(working_directory)
        xia2_logger.notice(banner("Scaling using model"))  # type: ignore

        scaled_results: FilesDict = {}
        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=reduction_params.nproc
        ) as pool:
            scale_futures: Dict[Any, int] = {
                pool.submit(
                    scale_against_model,
                    working_directory,
                    files,
                    index,
                    reduction_params,
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
        if not scaled_results:
            raise ValueError("No groups successfully scaled")

        xia2_logger.notice(banner("Merging"))  # type: ignore

        with record_step("merging"):
            scaled_expts = ExperimentList([])
            scaled_tables = []
            # For merging (a simple program), we don't require much data in the
            # reflection table. So to avoid a large memory spike, just keep the
            # values we know we need for merging and to report statistics
            # first 6 in keep are required in merge, the rest will potentially
            #  be used for filter_reflections call in merge
            for file_pair in scaled_results.values():
                expts = load.experiment_list(file_pair.expt, check_format=False)
                _wrap_extend_expts(scaled_expts, expts)
                table = flex.reflection_table.from_file(file_pair.refl)
                for k in list(table.keys()):
                    if k not in scaled_cols_to_keep:
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
            merge(
                working_directory,
                scaled_expts,
                scaled_table,
                reduction_params.d_min,
                uc,
            )

            # export an unmerged mtz too

            # now add any extra data previously scaled
            if self._previously_scaled_data:
                (
                    prev_scaled_expts,
                    prev_scaled_tables,
                ) = self._combine_previously_scaled()
                _wrap_extend_expts(scaled_expts, prev_scaled_expts)
                scaled_table = flex.reflection_table.concat(
                    scaled_tables + prev_scaled_tables
                )

                # n_final = len(scaled_expts)
                uc = determine_best_unit_cell(scaled_expts)
                uc_str = ", ".join(str(round(i, 3)) for i in uc.parameters())
                xia2_logger.info(
                    "Summary statistics for all input data, including previously scaled"
                )
                xia2_logger.info(
                    statistics_output_from_scaled_files(scaled_expts, scaled_table, uc)
                )
                merge(
                    working_directory,
                    scaled_expts,
                    scaled_table,
                    reduction_params.d_min,
                    suffix="_all",
                )
