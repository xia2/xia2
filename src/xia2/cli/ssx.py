from __future__ import annotations

import functools
import json
import logging
import math
import os
import pathlib
import sys
from typing import List, Tuple

import procrunner

from cctbx.uctbx import unit_cell
from dials.util import log
from dials.util.options import ArgumentParser
from dxtbx.serialize import load
from iotbx import phil

from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration import (
    best_cell_from_cluster,
    ssx_find_spots,
    ssx_index,
    ssx_integrate,
)
from xia2.Modules.SSX.data_reduction import SimpleDataReduction

# sensible image input?
# multiple image=, directory= or template=


phil_str = """
images = None
  .type = str
  .multiple = True
  .help = "Path to image files"
reference_geometry = None
  .type = path
  .help = "Path to reference geomtry .expt file"
space_group = None
  .type = space_group
unit_cell = None
  .type = unit_cell
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
    .help = "Specify an inclusive image range to use freference geometry"
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

}
anomalous = False
  .type = bool
d_min = None
  .type = float
"""

phil_scope = phil.parse(phil_str)

logger = logging.getLogger("dials")


def process_batch(
    working_directory, space_group, unit_cell, integration_params, nproc=1
):
    strong = ssx_find_spots(working_directory)
    strong.as_file(working_directory / "strong.refl")
    expt, refl, _ = ssx_index(working_directory, nproc, space_group, unit_cell)
    expt.as_file(working_directory / "indexed.expt")
    refl.as_file(working_directory / "indexed.refl")
    ssx_integrate(working_directory, integration_params)


def run_refinement(working_directory):
    refine_command = [
        "dials.refine",
        "indexed.expt",
        "indexed.refl",
        "auto_reduction.action=fix",
        "beam.fix=all",
        "detector.fix_list=Tau1",
        "refinery.engine=SparseLevMar",
        "outlier.algorithm=sauter_poon",
    ]
    result = procrunner.run(refine_command, working_directory=working_directory)
    if result.returncode or result.stderr:
        raise ValueError("Refinement returned error status:\n" + str(result.stderr))


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
        if not pathlib.Path.is_dir(subdir):
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
    logger.info(
        f"xia2.ssx: Saved images {start+1} to {end} into {destination_directory / 'imported.expt'}"
    )


"""def run_import_with_reference(main_directory, file_input):

    # allow for fact that reference may have changed or file input may have changed.
    if not pathlib.Path.is_dir(main_directory / "import_with_reference"):
        pathlib.Path.mkdir(main_directory / "import_with_reference")

    logger.info("xia2.ssx: Importing images with determined reference experiments")
    import_command = ["dials.import"] + [i for i in file_input["images"]]
    import_command += [
        f"reference_geometry={main_directory / 'reference_geometry' / 'refined.expt'}",
        "use_gonio_reference=False",
    ]
    result = procrunner.run(
        import_command,
        working_directory=main_directory / "import_with_reference",
    )
    if result.returncode or result.stderr:
        raise ValueError("dials.import returned error status:\n" + str(result.stderr))
    outfile = main_directory / "import_with_reference" / "file_input.json"
    outfile.touch()
    with (outfile).open(mode="w") as f:
        json.dump(file_input, f, indent=2)"""


def determine_if_need_to_import_with_reference(main_directory, file_input):

    if not pathlib.Path.is_dir(main_directory / "import_with_reference"):
        pathlib.Path.mkdir(main_directory / "import_with_reference")
        run_import_with_reference(main_directory, file_input)
        return

    if not (main_directory / "import_with_reference" / "file_input.json").is_file():
        # some error must have occured in importing, so just rerun
        run_import_with_reference(main_directory, file_input)
        return

    with open(main_directory / "import_with_reference" / "file_input.json", "r") as f:
        previous = json.load(f)
        if previous["images"] == file_input["images"]:
            logger.info(
                f"xia2.ssx: Images already imported with reference in previous run of xia2.ssx:\n  {','.join(previous['images'])}"
            )
        else:
            logger.info(
                "xia2.ssx: New images detected, rerunning import with reference"
            )
            run_import_with_reference(main_directory, file_input)
        return


def run_import(
    working_directory: pathlib.Path,
    file_input: dict,
    reference_geometry: pathlib.Path = None,
) -> None:
    def import_and_save():
        import_command = ["dials.import"] + [i for i in file_input["images"]]
        if reference_geometry:
            import_command += [
                f"reference_geometry={os.fspath(reference_geometry)}",
                "use_gonio_reference=False",
            ]
            logger.notice(banner("Importing with reference geometry"))
        else:
            logger.notice(banner("Importing"))
        result = procrunner.run(
            import_command,
            working_directory=working_directory,
        )
        if result.returncode or result.stderr:
            raise ValueError(
                "dials.import returned error status:\n" + str(result.stderr)
            )

        outfile = working_directory / "file_input.json"
        outfile.touch()
        file_input["reference_geometry"] = None
        if reference_geometry:
            file_input["reference_geometry"] = str(reference_geometry)
        with (outfile).open(mode="w") as f:
            json.dump(file_input, f, indent=2)

    if not pathlib.Path.is_dir(working_directory):
        pathlib.Path.mkdir(working_directory)
        import_and_save()
        return

    if not (working_directory / "file_input.json").is_file():
        # some error must have occured in importing, so just rerun
        import_and_save()
        return

    with open(working_directory / "file_input.json", "r") as f:
        previous = json.load(f)
        if previous["images"] == file_input["images"]:
            if str(reference_geometry) == previous["reference_geometry"]:
                logger.info(
                    f"xia2.ssx: Images already imported in previous run of xia2.ssx:\n  {', '.join(previous['images'])}"
                )
                return
        logger.info("xia2.ssx: New images or geometry detected, rerunning import")
        import_and_save()
        return


def determine_reference_geometry(
    main_directory, reference_geometry, space_group_determination
) -> bool:

    # if a reference geometry is not specified, look in the reference_geometry
    # folder if it exists and see if there is a "refined.expt"

    def _do_run_and_save(working_directory, start_at_indexing=False):
        logger.info(
            "xia2.ssx: Determining reference geometry in reference_geometry folder"
        )
        if not start_at_indexing:
            images = reference_geometry["images_to_use"]
            if not images:
                images = (0, reference_geometry["n_images"])
            slice_images_from_initial_input(main_directory, working_directory, images)

            strong = ssx_find_spots(new_directory)
            strong.as_file(new_directory / "strong.refl")

        expt, refl, _ = ssx_index(
            new_directory,
            nproc=space_group_determination["nproc"],
            space_group=space_group_determination["space_group"],
            unit_cell=space_group_determination["unit_cell"],
        )
        expt.as_file(new_directory / "indexed.expt")
        refl.as_file(new_directory / "indexed.refl")

        run_refinement(working_directory)

        reference_geometry["space_group"] = str(
            space_group_determination["space_group"]
        )
        reference_geometry["unit_cell"] = str(space_group_determination["unit_cell"])
        outfile = working_directory / "reference_geometry.json"
        outfile.touch()
        with (outfile).open(mode="w") as f:
            json.dump(reference_geometry, f, indent=2)
        # history_tracking["reimport_with_current_reference"] = True

    new_directory = main_directory / "reference_geometry"
    if not pathlib.Path.is_dir(new_directory):
        # First time, so determine reference geometry.
        pathlib.Path.mkdir(new_directory)
    _do_run_and_save(new_directory)
    return True
    """
    if not (new_directory / "reference_geometry.json").is_file():
        # some error must have occured when trying previously, so just rerun
        _do_run_and_save(new_directory)
        return True

    # so have the right directory and record of previous run, check if we need to redo
    with open(new_directory / "reference_geometry.json", "r") as f:
        previous = json.load(f)

        # things that may have changed - n_images, images_to_use, space group, unit_cell

        if reference_geometry["n_images"] != previous["n_images"]:
            _do_run_and_save(new_directory)  # need to do full rerun
            return True
        if (
            reference_geometry["n_images"] == previous["n_images"]
        ) and (reference_geometry["images_to_use"] is not None):
            if reference_geometry["images_to_use"] != previous["images_to_use"]:
                _do_run_and_save(new_directory)  # need to do full rerun
                return True

        # is the space group and unit cell the same or different
        if space_group_determination["space_group"] != previous["space_group"]:
            _do_run_and_save(new_directory, start_at_indexing=True)  # need to rerun
            return True

        if not space_group_determination["unit_cell"].is_similar_to(
            unit_cell(previous["unit_cell"]),
            absolute_length_tolerance=0.2,
            absolute_angle_tolerance=0.5,
        ):
            _do_run_and_save(new_directory, start_at_indexing=True)  # need to rerun
            return True

        # everything appears to be the same as for previous run, so can use the refined.expt
        if not (new_directory / "refined.expt").is_file():
            _do_run_and_save(new_directory)  # something went wrong, need to rerun
            return True
        logger.info("xia2.ssx: Existing reference geometry found and will be used.")
        return False"""


def assess_crystal_parameters(
    main_directory: pathlib.Path, space_group_determination: dict
) -> None:

    # U.C. + S.G. has not been given, so need to work out what was different from before
    new_directory = main_directory / "assess_crystals"
    if not pathlib.Path.is_dir(new_directory):  # This is the first attempt
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
    )
    sg, uc = best_cell_from_cluster(largest_clusters[0])
    logger.info(
        "xia2.ssx: Highest possible metric unit cell: "
        + ", ".join(f"{i:.3f}" for i in uc)
    )
    logger.info(f"xia2.ssx: Highest possible metric symmetry: {sg}")


def run(args=sys.argv[1:]):

    parser = ArgumentParser(
        usage="xia2.ssx images=*cbf unit_cell=x space_group=y",
        read_experiments=False,
        read_reflections=False,
        phil=phil_scope,
        check_format=False,
        epilog="",
    )
    params, options = parser.parse_args(args=args, show_diff_phil=False)
    log.config(verbosity=options.verbose, logfile="xia2.ssx.log")
    diff_phil = parser.diff_phil.as_str()
    if diff_phil:
        logger.info("The following parameters have been modified:\n%s", diff_phil)

    cwd = pathlib.Path.cwd()

    file_input = {
        "images": [str(pathlib.Path(i).resolve()) for i in params.images],
    }

    space_group_determination = {
        "space_group": params.space_group,
        "unit_cell": params.unit_cell,
        # if these are not both given, then below parameters come into effect.
        "n_images": params.assess_crystals.n_images,
        "images_to_use": None,  # specify which image ranges from imported.expt to use
        "nproc": params.nproc,
    }
    if params.assess_crystals.images_to_use:
        if not ":" in params.assess_crystals.images_to_use:
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
    }

    history_tracking = {
        "reimport_with_current_reference": True,
    }

    main_process = {
        "batch_size": params.batch_size,
    }

    reference = None
    reimport_with_reference = True
    if params.reference_geometry:
        reference = pathlib.Path(params.reference_geometry).resolve()
        if not reference.is_file():
            logger.warn(
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
        logger.info("xia2.ssx: Space group and unit cell specified and will be used")
    else:
        assess_crystal_parameters(cwd, space_group_determination)
        logger.info(
            "xia2.ssx: Rerun with a space group and unit cell to continue processing"
        )
        exit(0)

    # 3 scenarios - reference given, reference previously determined, or
    # reference previously determined but some parameters have changed, such
    # that it should be done again.
    if reimport_with_reference:
        determine_reference_geometry(cwd, reference_geometry, space_group_determination)

        # if reimport_with_reference:
        run_import(
            cwd / "reimported_with_reference",
            file_input,
            cwd / "reference_geometry" / "refined.expt",
        )
        # else:  # also allow for fact that input files may have changed.
        #    determine_if_need_to_import_with_reference(cwd, file_input)
        # history_tracking["reimport_with_current_reference"] = False
        imported = cwd / "reimported_with_reference" / "imported.expt"

    else:
        imported = cwd / "initial_import" / "imported.expt"

    setup_main_process(cwd, main_process, imported)
    for i, batch_dir in enumerate(main_process["batch_directories"]):
        logger.notice(banner(f"Processing batch {i+i}"))
        process_batch(
            batch_dir,
            space_group_determination["space_group"],
            space_group_determination["unit_cell"],
            params.integration,
            nproc=params.nproc,
        )

    c = SimpleDataReduction(cwd, main_process["batch_directories"], 0)
    c.run(
        batch_size=main_process["batch_size"],
        nproc=params.nproc,
        anomalous=params.anomalous,
        space_group=str(params.space_group),
        cluster_threshold=params.clustering.threshold,
        d_min=params.d_min,
    )

    logger.info("xia2.ssx: Finished processing")
