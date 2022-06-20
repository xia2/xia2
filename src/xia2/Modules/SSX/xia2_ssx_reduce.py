from __future__ import annotations

import logging
from pathlib import Path

import iotbx.phil
from libtbx import Auto
from libtbx.introspection import number_of_processors

from xia2.Modules.SSX.data_reduction_definitions import ReductionParams
from xia2.Modules.SSX.data_reduction_interface import get_reducer
from xia2.Modules.SSX.util import report_timing

phil_str = """
input {
  directory = None
    .type = str
    .multiple = True
    .help = "Path to directory containing integrated_*.{refl,expt} files"
  reflections = None
    .type = str
    .multiple = True
    .help = "Path to an integrated reflections file"
  experiments = None
    .type = str
    .multiple = True
    .help = "Path to an integrated experiments file"
  processed_directory = None
    .type = str
    .multiple = True
    .help = "Path to previously reduced data"
}
multiprocessing.nproc = Auto
  .type = int
batch_size = 1000
  .type = int
  .help = "The minimum batch size for consistent reindexing of data with cosym"
d_min = None
  .type = float
"""

data_reduction_phil_str = """
clustering {
  threshold=None
    .type = float(value_min=0, allow_none=True)
    .help = "If no data has previously been reduced, then unit cell clustering"
            "is performed. This threshold is the value at which the dendrogram"
            "will be split in dials.cluster_unit_cell (the default value there"
            "is 5000). A higher threshold value means that unit cells with greater"
            "differences will be retained."
            "Only the largest cluster obtained from cutting at this threshold is"
            "used for data reduction. Setting the threshold to None/0 will"
            "skip this unit cell clustering and proceed to filtering based on"
            "the absolute angle/length tolerances."
  absolute_angle_tolerance = 1.0
    .type = float(value_min=0, allow_none=True)
    .help = "Filter the integrated data based on the median unit cell angles"
            "and this tolerance. If set to None/0, filtering will be skipped."
  absolute_length_tolerance = 1.0
    .type = float(value_min=0, allow_none=True)
    .help = "Filters the integrated data based on the median unit cell lengths"
            "and this tolerance. If set to None/0, filtering will be skipped."
  central_unit_cell = None
    .type = unit_cell
    .help = "Filter the integrated data based on the tolerances about these cell"
            "parameters, rather than the median cell."
}
symmetry {
  space_group = None
    .type = space_group
    .expert_level = 1
  phil = None
    .type = path
    .help = "Phil options file to use for symmetry analysis with dials.cosym. "
            "Parameters defined in the xia2.ssx phil scope will take precedent"
            "over identical options defined in the phil file."
    .expert_level = 3
}
scaling {
  anomalous = False
    .type = bool
    .help = "If True, keep anomalous pairs separate during scaling."
  model = None
    .type = path
    .help = "A model pdb file to use as a reference for scaling."
}
"""

full_phil_str = phil_str + data_reduction_phil_str

xia2_logger = logging.getLogger(__name__)


@report_timing
def run_xia2_ssx_reduce(
    root_working_directory: Path, params: iotbx.phil.scope_extract
) -> None:

    if params.multiprocessing.nproc is Auto:
        params.multiprocessing.nproc = number_of_processors(return_value_if_unknown=1)

    reduction_params = ReductionParams.from_phil(params)
    reducer_class = get_reducer(reduction_params)
    processed_directories = []
    if params.input.processed_directory:
        for d in params.input.processed_directory:
            processed_directories.append(Path(d).resolve())

    if params.input.directory:
        if params.input.reflections or params.input.experiments:
            xia2_logger.warning(
                "Only a directory or reflections+experiments can be given\n"
                "as input. Proceeding using only directories"
            )
        directories = [Path(i).resolve() for i in params.input.directory]
        reducer = reducer_class.from_directories(
            root_working_directory,
            directories,
            processed_directories,
            reduction_params,
        )
    elif params.input.reflections or params.input.experiments:
        if not (params.input.reflections and params.input.experiments):
            raise ValueError("Reflections and experiments files must both be specified")
        reflections = [Path(i).resolve() for i in params.input.reflections]
        experiments = [Path(i).resolve() for i in params.input.experiments]
        reducer = reducer_class.from_files(
            root_working_directory,
            reflections,
            experiments,
            processed_directories,
            reduction_params,
        )
    elif processed_directories:
        reducer = reducer_class.from_processed_only(
            root_working_directory, processed_directories, reduction_params
        )
    else:
        raise ValueError(reducer_class._no_input_error_msg)

    reducer.run()
