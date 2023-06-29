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
    def _reindex(self) -> None:
        # First do parallel reindexing of each batch
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

        if len(scaled_results) > 1:
            # now batch cosym and batch scale
            if "scale" not in self._reduction_params.output_save_files:
                for result in scaled_results:
                    FileHandler.record_temporary_file(result.expt)
                    FileHandler.record_temporary_file(result.refl)
            xia2_logger.notice(banner("Reindexing"))  # type: ignore

            files_to_scale = cosym_reindex(
                self._reindex_wd,
                scaled_results,
                self._reduction_params.d_min,
                self._reduction_params.lattice_symmetry_max_delta,
            )
            xia2_logger.info(f"Consistently reindexed {len(scaled_results)} batches")
            if "cosym" not in self._reduction_params.output_save_files:
                for fp in files_to_scale:
                    FileHandler.record_temporary_file(fp.expt)
                    FileHandler.record_temporary_file(fp.refl)
            xia2_logger.notice(banner("Scaling"))  # type: ignore
            outfiles = batch_scale(
                self._scale_wd, files_to_scale, self._reduction_params
            )
            xia2_logger.info("Completed joint scaling of all batches")
            self._files_to_merge = outfiles
        else:
            expt_f = scaled_results[0].expt
            new_expt_f = expt_f.parent / "scaled_1.expt"
            expt_f.rename(new_expt_f)
            refl_f = scaled_results[0].refl
            new_refl_f = refl_f.parent / "scaled_1.refl"
            refl_f.rename(new_refl_f)
            FileHandler.record_data_file(new_expt_f)
            FileHandler.record_data_file(new_refl_f)
            self._files_to_merge = [FilePair(new_expt_f, new_refl_f)]

    def _scale(self) -> None:
        xia2_logger.notice(banner("Scaling"))  # type: ignore
        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)

        scaled_results = []
        batch_template = functools.partial(
            "batch{index:0{maxindexlength:d}d}".format,
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

        if len(scaled_results) > 1:
            if "scale" not in self._reduction_params.output_save_files:
                for fp in scaled_results:
                    FileHandler.record_temporary_file(fp.expt)
                    FileHandler.record_temporary_file(fp.refl)
            self._files_to_merge = batch_scale(
                self._scale_wd, scaled_results, self._reduction_params
            )
            xia2_logger.info("Completed joint scaling of all batches")
        else:
            expt_f = scaled_results[0].expt
            new_expt_f = expt_f.parent / "scaled_1.expt"
            expt_f.rename(new_expt_f)
            refl_f = scaled_results[0].refl
            new_refl_f = refl_f.parent / "scaled_1.refl"
            refl_f.rename(new_refl_f)
            FileHandler.record_data_file(new_expt_f)
            FileHandler.record_data_file(new_refl_f)
            self._files_to_merge = [FilePair(new_expt_f, new_refl_f)]

        # The final scaled files should be kept, to allow further analysis

        # The merged files should be kept to allow quick merging (allowing for merge groups too).
