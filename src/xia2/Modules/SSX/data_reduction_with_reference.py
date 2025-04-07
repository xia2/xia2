from __future__ import annotations

import concurrent.futures
import functools
import logging
from pathlib import Path
from typing import Any

from cctbx import sgtbx, uctbx

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    CrystalsDict,
    FilePair,
    filter_,
    scale_against_reference,
)

xia2_logger = logging.getLogger(__name__)


class DataReductionWithReference(BaseDataReduction):
    ### This implementation uses the reference model when reindexing and scaling,
    ### allowing parallel processing in batches.

    def _filter(self) -> tuple[CrystalsDict, uctbx.unit_cell, sgtbx.space_group_info]:
        good_crystals_data, best_unit_cell, space_group = filter_(
            self._filter_wd, self._integrated_data, self._reduction_params
        )
        self._reduction_params.central_unit_cell = best_unit_cell  # store the
        # updated value to use in scaling
        return good_crystals_data, best_unit_cell, space_group

    def _scale(self) -> None:
        """Run scaling"""

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        scaled_results = [FilePair()] * len(self._batches_to_scale)

        batch_template = functools.partial(
            "scaled_batch{index:0{maxindexlength:d}d}".format,
            maxindexlength=len(str(len(self._batches_to_scale))),
        )
        jobs = {
            f"{batch_template(index=i + 1)}": fp
            for i, fp in enumerate(self._batches_to_scale)
        }

        with (
            record_step("dials.scale (parallel)"),
            concurrent.futures.ProcessPoolExecutor(
                max_workers=self._reduction_params.nproc
            ) as pool,
        ):
            scale_futures: dict[Any, int] = {
                pool.submit(
                    scale_against_reference,
                    self._scale_wd,
                    batch,
                    self._reduction_params,
                    name,
                ): idx
                for idx, (name, batch) in enumerate(jobs.items())
            }
            for future in concurrent.futures.as_completed(scale_futures):
                try:
                    result = future.result()
                    idx = scale_futures[future]
                except Exception as e:
                    xia2_logger.warning(f"Unsuccessful scaling of group. Error:\n{e}")
                else:
                    xia2_logger.info(f"Completed scaling of batch {idx + 1}")
                    scaled_results[idx] = FilePair(result.exptfile, result.reflfile)
                    FileHandler.record_data_file(result.exptfile)
                    FileHandler.record_data_file(result.reflfile)
                    FileHandler.record_log_file(
                        result.logfile.name.rstrip(".log"), result.logfile
                    )
        scaled_results = [s for s in scaled_results if s.expt]
        if not scaled_results:
            raise ValueError("No groups successfully scaled")
        self._files_to_merge = scaled_results
