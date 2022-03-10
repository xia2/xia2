from __future__ import annotations

import functools
import json
import logging
import math
import os
import pathlib
import sys
import time
from typing import Tuple

import procrunner

from dials.util.options import ArgumentParser
from dxtbx.serialize import load
from iotbx import phil

import xia2.Handlers.Streams
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration import (
    best_cell_from_cluster,
    condensed_unit_cell_info,
    run_refinement,
    ssx_find_spots,
    ssx_index,
    ssx_integrate,
)
from xia2.Modules.SSX.data_reduction import SimpleDataReduction

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
  .help = "Processes the images in batches, with a subfolder for each batch"
assess_crystals {
  n_images = 1000
    .type = int
    .help = "Number of images to use for crystal assessment."
  images_to_use = None
    .type = str
    .help = "Specify an inclusive image range to use for crystal assessment,"
            "in the form start:end"
}
geometry_refinement {
  n_images = 1000
    .type = int
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
    working_directory,
    space_group,
    unit_cell,
    integration_params,
    nproc=1,
    max_lattices=1,
):
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


def setup_main_process(main_directory, main_process, imported):
    expts = load.experiment_list(imported, check_format=True)
    batch_size = main_process["batch_size"]
    n_batches = math.floor(len(expts) / batch_size)
    splits = [i * batch_size for i in range(max(1, n_batches))] + [len(expts)]
    # make sure last batch has at least the batch size
    template = functools.partial(
        "batch_{index:0{fmt:d}d}".format, fmt=len(str(n_batches))
    )
    batch_directories = []
    for i in range(len(splits) - 1):
        subdir = main_directory / template(index=i + 1)
        if not subdir.is_dir():
            pathlib.Path.mkdir(subdir)
            # now copy file and run
        sub_expt = expts[splits[i] : splits[i + 1]]
        sub_expt.as_file(subdir / "imported.expt")
        batch_directories.append(subdir)
    main_process["batch_directories"] = batch_directories


def slice_images_from_initial_input(
    main_directory: pathlib.Path,
    destination_directory: pathlib.Path,
    images: Tuple[int],
) -> None:
    expts = load.experiment_list(
        main_directory / "initial_import" / "imported.expt", check_format=False
    )
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
    file_input: dict,
    reference_geometry: pathlib.Path = None,
) -> None:

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
    import_command = ["dials.import"]
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
        xia2_logger.notice(banner("Importing with reference geometry"))
    else:
        xia2_logger.notice(banner("Importing"))
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


def determine_reference_geometry(
    main_directory: pathlib.Path,
    reference_geometry: dict,
    space_group_determination: dict,
) -> None:

    new_directory = main_directory / "geometry_refinement"
    if not new_directory.is_dir():
        # First time, so determine reference geometry.
        pathlib.Path.mkdir(new_directory)

    images = reference_geometry["images_to_use"]
    if not images:
        images = (0, reference_geometry["n_images"])
    slice_images_from_initial_input(main_directory, new_directory, images)

    strong = ssx_find_spots(new_directory)
    strong.as_file(new_directory / "strong.refl")

    expt, refl, large_clusters = ssx_index(
        new_directory,
        nproc=space_group_determination["nproc"],
        space_group=space_group_determination["space_group"],
        unit_cell=space_group_determination["unit_cell"],
        max_lattices=reference_geometry["max_lattices"],
    )
    expt.as_file(new_directory / "indexed.expt")
    refl.as_file(new_directory / "indexed.refl")
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    run_refinement(new_directory)


def assess_crystal_parameters(
    main_directory: pathlib.Path, space_group_determination: dict
) -> None:
    """
    Using the options in the space_group_determination dict, run
    spotfinding and indexing and report on the properties of
    the largest cluster.
    """
    new_directory = main_directory / "assess_crystals"
    if not new_directory.is_dir():  # This is the first attempt
        pathlib.Path.mkdir(new_directory)

    images = space_group_determination["images_to_use"]
    if not images:
        images = (0, space_group_determination["n_images"])
    slice_images_from_initial_input(main_directory, new_directory, images)

    # now run find spots and index
    strong = ssx_find_spots(new_directory)
    strong.as_file(new_directory / "strong.refl")
    _, __, largest_clusters = ssx_index(
        new_directory,
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


def _log_duration(start_time):
    duration = time.time() - start_time
    # write out the time taken in a human readable way
    xia2_logger.info(
        "Processing took %s", time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
    )


def run_xia2_ssx(root_working_directory, params):

    cwd = root_working_directory
    start_time = time.time()

    # First separate out some of the input params into relevant sections.
    file_input = {"images": [], "template": [], "directory": []}
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

    space_group_determination = {
        "space_group": params.space_group,
        "unit_cell": params.unit_cell,
        # if these are not both given, then below parameters come into effect.
        "n_images": params.assess_crystals.n_images,
        "images_to_use": None,  # specify which image ranges from imported.expt to use
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
        space_group_determination["images_to_use"] = (start, end)

    reference_geometry = {
        "n_images": params.geometry_refinement.n_images,
        "images_to_use": None,  # specify which image ranges from imported.expt to use e.g. [0:100,500:600]
        "max_lattices": params.max_lattices,
    }

    main_process = {
        "batch_size": params.batch_size,
    }

    reference = None
    reimport_with_reference = True  # a flag to say if we will need to determine
    # a reference geometry and reimport later

    # Determine if we can import with a valid reference geometry at the start
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
    run_import(cwd / "initial_import", file_input, reference)

    # If space group and unit cell not given, then assess the crystals
    if (
        space_group_determination["space_group"]
        and space_group_determination["unit_cell"]
    ):
        xia2_logger.info("Space group and unit cell specified and will be used")
    else:
        assess_crystal_parameters(cwd, space_group_determination)
        xia2_logger.info(
            "Rerun with a space group and unit cell to continue processing"
        )
        _log_duration(start_time)
        exit(0)

    # Do joint geometry refinement if applicable.
    if reimport_with_reference:
        determine_reference_geometry(cwd, reference_geometry, space_group_determination)
        if params.workflow.stop_after_geometry_refinement:
            _log_duration(start_time)
            exit(0)

        run_import(
            cwd / "reimported_with_reference",
            file_input,
            cwd / "geometry_refinement" / "refined.expt",
        )
        imported = cwd / "reimported_with_reference" / "imported.expt"
    else:
        imported = cwd / "initial_import" / "imported.expt"

    # Now do the main processing using reference geometry
    setup_main_process(cwd, main_process, imported)
    for i, batch_dir in enumerate(main_process["batch_directories"]):
        xia2_logger.notice(banner(f"Processing batch {i+1}"))
        process_batch(
            batch_dir,
            space_group_determination["space_group"],
            space_group_determination["unit_cell"],
            params.integration,
            nproc=params.nproc,
            max_lattices=params.max_lattices,
        )
    if params.workflow.stop_after_integration:
        _log_duration(start_time)
        exit(0)

    # Now do the data reduction
    c = SimpleDataReduction(cwd, main_process["batch_directories"], 0)
    c.run(
        batch_size=main_process["batch_size"],
        nproc=params.nproc,
        anomalous=params.anomalous,
        space_group=params.space_group,
        cluster_threshold=params.clustering.threshold,
        d_min=params.d_min,
    )

    _log_duration(start_time)


def run(args=sys.argv[1:]):

    parser = ArgumentParser(
        usage="xia2.ssx images=*cbf unit_cell=x space_group=y",
        read_experiments=False,
        read_reflections=False,
        phil=phil_scope,
        check_format=False,
        epilog="",
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
