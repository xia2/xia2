from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from dials.array_family import flex
from dxtbx import flumpy
from dxtbx.serialize import load

from xia2.Modules.SSX.data_reduction_programs import FilePair, ReductionParams

xia2_logger = logging.getLogger(__name__)
from multiprocessing import Pool

from dials.util.filter_reflections import filter_reflection_table
from dials.util.image_grouping import (
    GroupsForExpt,
    ParsedYAML,
    SplittingIterable,
    get_grouping_handler,
)

from xia2.Modules.SSX.data_reduction_programs import trim_table_for_merge


def save_scaled_array_for_merge(
    input_: SplittingIterable,
) -> Optional[Tuple[str, FilePair]]:
    expts = load.experiment_list(input_.fp.expt, check_format=False)
    refls = flex.reflection_table.from_file(input_.fp.refl)
    trim_table_for_merge(refls)
    groupdata = input_.groupdata
    if (groupdata.single_group is not None) and (
        groupdata.single_group == input_.groupindex
    ):
        pass
    else:
        # need to select
        identifiers = expts.identifiers()
        sel = flumpy.from_numpy(input_.groupdata.groups_array == input_.groupindex)
        sel_identifiers = list(identifiers.select(sel))
        expts.select_on_experiment_identifiers(sel_identifiers)
        refls = refls.select_on_experiment_identifiers(sel_identifiers)
    if expts:
        best_uc = input_.params.central_unit_cell
        refls["d"] = best_uc.d(refls["miller_index"])
        for expt in expts:
            expt.crystal.set_unit_cell(best_uc)
        refls = filter_reflection_table(
            refls,
            intensity_choice=["scale"],
            d_min=input_.params.d_min,
            combine_partials=False,
            partiality_threshold=0.4,  # make this setable?
        )
        tmp = flex.reflection_table()
        tmp["miller_index"] = refls["miller_index"]
        tmp["intensity"] = refls["intensity.scale.value"]
        tmp["sigma"] = flex.sqrt(refls["intensity.scale.variance"])
        tmp = tmp.select(refls["inverse_scale_factor"] > 0)
        exptout = (
            input_.working_directory
            / f"group_{input_.groupindex}_{input_.fileindex}.expt"
        )
        reflout = (
            input_.working_directory
            / f"group_{input_.groupindex}_{input_.fileindex}.refl"
        )
        expts.as_file(exptout)
        tmp.as_file(reflout)
        return (input_.name, FilePair(exptout, reflout))
    return None


def apply_scaled_array_to_all_files(
    working_directory: Path,
    scaled_files: List[FilePair],
    reduction_params: ReductionParams,
) -> dict[str, List[FilePair]]:

    groupindex = 0
    name = "all data"
    groupdata = GroupsForExpt(0)
    input_iterable = []
    filesdict: dict[str, List[FilePair]] = {name: []}
    for i, fp in enumerate(scaled_files):
        input_iterable.append(
            SplittingIterable(
                working_directory,
                fp,
                i,
                groupindex,
                groupdata,
                name,
                reduction_params,
            )
        )
    if input_iterable:
        with Pool(min(reduction_params.nproc, len(input_iterable))) as pool:
            results = pool.map(save_scaled_array_for_merge, input_iterable)
        for result in results:
            if result:
                name = result[0]
                fp = result[1]
                filesdict[name].append(fp)
    return filesdict


def yml_to_merged_filesdict(
    working_directory: Path,
    parsed: ParsedYAML,
    integrated_files: List[FilePair],
    reduction_params: ReductionParams,
    grouping: str = "merge_by",
):

    handler = get_grouping_handler(parsed, grouping, reduction_params.nproc)

    filesdict = handler.split_files_to_groups(
        working_directory,
        integrated_files,
        function_to_apply=save_scaled_array_for_merge,
        params=reduction_params,
    )
    metadata_groups = handler._groups
    return (filesdict, metadata_groups)
