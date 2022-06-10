from __future__ import annotations

import logging
import os
import pathlib

import iotbx.phil
from libtbx import Auto
from libtbx.introspection import number_of_processors

from xia2.Modules.SSX.data_integration_programs import (
    IndexingParams,
    IntegrationParams,
    RefinementParams,
    SpotfindingParams,
)
from xia2.Modules.SSX.data_integration_standard import (
    AlgorithmParams,
    FileInput,
    run_data_integration,
)
from xia2.Modules.SSX.data_reduction_base import ReductionParams
from xia2.Modules.SSX.data_reduction_simple import get_reducer
from xia2.Modules.SSX.util import report_timing
from xia2.Modules.SSX.xia2_ssx_reduce import data_reduction_phil_str

xia2_logger = logging.getLogger(__name__)

phil_str = """
image = None
  .type = str
  .multiple = True
  .help = "Path to image files"
  .expert_level=0
template = None
  .type = str
  .help = "The image sequence template"
  .multiple = True
  .expert_level=0
directory = None
  .type = str
  .help = "A directory with images"
  .multiple = True
  .expert_level=0
mask = None
  .type = str
  .help = "A mask to use for spotfinding and integration"
  .expert_level=1
reference_geometry = None
  .type = path
  .help = "Path to a reference geomtery (refined.expt) file"
  .expert_level=1
multiprocessing {
  nproc = Auto
    .type = int
    .expert_level=2
  njobs = 1
    .type = int
    .expert_level=3
    .help = "If >1, try to process in parallel across multiple computing nodes,"
            "using $nproc processes on each node. Up to $njobs nodes will be used,"
            "with the processing of each batch of images submitted as a job on this"
            "cluster."
            "WARNING: be considerate of fair use policies for the computing"
            "resources you will be using and whether it is necessary to use njobs>1."
}

space_group = None
  .type = space_group
  .help = "Space group to be used for indexing and integration."
  .expert_level = 0
d_min = None
  .type = float
  .help = "Resolution cutoff for spotfinding and integration."
  .expert_level=1
batch_size = 1000
  .type = int
  .help = "Index and integrate the images in batches with at least this number"
          "of images, with a subfolder for each batch. This is a means to manage"
          "the resource requirements and output reporting of the program, but"
          "does not change the resultant integrated data."
  .expert_level=2
dials_import.phil = None
  .type = path
  .help = "Phil file to use for dials.import. Parameters defined in the"
          "xia2.ssx phil scope will take precedent over identical options"
          "defined in the phil file."
  .expert_level=3
spotfinding {
  min_spot_size = 3
    .type = int
    .help = "The minimum spot size to allow in spotfinding."
    .expert_level=2
  max_spot_size = 20
    .type = int
    .help = "The maximum spot size to allow in spotfinding."
    .expert_level=2
  phil = None
    .type = path
    .help = "Phil options file to use for spotfinding. Parameters defined in"
            "the xia2.ssx phil scope will take precedent over identical options"
            "defined in the phil file."
    .expert_level=3
}
indexing {
  unit_cell = None
    .type = unit_cell
    .expert_level=0
  max_lattices = 1
    .type = int
    .help = "Maximum number of lattices to search for, per image"
    .expert_level=1
  phil = None
    .type = path
    .help = "Phil options file to use for indexing. Parameters defined in"
            "the xia2.ssx phil scope will take precedent over identical options"
            "defined in the phil file."
    .expert_level=3
}
integration {
  algorithm = stills *ellipsoid
    .type = choice
    .expert_level=2
  ellipsoid.rlp_mosaicity = *angular4 angular2 simple1 simple6
    .type = choice
    .expert_level=3
  phil = None
    .type = path
    .help = "Phil options file to use for integration. Parameters defined in"
            "the xia2.ssx phil scope will take precedent over identical options"
            "defined in the phil file."
    .expert_level=3
}
"""

workflow_phil = """
assess_crystals {
  n_images = 1000
    .type = int(value_min=1)
    .help = "Number of images to use for crystal assessment."
    .expert_level=2
  images_to_use = None
    .type = str
    .help = "Specify an inclusive image range to use for crystal assessment,"
            "in the form start:end"
    .expert_level=3
}
geometry_refinement {
  n_images = 1000
    .type = int(value_min=1)
    .help = "Number of images to use for reference geometry determination."
    .expert_level=2
  images_to_use = None
    .type = str
    .help = "Specify an inclusive image range to use for reference geometry"
            "determination, in the form start:end"
    .expert_level=3
  phil = None
    .type = path
    .help = "Phil options file to use for joint refinement with dials.refine."
            "Parameters defined in the xia2.ssx phil scope will take precedent"
            "over identical options defined in the phil file."
    .expert_level=3
}
workflow {
  steps = *find_spots *index *integrate *reduce
    .help = "Option to turn off particular steps. If None, then only geometry"
            "refinement will be done. Multiple choices should be of the format"
            "steps=find_spots+index".
    .type=choice(multi=True)
    .expert_level=3
}
enable_live_reporting = False
  .type = bool
  .help = "If True, additional output will be generated to allow in-process monitoring"
  .expert_level=3
"""

full_phil_str = phil_str + data_reduction_phil_str + workflow_phil
# full_phil_str = phil_str + workflow_phil


@report_timing
def run_xia2_ssx(
    root_working_directory: pathlib.Path, params: iotbx.phil.scope_extract
) -> None:
    """
    Run data integration for ssx images.
    """
    # First separate out some of the input params into relevant sections.
    # Although it would be nice to have these as lists of Paths, we will need
    # to compare to json data, add them as command line arguments etc, so simpler
    # to have as strings from the start.
    file_input = FileInput()
    if params.image:
        file_input.images = [str(pathlib.Path(i).resolve()) for i in params.image]
    elif params.template:
        file_input.templates = [str(pathlib.Path(i).resolve()) for i in params.template]
    elif params.directory:
        file_input.directories = [
            str(pathlib.Path(i).resolve()) for i in params.directory
        ]
    else:
        raise ValueError(
            "No input data identified (use image=, template= or directory=)"
        )
    if params.mask:
        file_input.mask = pathlib.Path(params.mask).resolve()
    if params.reference_geometry:
        reference = pathlib.Path(params.reference_geometry).resolve()
        if not reference.is_file():
            xia2_logger.warn(
                f"Unable to find reference geometry at {os.fspath(reference)}, proceeding without this reference"
            )
        else:
            file_input.reference_geometry = reference
    if params.dials_import.phil:
        file_input.import_phil = pathlib.Path(params.dials_import.phil).resolve()

    options = AlgorithmParams(
        batch_size=params.batch_size,
        njobs=params.multiprocessing.njobs,
        nproc=params.multiprocessing.nproc,
        steps=params.workflow.steps,
        enable_live_reporting=params.enable_live_reporting,
    )

    if params.assess_crystals.images_to_use:
        if ":" not in params.assess_crystals.images_to_use:
            raise ValueError("Images to use must be given in format start:end")
        vals = params.assess_crystals.images_to_use.split(":")
        if len(vals) != 2:
            raise ValueError("Images to use must be given in format start:end")
        start = min(0, int(vals[0]) - 1)  # convert from image number to slice
        end = int(vals[1])
        options.assess_images_to_use = (start, end)
    else:
        options.assess_images_to_use = (0, params.assess_crystals.n_images)

    if params.geometry_refinement.images_to_use:
        if ":" not in params.geometry_refinement.images_to_use:
            raise ValueError("Images to use must be given in format start:end")
        vals = params.geometry_refinement.images_to_use.split(":")
        if len(vals) != 2:
            raise ValueError("Images to use must be given in format start:end")
        start = min(0, int(vals[0]) - 1)  # convert from image number to slice
        end = int(vals[1])
        options.refinement_images_to_use = (start, end)
    else:
        options.refinement_images_to_use = (0, params.geometry_refinement.n_images)

    if params.multiprocessing.nproc is Auto:
        params.multiprocessing.nproc = number_of_processors(return_value_if_unknown=1)

    spotfinding_params = SpotfindingParams(
        params.spotfinding.min_spot_size,
        params.spotfinding.max_spot_size,
        params.d_min,
        params.multiprocessing.nproc,
        (
            pathlib.Path(params.spotfinding.phil).resolve()
            if params.spotfinding.phil
            else None
        ),
    )
    indexing_params = IndexingParams(
        params.space_group,
        params.indexing.unit_cell,
        params.indexing.max_lattices,
        params.multiprocessing.nproc,
        (
            pathlib.Path(params.indexing.phil).resolve()
            if params.indexing.phil
            else None
        ),
    )
    refinement_params = RefinementParams(
        (
            pathlib.Path(params.geometry_refinement.phil).resolve()
            if params.geometry_refinement.phil
            else None
        ),
    )
    integration_params = IntegrationParams(
        params.integration.algorithm,
        params.integration.ellipsoid.rlp_mosaicity,
        params.d_min,
        params.multiprocessing.nproc,
        (
            pathlib.Path(params.integration.phil).resolve()
            if params.integration.phil
            else None
        ),
    )

    integrated_batch_directories = run_data_integration(
        root_working_directory,
        file_input,
        options,
        spotfinding_params,
        indexing_params,
        refinement_params,
        integration_params,
    )
    if not integrated_batch_directories or not ("reduce" in params.workflow.steps):
        return

    # Now do the data reduction
    if not params.symmetry.space_group:
        params.symmetry.space_group = params.space_group
    reduction_params = ReductionParams.from_phil(params)
    reducer_class = get_reducer(reduction_params)
    reducer = reducer_class.from_directories(
        root_working_directory, integrated_batch_directories, [], reduction_params
    )
    reducer.run()
