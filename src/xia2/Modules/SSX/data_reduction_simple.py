from __future__ import annotations

import concurrent.futures
import functools
import logging
from pathlib import Path
from typing import Any, Dict

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    FilePair,
    batch_scale,
    cosym_reindex,
    parallel_cosym,
    scale,
)

xia2_logger = logging.getLogger(__name__)


class SimpleDataReduction(BaseDataReduction):
    def _prepare_for_scaling(self, good_crystals_data) -> None:
        # Really this means prepare for the final scale, so do parallel
        # batch scaling if >1 batch.
        super()._prepare_for_scaling(good_crystals_data)
        if len(self._files_to_scale) > 1:
            self._files_to_scale = self._scale_parallel_batches(self._files_to_scale)

    def _scale_parallel_batches(self, files):
        # scale multiple batches in parallel
        scaled_results = []
        batch_template = functools.partial(
            "batch{index:0{maxindexlength:d}d}".format,
            maxindexlength=len(str(len(files))),
        )
        jobs = {f"{batch_template(index=i+1)}": fp for i, fp in enumerate(files)}
        xia2_logger.notice(banner("Scaling"))  # type: ignore
        with record_step(
            "dials.scale (parallel)"
        ), concurrent.futures.ProcessPoolExecutor(
            max_workers=min(self._reduction_params.nproc, len(files))
        ) as pool:
            scale_futures: Dict[Any, str] = {
                pool.submit(
                    scale,
                    self._scale_wd,
                    [files],
                    self._reduction_params,
                    name,
                ): name
                for name, files in jobs.items()
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
                    if "scale" not in self._reduction_params.output_save_files:
                        FileHandler.record_temporary_file(result.exptfile)
                        FileHandler.record_temporary_file(result.reflfile)

        if not scaled_results:
            raise ValueError("No groups successfully scaled")
        return scaled_results

    def _reindex(self) -> None:
        # First do parallel reindexing of each batch
        xia2_logger.notice(banner("Reindexing"))  # type: ignore
        reindexed_new_files = parallel_cosym(
            self._reindex_wd,
            self._filtered_files_to_process,
            self._reduction_params,
            nproc=self._reduction_params.nproc,
        )

        if len(reindexed_new_files) > 1:
            scaled_results = self._scale_parallel_batches(reindexed_new_files)

            if len(scaled_results) > 1:
                # now batch cosym to finish internal resolution of ambiguity
                if "scale" not in self._reduction_params.output_save_files:
                    for result in scaled_results:
                        FileHandler.record_temporary_file(result.expt)
                        FileHandler.record_temporary_file(result.refl)
                xia2_logger.notice(banner("Reindexing"))  # type: ignore

                self._files_to_scale = cosym_reindex(
                    self._reindex_wd,
                    scaled_results,
                    self._reduction_params.d_min,
                    self._reduction_params.lattice_symmetry_max_delta,
                    self._reduction_params.partiality_threshold,
                    self._reduction_params.nproc,
                )
                xia2_logger.info(
                    f"Consistently reindexed {len(scaled_results)} batches"
                )
                if "cosym" not in self._reduction_params.output_save_files:
                    for fp in self._files_to_scale:
                        FileHandler.record_temporary_file(fp.expt)
                        FileHandler.record_temporary_file(fp.refl)

        else:
            self._files_to_scale = reindexed_new_files

    def _scale(self) -> None:
        # Do the final scaling job i.e. batch scaling if njobs > 1, standard scale job if njobs=1
        xia2_logger.notice(banner("Scaling"))  # type: ignore
        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        if len(self._files_to_scale) > 1:
            # batch scale
            self._files_to_merge = batch_scale(
                self._scale_wd, self._files_to_scale, self._reduction_params
            )
            xia2_logger.info("Completed joint scaling of all batches")
        else:
            result = scale(self._scale_wd, self._files_to_scale, self._reduction_params)
            xia2_logger.info("Completed scaling of data reduction batch 1")
            self._files_to_merge = [FilePair(result.exptfile, result.reflfile)]
            FileHandler.record_log_file(
                result.logfile.name.rstrip(".log"), result.logfile
            )
        for fp in self._files_to_merge:
            FileHandler.record_data_file(fp.expt)
            FileHandler.record_data_file(fp.refl)

        # The final scaled files should be kept, to allow further analysis

        # The merged files should be kept to allow quick merging (allowing for merge groups too).
