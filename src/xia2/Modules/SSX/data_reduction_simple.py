from __future__ import annotations

import logging
from pathlib import Path

from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_reduction_base import BaseDataReduction
from xia2.Modules.SSX.data_reduction_programs import (
    assess_for_indexing_ambiguities,
    check_consistent_space_group,
    cosym_reindex,
    determine_best_unit_cell_from_crystals,
    load_crystal_data_from_new_expts,
    merge,
    parallel_cosym,
    scale,
    FilePair,
)
from xia2.Modules.SSX.reporting import statistics_output_from_scaled_files


from xia2.Modules.SSX.yml_handling import yml_to_filesdict
from xia2.Modules.SSX.data_reduction_programs import split_integrated_data

xia2_logger = logging.getLogger(__name__)

from dxtbx.serialize import load
import yaml
from yaml.loader import SafeLoader
import h5py
import numpy as np
from dxtbx.model import ExperimentList
from dials.array_family import flex


#expt_file = "batch_2/integrated_1.expt"
#structure = "structure.yaml"

#expts = load.experiment_list(expt_file, check_format=False)

'''def split_experiments_to_groups(expts, table, structure):

    with open(structure, 'r') as f:
        data = list(yaml.load_all(f, Loader=SafeLoader))
        groupby = data[0]["structure"]["group_by"]["values"][0]
        file, metadata = groupby.split(":")
        print(file)
        print(metadata)
        with h5py.File(file, mode="r") as filedata:
            metadata = metadata.split("/")[1:]
            print(metadata)
            while metadata:
                next = metadata.pop(0)
                print(next)
                filedata = filedata[next]
            groups_for_images = filedata[()]

        output_expts = [[] for _ in range(np.max(groups_for_images)+1)]

        def map_expt_to_group(expt):
            return groups_for_images[expt.imageset.indices()[0]]

        groups = map(map_expt_to_group, expts)

        for expt, g in zip(expts, groups):
            output_expts[g].append(expt)
        #print(list(groups))
    elists = [ExperimentList(e) for e in output_expts]
    refls = []
    for e in elists:
        refls.append(table.select_on_experiment_identifiers(e.identifiers()))
    return (elists, refls)'''


class SimpleDataReduction(BaseDataReduction):

    _no_input_error_msg = (
        "No input integrated data, or previously processed scale directories\n"
        + "have been found in the input. Please provide at least some integrated data or\n"
        + "a directory of data previously scaled with xia2.ssx/xia2.ssx_reduce\n"
        + " - Use directory= to specify a directory containing integrated data,\n"
        + "   or both reflections= and experiments= to specify integrated data files.\n"
        + " - Use processed_directory= to specify /data_reduction/scale directories of\n"
        + "   data previously processed in a similar manner (without a reference)."
    )

    def _run_only_previously_scaled(self):
        # ok, so want to check all consistent sg, do batch reindex if
        # necessary and then scale

        crystals_data = load_crystal_data_from_new_expts(self._previously_scaled_data)
        space_group = check_consistent_space_group(crystals_data)
        best_unit_cell = determine_best_unit_cell_from_crystals(crystals_data)

        if not self._reduction_params.space_group:
            self._reduction_params.space_group = space_group
            xia2_logger.info(f"Using space group: {str(space_group)}")

        sym_requires_reindex = assess_for_indexing_ambiguities(
            self._reduction_params.space_group,
            best_unit_cell,
            self._reduction_params.lattice_symmetry_max_delta,
        )
        if sym_requires_reindex and len(self._previously_scaled_data) > 1:
            xia2_logger.notice(banner("Reindexing"))
            self._files_to_scale = cosym_reindex(
                self._reindex_wd,
                self._previously_scaled_data,
                self._reduction_params.d_min,
                self._reduction_params.lattice_symmetry_max_delta,
            )
            xia2_logger.info("Consistently reindexed batches of previously scaled data")
        else:
            self._files_to_scale = self._previously_scaled_data
        xia2_logger.notice(banner("Scaling"))
        self._scale_and_merge()

    def _reindex(self) -> None:
        # First do parallel reindexing of each batch
        reindexed_new_files = list(
            parallel_cosym(
                self._reindex_wd,
                self._filtered_files_to_process,
                self._reduction_params,
                nproc=self._reduction_params.nproc,
            ).values()
        )
        # At this point, add in any previously scaled data.
        files_to_scale = reindexed_new_files + self._previously_scaled_data
        if len(files_to_scale) > 1:
            # Reindex all batches together.
            files_to_scale = cosym_reindex(
                self._reindex_wd,
                files_to_scale,
                self._reduction_params.d_min,
                self._reduction_params.lattice_symmetry_max_delta,
            )
            if self._previously_scaled_data:
                xia2_logger.info(
                    "Consistently reindexed all batches, including previously scaled data"
                )
            else:
                xia2_logger.info(
                    f"Consistently reindexed {len(reindexed_new_files)} batches"
                )
        if "scale_by" in self._parsed_yaml:
            self._files_to_scale = yml_to_filesdict(
                self._reindex_wd,
                self._parsed_yaml,
                files_to_scale,
            )
        else:
            self._files_to_scale =  {"scalegroup_1" : files_to_scale}

    def _prepare_for_scaling(self, good_crystals_data) -> None:
        if self._parsed_yaml:
            if "scale_by" in self._parsed_yaml:
                self._files_to_scale = yml_to_filesdict(
                    self._filter_wd,
                    self._parsed_yaml,
                    self._integrated_data,
                    good_crystals_data,
                )
            else:
                new_files_to_process = split_integrated_data(
                    self._filter_wd,
                    good_crystals_data,
                    self._integrated_data,
                    self._reduction_params,
                )
                self._files_to_scale = {"scalegroup_1" : [i for i in new_files_to_process.values()]}
        else:
            new_files_to_process = split_integrated_data(
                self._filter_wd,
                good_crystals_data,
                self._integrated_data,
                self._reduction_params,
            )
            self._files_to_scale = {"scalegroup_1" : [i for i in new_files_to_process.values()]}


    def _scale_and_merge(self) -> None:
        """Run scaling and merging"""

        if not Path.is_dir(self._scale_wd):
            Path.mkdir(self._scale_wd)
        from collections import defaultdict
        scaled_results = defaultdict(list)

        from xia2.Handlers.Files import FileHandler
        if len(self._files_to_scale) > 1:
            pass
        else:
            name = list(self._files_to_scale.keys())[0]
            flist = self._files_to_scale[name]
            result = scale(
                self._scale_wd,
                flist,#self._files_to_scale,
                self._reduction_params,
                name=name
            )
            xia2_logger.info(f"Completed scaling of {', '.join(name.split('.'))}")
            scaled_results[name.split('.')[0]].append(result)
            FileHandler.record_data_file(result.expt)
            FileHandler.record_data_file(result.refl)
            FileHandler.record_log_file(
                f"dials.scale.{name}", self._scale_wd / f"dials.scale.{name}.log"
            )
            #scaled_results = dict(sorted(scaled_results.items()))

            from cctbx import sgtbx, uctbx
            #stats_summary, _ = statistics_output_from_scaled_files(
            #    scaled_expts, scaled_table, self._reduction_params.central_unit_cell , self._reduction_params.d_min
            #)
            uc_params = [flex.double() for _ in range(6)]
            for filepairs in scaled_results.values():
                for fp in filepairs:
                    expts = load.experiment_list(fp.expt, check_format=False)
                    for c in expts.crystals():
                        unit_cell = c.get_recalculated_unit_cell() or c.get_unit_cell()
                        for i, p in enumerate(unit_cell.parameters()):
                            uc_params[i].append(p)
            best_unit_cell = uctbx.unit_cell(parameters=[flex.median(p) for p in uc_params])
            self._reduction_params.central_unit_cell = best_unit_cell
            n_final = len(uc_params[0])
            uc_str = ", ".join(str(round(i, 3)) for i in best_unit_cell.parameters())
            xia2_logger.info(
                f"{n_final} crystals in total scaled in space group {self._reduction_params.space_group}\nMedian cell: {uc_str}"
            )
            from xia2.Handlers.Streams import banner
            xia2_logger.notice(banner("Merging"))
            merge_input = {}
            if self._parsed_yaml:
                if "merge_by" in self._parsed_yaml:
                    for name, scaled_files in scaled_results.items():
                        groups_for_merge = yml_to_filesdict(
                            self._reindex_wd,
                            self._parsed_yaml,
                            scaled_files,
                            grouping="merge_by"
                        )
                        for g, flist in groups_for_merge.items():
                            merge_input[f"{name}.{g}"] = flist
                else:
                    merge_input = scaled_results
            else:
                merge_input = scaled_results

            from xia2.Modules.SSX.data_reduction_with_reference import merge_scalegroup

            from xia2.Driver.timing import record_step

            import concurrent.futures
            future_list = [] # do it this way to get results in order for consistent printing
            with record_step(
                "dials.merge (parallel)"
            ), concurrent.futures.ProcessPoolExecutor(
                max_workers=self._reduction_params.nproc
            ) as pool:
                for name, results in merge_input.items():
                    future_list.append(
                        pool.submit(
                            merge_scalegroup,
                            self._merge_wd,
                            results,
                            self._reduction_params,
                            name,
                        )
                    )
            for name, future in zip(merge_input.keys(), future_list):
                try:
                    summary = future.result()
                    xia2_logger.info(summary)
                except Exception as e:
                    xia2_logger.warning(f"Unsuccessful merging of {', '.join(name.split('.'))}. Error:\n{e}")

