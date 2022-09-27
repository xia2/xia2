from __future__ import annotations

import concurrent.futures
import functools
import logging
from pathlib import Path
from typing import Any, Dict, Tuple

from cctbx import sgtbx, uctbx

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    CrystalsDict,
    FilePair,
    filter_,
    parallel_cosym_reference,
    scale_against_reference,
    split_integrated_data,
)

xia2_logger = logging.getLogger(__name__)


class DataReductionWithReference(BaseDataReduction):

    ### This implementation uses the reference model when reindexing and scaling,
    ### allowing parallel processing in batches. If there is any previously scaled
    ### data, this is just added in at the end at the point of merging.

    _no_input_error_msg = (
        "No input integrated data, or previously processed scale directories\n"
        + "have been found in the input. Please provide at least some integrated data or\n"
        + "a directory of data previously scaled with xia2.ssx/xia2.ssx_reduce\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated data files.\n"
        + " - Use processed_directory= to specify /data_reduction/scale directories of\n"
        + "   data previously processed with the same PDB model/data file as reference."
    )

    def _run_only_previously_scaled(self):

        if not Path.is_dir(self._merge_wd):
            Path.mkdir(self._merge_wd)

        self._files_to_merge = self._previously_scaled_data
        self._merge()

    def _filter(self) -> Tuple[CrystalsDict, uctbx.unit_cell, sgtbx.space_group_info]:
        good_crystals_data, best_unit_cell, space_group = filter_(
            self._filter_wd, self._integrated_data, self._reduction_params
        )
        self._reduction_params.central_unit_cell = best_unit_cell  # store the
        # updated value to use in scaling
        return good_crystals_data, best_unit_cell, space_group

    def _prepare_for_scaling(self, good_crystals_data) -> None:

        self._files_to_scale = split_integrated_data(
            self._filter_wd,
            good_crystals_data,
            self._integrated_data,
            self._reduction_params,
        )

    def _reindex(self) -> None:
        self._files_to_scale = parallel_cosym_reference(
            self._reindex_wd,
            self._filtered_files_to_process,
            self._reduction_params,
            nproc=self._reduction_params.nproc,
        )

    def _scale(self) -> None:
        """Run scaling"""

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        scaled_results = []

        batch_template = functools.partial(
            "scalebatch_{index:0{maxindexlength:d}d}".format,
            maxindexlength=len(str(len(self._files_to_scale))),
        )
        jobs = {
            f"{batch_template(index=i+1)}": fp
            for i, fp in enumerate(self._files_to_scale)
        }

        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            scale_futures: Dict[Any, str] = {
                pool.submit(
                    scale_against_reference,
                    self._scale_wd,
                    files,
                    self._reduction_params,
                    name,
                ): name
                for name, files in jobs.items()  # .items()
            }
            for future in concurrent.futures.as_completed(scale_futures):
                try:
                    result = future.result()
                    name = scale_futures[future]
                except Exception as e:
                    xia2_logger.warning(f"Unsuccessful scaling of group. Error:\n{e}")
                else:
                    xia2_logger.info(f"Completed scaling of {name}")
                    scaled_results.append(FilePair(result.exptfile, result.reflfile))
                    FileHandler.record_data_file(result.exptfile)
                    FileHandler.record_data_file(result.reflfile)
                    FileHandler.record_log_file(
                        result.logfile.name.rstrip(".log"), result.logfile
                    )

        if not scaled_results:
            raise ValueError("No groups successfully scaled")
        self._files_to_merge = scaled_results

    def _prepare_for_merging(self):

        if self._previously_scaled_data:
            self._files_to_merge += self._previously_scaled_data
