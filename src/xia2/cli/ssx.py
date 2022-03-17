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
from typing import Dict

from dials.util.options import ArgumentParser
from iotbx import phil

import xia2.Driver.timing
import xia2.Handlers.Streams
from xia2.Modules.SSX.data_integration_standard import DataIntegration
from xia2.Modules.SSX.data_reduction_simple import SimpleDataReduction

phil_str = """
images = None
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
reference_geometry = None
  .type = path
  .help = "Path to reference geomtry .expt file"
space_group = None
  .type = space_group
unit_cell = None
  .type = unit_cell
max_lattices = 1
  .type = int
  .help = "Maximum number of lattices to search for, per image"
nproc = 1
  .type = int
batch_size = 1000
  .type = int
  .help = "Index and integrate the images in batches with at least this number"
          "of images, with a subfolder for each batch. In data reduction, perform"
          "consistent reindexing of crystals in batches of at least this number"
          "of crystals."
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
}
integration {
  algorithm = stills *ellipsoid
    .type = choice
  ellipsoid {
    rlp_mosaicity = *angular4 angular2 simple1 simple6
      .type = choice
  }
}
clustering {
  threshold=1000
    .type = float
    .help = "Threshold to use for splitting clusters during data reduction"

}
anomalous = False
  .type = bool
  .help = "If True, keep anomalous pairs separate during scaling."
d_min = None
  .type = float
  .help = "Resolution cutoff for data reduction."
workflow {
  stop_after_geometry_refinement = False
    .type = bool
  stop_after_integration = False
    .type = bool
}
"""

phil_scope = phil.parse(phil_str)

xia2_logger = logging.getLogger(__name__)


def _log_duration(start_time: float) -> None:

    xia2_logger.debug("\nTiming report:")
    xia2_logger.debug("\n".join(xia2.Driver.timing.report()))

    duration = time.time() - start_time
    # write out the time taken in a human readable way
    xia2_logger.info(
        "Processing took %s", time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
    )


def run_xia2_ssx(
    root_working_directory: pathlib.Path, params: phil.scope_extract
) -> None:
    """
    The main processing script.
    Import the data, followed by option crystal assessment (if the unit cell and
    space group were not given) and geometry refinement (if a reference geometry
    was not given). Then prepare and run data integration in batches with the
    given/determined reference geometry. Finally, run data reduction.
    """
    start_time = time.time()

    # First separate out some of the input params into relevant sections.
    # Although it would be nice to have these as lists of Paths, we will need
    # to compare to json data, add them as command line arguments etc, so simpler
    # to have as strings from the start.
    file_input: Dict = {"images": [], "template": [], "directory": []}
    if params.images:
        file_input["images"] = [str(pathlib.Path(i).resolve()) for i in params.images]
    elif params.template:
        file_input["template"] = [
            str(pathlib.Path(i).resolve()) for i in params.template
        ]
    elif params.directory:
        file_input["directory"] = [
            str(pathlib.Path(i).resolve()) for i in params.directory
        ]
    else:
        raise ValueError(
            "No input data identified (use images=, template= or directory=)"
        )

    # Now separate out the options for crystal assessment
    crystal_assessment = {
        "space_group": params.space_group,
        "unit_cell": params.unit_cell,
        "nproc": params.nproc,
        "max_lattices": params.max_lattices,
    }
    if params.assess_crystals.images_to_use:
        if ":" not in params.assess_crystals.images_to_use:
            raise ValueError("Images to use must be given in format start:end")
        vals = params.assess_crystals.images_to_use.split(":")
        if len(vals) != 2:
            raise ValueError("Images to use must be given in format start:end")
        start = min(0, int(vals[0]) - 1)  # convert from image number to slice
        end = int(vals[1])
        crystal_assessment["images_to_use"] = (start, end)
    else:
        crystal_assessment["images_to_use"] = (0, params.assess_crystals.n_images)

    # First see if we have a reference geometry that we can use on first import.
    # Else, we'll need to determine a reference geometry and reimport later.
    # Start with the state of no reference geometry give.
    reference = None
    # See if a valid reference geometry has been given.
    if params.reference_geometry:
        reference = pathlib.Path(params.reference_geometry).resolve()
        if not reference.is_file():
            xia2_logger.warn(
                f"Unable to find reference geometry at {os.fspath(reference)}, proceeding without this reference"
            )
            reference = None
    geometry_refinement = {
        "max_lattices": params.max_lattices,
        "reference": reference,
    }
    if params.geometry_refinement.images_to_use:
        if ":" not in params.geometry_refinement.images_to_use:
            raise ValueError("Images to use must be given in format start:end")
        vals = params.geometry_refinement.images_to_use.split(":")
        if len(vals) != 2:
            raise ValueError("Images to use must be given in format start:end")
        start = min(0, int(vals[0]) - 1)  # convert from image number to slice
        end = int(vals[1])
        geometry_refinement["images_to_use"] = (start, end)
    else:
        geometry_refinement["images_to_use"] = (
            0,
            params.geometry_refinement.n_images,
        )

    integrator = DataIntegration(file_input, crystal_assessment, geometry_refinement)
    processed_batch_directories = integrator.run(
        root_working_directory,
        integration_params=params.integration,
        nproc=params.nproc,
        batch_size=params.batch_size,
        stop_after_geometry_refinement=params.workflow.stop_after_geometry_refinement,
    )
    if not processed_batch_directories or params.workflow.stop_after_integration:
        _log_duration(start_time)
        exit(0)

    # Now do the data reduction
    c = SimpleDataReduction(root_working_directory, processed_batch_directories, 0)
    c.run(
        batch_size=params.batch_size,
        nproc=params.nproc,
        anomalous=params.anomalous,
        space_group=params.space_group,
        cluster_threshold=params.clustering.threshold,
        d_min=params.d_min,
    )

    _log_duration(start_time)


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
