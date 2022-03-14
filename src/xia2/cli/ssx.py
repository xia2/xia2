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

import functools
import json
import logging
import math
import os
import pathlib
import sys
import time
from typing import Dict, List, Tuple

import procrunner

from cctbx import sgtbx, uctbx
from dials.util.options import ArgumentParser
from dxtbx.serialize import load
from iotbx import phil

import xia2.Handlers.Streams
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration import (
    best_cell_from_cluster,
    run_refinement,
    ssx_find_spots,
    ssx_index,
    ssx_integrate,
)
from xia2.Modules.SSX.data_reduction_simple import SimpleDataReduction
from xia2.Modules.SSX.reporting import condensed_unit_cell_info

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


def process_batch(
    working_directory: pathlib.Path,
    space_group: sgtbx.space_group,
    unit_cell: uctbx.unit_cell,
    integration_params: phil.scope_extract,
    nproc: int = 1,
    max_lattices: int = 1,
) -> None:
    """Run find_spots, index and integrate in the working directory."""
    strong = ssx_find_spots(working_directory)
    strong.as_file(working_directory / "strong.refl")
    expt, refl, large_clusters = ssx_index(
        working_directory, nproc, space_group, unit_cell, max_lattices=max_lattices
    )
    expt.as_file(working_directory / "indexed.expt")
    refl.as_file(working_directory / "indexed.refl")
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    large_clusters = ssx_integrate(working_directory, integration_params)
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")


def setup_main_process(
    main_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    batch_size: int,
) -> List[pathlib.Path]:
    """
    Slice data from the imported data according to the bath size,
    saving each into it's own subdirectory for batch processing.
    """
    expts = load.experiment_list(imported_expts, check_format=True)
    n_batches = math.floor(len(expts) / batch_size)
    splits = [i * batch_size for i in range(max(1, n_batches))] + [len(expts)]
    # make sure last batch has at least the batch size
    template = functools.partial(
        "batch_{index:0{fmt:d}d}".format, fmt=len(str(n_batches))
    )
    batch_directories: List[pathlib.Path] = []
    for i in range(len(splits) - 1):
        subdir = main_directory / template(index=i + 1)
        if not subdir.is_dir():
            pathlib.Path.mkdir(subdir)
            # now copy file and run
        sub_expt = expts[splits[i] : splits[i + 1]]
        sub_expt.as_file(subdir / "imported.expt")
        batch_directories.append(subdir)
    return batch_directories


def slice_images_from_experiments(
    imported_expts: pathlib.Path,
    destination_directory: pathlib.Path,
    images: Tuple[int, int],
) -> None:
    """Saves a slice of the experiment list into the destination directory."""

    if not destination_directory.is_dir():  # This is the first attempt
        pathlib.Path.mkdir(destination_directory)

    expts = load.experiment_list(imported_expts, check_format=False)
    assert len(images) == 2  # Input is a tuple representing a slice
    start, end = images[0], images[1]
    if (end - start) > len(expts):
        end = len(expts)
    new_expts = expts[start:end]
    new_expts.as_file(destination_directory / "imported.expt")
    xia2_logger.info(
        f"Saved images {start+1} to {end} into {destination_directory / 'imported.expt'}"
    )


def run_import(
    working_directory: pathlib.Path,
    file_input: Dict,
    reference_geometry: pathlib.Path = None,
) -> None:
    """
    Run dials.import with either images, templates or directories.
    After running dials.import, the options are saved to file_input.json

    If dials.import has previously been run in this directory, then try
    to load the previous file_input.json and see what options were used.
    If the options are the same as the current options, then don't rerun
    dials.import and just return.
    """

    if not working_directory.is_dir():
        pathlib.Path.mkdir(working_directory)

    if (working_directory / "file_input.json").is_file():
        with open(working_directory / "file_input.json", "r") as f:
            previous = json.load(f)
            same_reference = False
            if not reference_geometry:
                if previous["reference_geometry"] is None:
                    same_reference = True
            else:
                if str(reference_geometry) == previous["reference_geometry"]:
                    same_reference = True
            if same_reference:
                for input_ in ["images", "template", "directory"]:
                    if file_input[input_] and (previous[input_] == file_input[input_]):
                        xia2_logger.info(
                            f"Images already imported in previous run of xia2.ssx:\n  {', '.join(previous[input_])}"
                        )
                        return

    xia2_logger.info("New images or geometry detected, running import")
    import_command = ["dials.import", "output.experiments=imported.expt"]
    if file_input["images"]:
        import_command += file_input["images"]
    elif file_input["template"]:
        for t in file_input["template"]:
            import_command.append(f"template={t}")
    elif file_input["directory"]:
        for d in file_input["directory"]:
            import_command.append(f"directory={d}")
    if reference_geometry:
        import_command += [
            f"reference_geometry={os.fspath(reference_geometry)}",
            "use_gonio_reference=False",
        ]
        xia2_logger.notice(banner("Importing with reference geometry"))  # type: ignore
    else:
        xia2_logger.notice(banner("Importing"))  # type: ignore
    result = procrunner.run(import_command, working_directory=working_directory)
    if result.returncode or result.stderr:
        raise ValueError("dials.import returned error status:\n" + str(result.stderr))
    outfile = working_directory / "file_input.json"
    outfile.touch()
    file_input["reference_geometry"] = None
    if reference_geometry:
        file_input["reference_geometry"] = str(reference_geometry)
    with (outfile).open(mode="w") as f:
        json.dump(file_input, f, indent=2)


def assess_crystal_parameters(
    working_directory: pathlib.Path, space_group_determination: Dict
) -> None:
    """
    Using the options in the space_group_determination dict, run
    spotfinding and indexing and report on the properties of
    the largest cluster.
    """

    # now run find spots and index
    strong = ssx_find_spots(working_directory)
    strong.as_file(working_directory / "strong.refl")
    _, __, largest_clusters = ssx_index(
        working_directory,
        nproc=space_group_determination["nproc"],
        space_group=space_group_determination["space_group"],
        unit_cell=space_group_determination["unit_cell"],
        max_lattices=space_group_determination["max_lattices"],
    )
    if largest_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(largest_clusters)}")

    sg, uc = best_cell_from_cluster(largest_clusters[0])
    xia2_logger.info(
        "Properties of largest cluster:\n"
        "Highest possible metric unit cell: "
        + ", ".join(f"{i:.3f}" for i in uc)
        + f"\nHighest possible metric symmetry: {sg}"
    )


def determine_reference_geometry(
    working_directory: pathlib.Path,
    reference_geometry: Dict,
    space_group_determination: Dict,
) -> None:
    """Run find spots, indexing and joint refinement in the working directory."""

    strong = ssx_find_spots(working_directory)
    strong.as_file(working_directory / "strong.refl")

    expt, refl, large_clusters = ssx_index(
        working_directory,
        nproc=space_group_determination["nproc"],
        space_group=space_group_determination["space_group"],
        unit_cell=space_group_determination["unit_cell"],
        max_lattices=reference_geometry["max_lattices"],
    )
    expt.as_file(working_directory / "indexed.expt")
    refl.as_file(working_directory / "indexed.refl")
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    run_refinement(working_directory)


def _log_duration(start_time: float) -> None:
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

    # First see if we have a referene geometry that we can use on first import.
    # Else, we'll need to determine a reference geometry and reimport later.
    # Start with the state of no reference geometry give.
    reference = None
    reimport_with_reference = True
    # See if a valid reference geometry has been given.
    if params.reference_geometry:
        reference = pathlib.Path(params.reference_geometry).resolve()
        if not reference.is_file():
            xia2_logger.warn(
                f"Unable to find reference geometry at {os.fspath(reference)}, proceeding without this reference"
            )
            reference = None
        else:
            reimport_with_reference = False

    # Start by importing the data
    initial_import_wd = root_working_directory / "initial_import"
    run_import(initial_import_wd, file_input, reference)
    imported_expts = initial_import_wd / "imported.expt"

    # If space group and unit cell not both given, then assess the crystals
    if not (crystal_assessment["space_group"] and crystal_assessment["unit_cell"]):
        assess_working_directory = root_working_directory / "assess_crystals"
        slice_images_from_experiments(
            imported_expts,
            assess_working_directory,
            crystal_assessment["images_to_use"],
        )
        assess_crystal_parameters(assess_working_directory, crystal_assessment)
        xia2_logger.info(
            "Rerun with a space group and unit cell to continue processing"
        )
        _log_duration(start_time)
        exit(0)

    # Do joint geometry refinement if a reference geometry was not specified.
    if reimport_with_reference:

        geometry_refinement = {
            "max_lattices": params.max_lattices,
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

        geom_ref_working_directory = root_working_directory / "geometry_refinement"
        slice_images_from_experiments(
            imported_expts,
            geom_ref_working_directory,
            geometry_refinement["images_to_use"],
        )
        determine_reference_geometry(
            geom_ref_working_directory,
            geometry_refinement,
            crystal_assessment,
        )
        if params.workflow.stop_after_geometry_refinement:
            _log_duration(start_time)
            exit(0)

        # Reimport with this reference geometry to prepare for the main processing
        reimport_wd = root_working_directory / "reimported_with_reference"
        run_import(
            reimport_wd,
            file_input,
            geom_ref_working_directory / "refined.expt",
        )
        imported_expts = reimport_wd / "imported.expt"

    # Now do the main processing using reference geometry
    batch_directories = setup_main_process(
        root_working_directory,
        imported_expts,
        params.batch_size,
    )
    for i, batch_dir in enumerate(batch_directories):
        xia2_logger.notice(banner(f"Processing batch {i+1}"))  # type: ignore
        process_batch(
            batch_dir,
            crystal_assessment["space_group"],
            crystal_assessment["unit_cell"],
            params.integration,
            nproc=params.nproc,
            max_lattices=params.max_lattices,
        )
    if params.workflow.stop_after_integration:
        _log_duration(start_time)
        exit(0)

    # Now do the data reduction
    c = SimpleDataReduction(root_working_directory, batch_directories, 0)
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

    xia2.Handlers.Streams.setup_logging(logfile="xia2.ssx.log")
    # remove the xia2 handler from the dials logger.
    dials_logger = logging.getLogger("dials")
    dials_logger.handlers.clear()

    diff_phil = parser.diff_phil.as_str()
    if diff_phil:
        xia2_logger.info("The following parameters have been modified:\n%s", diff_phil)

    cwd = pathlib.Path.cwd()
    run_xia2_ssx(cwd, params)
