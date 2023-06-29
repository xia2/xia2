from __future__ import annotations

import concurrent.futures
import functools
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from cctbx import sgtbx, uctbx

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    CrystalsDict,
    FilePair,
    filter_,
    parallel_cosym,
    reindex_against_reference,
    scale,
    scale_against_reference,
)

xia2_logger = logging.getLogger(__name__)


class DataReductionWithReference(BaseDataReduction):

    ### This implementation uses the reference model when reindexing and scaling,
    ### allowing parallel processing in batches.

    def _filter(self) -> Tuple[CrystalsDict, uctbx.unit_cell, sgtbx.space_group_info]:
        good_crystals_data, best_unit_cell, space_group = filter_(
            self._filter_wd, self._integrated_data, self._reduction_params
        )
        self._reduction_params.central_unit_cell = best_unit_cell  # store the
        # updated value to use in scaling
        return good_crystals_data, best_unit_cell, space_group

    def _reindex(self) -> None:
        """self._files_to_scale = parallel_cosym_reference(
            self._reindex_wd,
            self._filtered_files_to_process,
            self._reduction_params,
            nproc=self._reduction_params.nproc,
        )"""
        xia2_logger.notice(banner("Reindexing"))  # type: ignore
        reindexed_new_files = parallel_cosym(
            self._reindex_wd,
            self._filtered_files_to_process,
            self._reduction_params,
            nproc=self._reduction_params.nproc,
        )

        # now scale all batches
        scaled_results = []
        batch_template = functools.partial(
            "batch{index:0{maxindexlength:d}d}".format,
            maxindexlength=len(str(len(reindexed_new_files))),
        )
        jobs = {
            f"{batch_template(index=i+1)}": fp
            for i, fp in enumerate(reindexed_new_files)
        }
        xia2_logger.notice(banner("Scaling"))  # type: ignore
        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            scale_futures: Dict[Any, str] = {
                pool.submit(
                    scale,
                    self._scale_wd,
                    [files],
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
                    xia2_logger.info(
                        f"Completed scaling of data reduction batch {name.lstrip('batch')}"
                    )
                    scaled_results.append(FilePair(result.exptfile, result.reflfile))
                    FileHandler.record_log_file(
                        result.logfile.name.rstrip(".log"), result.logfile
                    )

        if not scaled_results:
            raise ValueError("No groups successfully scaled")

        # Now reindex each batch against reference with dials.reindex
        reindex_results = []
        template = functools.partial(
            "{index:0{maxindexlength:d}d}".format,
            maxindexlength=len(str(len(scaled_results))),
        )
        xia2_logger.notice(banner("Scaling"))  # type: ignore
        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=self._reduction_params.nproc
        ) as pool:
            reidx_futures: List[Any] = [
                pool.submit(
                    reindex_against_reference,
                    self._reindex_wd,
                    fp,
                    self._reduction_params,
                    template(index=i),
                )
                for i, fp in enumerate(scaled_results)  # .items()
            ]
            for future in concurrent.futures.as_completed(reidx_futures):
                try:
                    result = future.result()
                    reindex_results.append(result)
                except Exception as e:
                    xia2_logger.warning(
                        f"Unsuccessful reindexing of group. Error:\n{e}"
                    )
                else:
                    xia2_logger.info("Reindexed against reference")
                    """FileHandler.record_log_file(
                        result.logfile.name.rstrip(".log"), result.logfile
                    )"""

        self._files_to_scale = reindex_results
        print(self._files_to_scale)
        self._scale()
        # then scale in batches against ref

    def _scale(self) -> None:
        """Run scaling"""

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        scaled_results = []

        batch_template = functools.partial(
            "scaled_batch{index:0{maxindexlength:d}d}".format,
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
                # try:
                result = future.result()
                name = scale_futures[future]
                # except Exception as e:
                #    xia2_logger.warning(f"Unsuccessful scaling of group. Error:\n{e}")
                # else:
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
