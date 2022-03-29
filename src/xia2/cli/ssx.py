"""
xia2.ssx: A processing pipeline for data integration and reduction of synchrotron
serial crystallography images, using tools from the DIALS package.

To explore the unit cell/space group of your data, run with just the image data, e.g.:
    xia2.ssx template=images_####.cbf
Accurate data integration requires an accurate reference geometry determined from
a joint refinement in DIALS (a refined.expt file).
With a known unit cell & space group, to determine a reference geometry, run e.g.:
    xia2.ssx template=images_####.cbf unit_cell=x space_group=y stop_after_geometry_refinement=True
To run full processing with a reference geometry, run e.g.:
    xia2.ssx template=images_####.cbf unit_cell=x space_group=y reference_geometry=geometry_refinement/refined.expt

The full processing runs dials.import, dials.find_spots, dials.ssx_index,
dials.ssx_integrate, dials.cluster_unit_cell, dials.cosym, dials.reindex,
dials.scale and dials.merge! Data integration and data reduction can also be run
separately: use the option stop_after_integration=True in xia2.ssx, then run
xia2.ssx_reduce, providing the processing directories containing integrated files.
Refer to the individual DIALS program documentation or
https://dials.github.io/ssx_processing_guide.html for more details.
"""
from __future__ import annotations

import logging
import os
import pathlib
import sys
import time

import iotbx.phil
from dials.util.options import ArgumentParser

import xia2.Driver.timing
import xia2.Handlers.Streams
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
from xia2.Modules.SSX.data_reduction_simple import (
    SimpleDataReduction,
    SimpleReductionParams,
)

phil_str = """
image = None
  .type = str
  .multiple = True
  .help = "Path to image files"
template = None
  .type = str
  .help = "The image sequence template"
  .multiple = True
directory = None
  .type = str
  .help = "A directory with images"
  .multiple = True
mask = None
  .type = str
  .help = "A mask to use for spotfinding and integration"
reference_geometry = None
  .type = path
  .help = "Path to reference geomtry .expt file"
nproc = 1
  .type = int
space_group = None
  .type = space_group
d_min = None
  .type = float
  .help = "Resolution cutoff for spotfinding, integration and data reduction."
batch_size = 1000
  .type = int
  .help = "Index and integrate the images in batches with at least this number"
          "of images, with a subfolder for each batch. In data reduction, perform"
          "consistent reindexing of crystals in batches of at least this number"
          "of crystals."
spotfinding {
  min_spot_size = 3
    .type = int
    .help = "The minimum spot size to allow in spotfinding."
  max_spot_size = 20
    .type = int
    .help = "The maximum spot size to allow in spotfinding."
}
indexing {
  unit_cell = None
    .type = unit_cell
  max_lattices = 1
    .type = int
    .help = "Maximum number of lattices to search for, per image"
}
integration {
  algorithm = stills *ellipsoid
    .type = choice
  ellipsoid {
    rlp_mosaicity = *angular4 angular2 simple1 simple6
      .type = choice
  }
}
assess_crystals {
  n_images = 1000
    .type = int(value_min=1)
    .help = "Number of images to use for crystal assessment."
  images_to_use = None
    .type = str
    .help = "Specify an inclusive image range to use for crystal assessment,"
            "in the form start:end"
}
geometry_refinement {
  n_images = 1000
    .type = int(value_min=1)
    .help = "Number of images to use for reference geometry determination."
  images_to_use = None
    .type = str
    .help = "Specify an inclusive image range to use for reference geometry"
            "determination, in the form start:end"
  outlier.algorithm = null auto mcd tukey *sauter_poon
    .help = "Outlier rejection algorithm for joint refinement. If auto is"
            "selected, the algorithm is chosen automatically."
    .type = choice
}
workflow {
  stop_after_geometry_refinement = False
    .type = bool
  stop_after_integration = False
    .type = bool
}
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
  absolute_length_tolerance = 1.0
    .type = float(value_min=0, allow_none=True)
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

phil_scope = iotbx.phil.parse(phil_str)

xia2_logger = logging.getLogger(__name__)


def report_timing(fn):
    def wrap_fn(*args, **kwargs):
        start_time = time.time()
        result = fn(*args, **kwargs)
        xia2_logger.debug("\nTiming report:")
        xia2_logger.debug("\n".join(xia2.Driver.timing.report()))
        duration = time.time() - start_time
        # write out the time taken in a human readable way
        xia2_logger.info(
            "Processing took %s", time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
        )
        return result

    return wrap_fn


@report_timing
def run_xia2_ssx(
    root_working_directory: pathlib.Path, params: iotbx.phil.scope_extract
) -> None:
    """
    Run data integration and reduction for ssx images.
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
            "No input data identified (use images=, template= or directory=)"
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

    options = AlgorithmParams(
        batch_size=params.batch_size,
        stop_after_geometry_refinement=params.workflow.stop_after_geometry_refinement,
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

    spotfinding_params = SpotfindingParams(
        params.spotfinding.min_spot_size,
        params.spotfinding.max_spot_size,
        params.d_min,
        params.nproc,
    )
    indexing_params = IndexingParams(
        params.space_group,
        params.indexing.unit_cell,
        params.indexing.max_lattices,
        params.nproc,
    )
    refinement_params = RefinementParams(params.geometry_refinement.outlier.algorithm)
    integration_params = IntegrationParams(
        params.integration.algorithm,
        params.integration.ellipsoid.rlp_mosaicity,
        params.d_min,
        params.nproc,
    )

    processed_batch_directories = run_data_integration(
        root_working_directory,
        file_input,
        options,
        spotfinding_params,
        indexing_params,
        refinement_params,
        integration_params,
    )
    if not processed_batch_directories or params.workflow.stop_after_integration:
        return

    # Now do the data reduction
    reduction_params = SimpleReductionParams.from_phil(params)
    reducer = SimpleDataReduction(root_working_directory, processed_batch_directories)
    reducer.run(reduction_params)


def run(args=sys.argv[1:]):
    """
    Parse the command line input, setup logging and run the ssx processing script.
    """
    parser = ArgumentParser(
        usage="xia2.ssx template=images_####.cbf unit_cell=x space_group=y",
        read_experiments=False,
        read_reflections=False,
        phil=phil_scope,
        check_format=False,
        epilog=__doc__,
    )
    params, _ = parser.parse_args(args=args, show_diff_phil=False)

    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.ssx.log", debugfile="xia2.ssx.debug.log"
    )
    # remove the xia2 handler from the dials logger.
    dials_logger = logging.getLogger("dials")
    dials_logger.handlers.clear()

    diff_phil = parser.diff_phil.as_str()
    if diff_phil:
        xia2_logger.info("The following parameters have been modified:\n%s", diff_phil)

    cwd = pathlib.Path.cwd()
    run_xia2_ssx(cwd, params)
