from __future__ import annotations

import functools
import json
import logging
import math
import pathlib
import sys

import procrunner

from cctbx.uctbx import unit_cell
from dials.util import log
from dials.util.options import ArgumentParser
from dxtbx.serialize import load
from iotbx import phil

from xia2.Modules.SSX.data_reduction import SimpleDataReduction

# sensible image input?
# multiple image=, directory= or template=


phil_str = """
images = None
  .type = str
  .multiple = True
  .help = "Path to image files"
space_group = None
  .type = space_group
unit_cell = None
  .type = unit_cell
nproc = 1
  .type = int
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
    logger.info(f"Performing spotfinding, indexing, integration in {working_directory}")
    run_spotfinding(working_directory)
    run_indexing(working_directory, nproc, space_group, unit_cell)
    run_integration(working_directory, integration_params)


def run_integration(working_directory, integration_params):
    integrate_command = [
        "dev.dials.ssx_integrate",
        "indexed.expt",
        "indexed.refl",
        f"algorithm={integration_params.algorithm}",
        "batch_size=100",
        "prediction.probability=0.95",
        "max_separation=1",
        "outlier_probability=0.95",
        "output.json=ssx_integrate.json",
    ]
    if integration_params.algorithm == "ellipsoid":
        integrate_command.extend(
            [f"rlp_mosaicity={integration_params.ellipsoid.rlp_mosaicity}"]
        )
    result = procrunner.run(integrate_command, working_directory=working_directory)
    if result.returncode or result.stderr:
        raise ValueError("Integration returned error status:\n" + str(result.stderr))


def run_spotfinding(working_directory):
    result = procrunner.run(
        ["dials.find_spots", "imported.expt"],
        working_directory=working_directory,
    )
    if result.returncode or result.stderr:
        raise ValueError("Find spots returned error status:\n" + str(result.stderr))


def run_indexing(working_directory, nproc=1, space_group=None, unit_cell=None):
    index_command = [
        "dev.dials.ssx_index",
        "imported.expt",
        "strong.refl",
        f"indexing.nproc={nproc}",
    ]
    if space_group:
        index_command.append(f"space_group={space_group}")
    if unit_cell:
        index_command.append(f"unit_cell={unit_cell}")
    result = procrunner.run(index_command, working_directory=working_directory)
    if result.returncode or result.stderr:
        raise ValueError("Indexing returned error status:\n" + str(result.stderr))


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


def setup_main_process(main_directory, main_process):
    expts = load.experiment_list(
        main_directory / "import_with_reference" / "imported.expt", check_format=True
    )
    batch_size = main_process["batch_size"]
    n_batches = math.floor(len(expts) / batch_size)
    splits = [i * batch_size for i in range(max(1, n_batches - 1))] + [len(expts)]
    # make sure last batch has at least the batch size
    template = functools.partial(
        "batch_{index:0{fmt:d}d}".format, fmt=len(str(n_batches))
    )
    batch_directories = []
    print(splits)
    for i in range(len(splits) - 1):
        subdir = main_directory / template(index=i + 1)
        if not pathlib.Path.is_dir(subdir):
            pathlib.Path.mkdir(subdir)
            # now copy file and run
        sub_expt = expts[splits[i] : splits[i + 1]]
        sub_expt.as_file(subdir / "imported.expt")
        batch_directories.append(subdir)
    main_process["batch_directories"] = batch_directories


def slice_images_from_initial_input(main_directory, images=[], subdirectory=""):
    expts = load.experiment_list(
        str(main_directory / "initial_import" / "imported.expt"), check_format=False
    )
    if len(images) == 1:
        # assert images[0] in form a:b
        start_and_end = tuple(int(i) for i in images[0].split(":"))

        if (start_and_end[1] - start_and_end[0]) > len(expts):
            start_and_end = (start_and_end[0], start_and_end[0] + len(expts))
        new_expts = expts[start_and_end[0] : start_and_end[1]]
        new_expts.as_file(main_directory / subdirectory / "imported.expt")
        logger.info(
            f"xia2.ssx: Saved images {start_and_end[0]} to {start_and_end[1]} into {subdirectory / 'imported.expt'}"
        )


def run_import_with_reference(main_directory, file_input):

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
        json.dump(file_input, f, indent=2)


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
                f"xia2.ssx: Images already imported with reference in previous run of xia2.ssx\n  {', '.join(previous['images'])}"
            )
        else:
            logger.info(
                "xia2.ssx: New images detected, rerunning import with reference"
            )
            run_import_with_reference(main_directory, file_input)
        return


def run_initial_import(main_directory, file_input):
    def _do_run_and_save():
        import_command = ["dials.import"] + [i for i in file_input["images"]]
        result = procrunner.run(
            import_command,
            working_directory=main_directory / "initial_import",
        )
        if result.returncode or result.stderr:
            raise ValueError(
                "dials.import returned error status:\n" + str(result.stderr)
            )
        outfile = main_directory / "initial_import" / "file_input.json"
        outfile.touch()
        with (outfile).open(mode="w") as f:
            json.dump(file_input, f, indent=2)

    if not pathlib.Path.is_dir(main_directory / "initial_import"):
        pathlib.Path.mkdir(main_directory / "initial_import")
        _do_run_and_save()
        return

    if not (main_directory / "initial_import" / "file_input.json").is_file():
        # some error must have occured in importing, so just rerun
        _do_run_and_save()
        return

    with open(main_directory / "initial_import" / "file_input.json", "r") as f:
        previous = json.load(f)
        if previous["images"] == file_input["images"]:
            logger.info(
                f"xia2.ssx: Images already imported in previous run of xia2.ssx:\n  {', '.join(previous['images'])}"
            )
        else:
            logger.info("xia2.ssx: New images detected, rerunning import")
            _do_run_and_save()
            return


def determine_reference_geometry(
    main_directory, reference_geometry, space_group_determination, history_tracking
):

    # if a reference geometry is not specified, look in the reference_geometry
    # folder if it exists and see if there is a "refined.expt"

    def _do_run_and_save(start_at_indexing=False):
        logger.info(
            "xia2.ssx: Determining reference geometry in reference_geometry folder"
        )
        if not start_at_indexing:
            images = reference_geometry["images_to_use"]
            if not images:
                images = [f"0:{reference_geometry['N_images_to_refine']}"]
            slice_images_from_initial_input(
                main_directory, images, pathlib.Path("reference_geometry")
            )

            run_spotfinding(new_directory)
        run_indexing(
            new_directory,
            nproc=space_group_determination["nproc"],
            space_group=space_group_determination["space_group"],
            unit_cell=space_group_determination["unit_cell"],
        )
        run_refinement(new_directory)

        reference_geometry["space_group"] = space_group_determination["space_group"]
        reference_geometry["unit_cell"] = space_group_determination["unit_cell"]
        outfile = new_directory / "reference_geometry.json"
        outfile.touch()
        with (outfile).open(mode="w") as f:
            json.dump(reference_geometry, f, indent=2)
        history_tracking["reimport_with_current_reference"] = True

    new_directory = main_directory / "reference_geometry"
    if not pathlib.Path.is_dir(new_directory):
        # First time, so determine reference geometry.
        pathlib.Path.mkdir(new_directory)
        _do_run_and_save()
        return

    if not (new_directory / "reference_geometry.json").is_file():
        # some error must have occured when trying previously, so just rerun
        _do_run_and_save()
        return

    # so have the right directory and record of previous run, check if we need to redo
    with open(new_directory / "reference_geometry.json", "r") as f:
        previous = json.load(f)
        if reference_geometry["N_images_to_refine"] != previous["N_images_to_refine"]:
            _do_run_and_save()  # need to do full rerun
            return
        if (
            reference_geometry["N_images_to_refine"] == previous["N_images_to_refine"]
        ) and (reference_geometry["images_to_use"] is not None):
            if reference_geometry["images_to_use"] != previous["images_to_use"]:
                _do_run_and_save()  # need to do full rerun
                return

        # is the space group and unit cell the same or different
        if space_group_determination["space_group"] != previous["space_group"]:
            _do_run_and_save(start_at_indexing=True)  # need to rerun
            return

        if not unit_cell(space_group_determination["unit_cell"]).is_similar_to(
            unit_cell(previous["unit_cell"]),
            absolute_length_tolerance=0.2,
            absolute_angle_tolerance=0.5,
        ):
            _do_run_and_save(start_at_indexing=True)  # need to rerun
            return
        # also check if unit cells are similar, absolute length tolerance 0.2,
        # absolute angle tolerance 0.5?

        # everything appears to be the same as for previous run, so can use the refined.expt
        if not (new_directory / "refined.expt").is_file():
            _do_run_and_save()  # something went wrong, need to rerun
            return
        logger.info("xia2.ssx: Existing reference geometry found and will be used.")
        history_tracking["reimport_with_current_reference"] = False


def assess_crystal_parameters(main_directory, space_group_determination):

    # U.C. + S.G. has not been given, so need to work out what was different from before
    new_directory = main_directory / "assess_crystals"
    if not pathlib.Path.is_dir(new_directory):  # This is the first attempt
        pathlib.Path.mkdir(new_directory)

        # select images, find spots, index, then pause or make smart choice
        images = space_group_determination["images_to_use"]
        if not images:
            images = [f"0:{space_group_determination['N_images_to_index']}"]
        slice_images_from_initial_input(
            main_directory, images, pathlib.Path("assess_crystals")
        )

        outfile = main_directory / "assess_crystals" / "crystal_assessment.json"
        outfile.touch()
        with (outfile).open(mode="w") as f:
            json.dump(space_group_determination, f, indent=2)

        # now run find spots and index
        run_spotfinding(new_directory)
        run_indexing(
            new_directory,
            nproc=space_group_determination["nproc"],
            space_group=space_group_determination["space_group"],
            unit_cell=space_group_determination["unit_cell"],
        )

    else:
        # Has previously been run, so see what settings were used.
        # code below assumes crystal_assessment.json, strong.refl and imported.expt exist #FIXME
        with open(
            main_directory / "assess_crystals" / "crystal_assessment.json", "r"
        ) as f:
            previous = json.load(f)
            # first of all, do we need to load more images, or can we just redo the indexing

            if (
                space_group_determination["N_images_to_index"]
                != previous["N_images_to_index"]
            ):
                # need to get the right images and redo spotfinding and indexing
                pass
            elif (
                space_group_determination["N_images_to_index"]
                == previous["N_images_to_index"]
            ) and (space_group_determination["images_to_use"] is not None):
                if (
                    space_group_determination["images_to_use"]
                    != previous["images_to_use"]
                ):
                    # need to get the right images and redo spotfinding and indexing
                    pass
            else:  # working on same images, reindex with new sg and uc options
                assert (main_directory / "assess_crystals" / "imported.expt").is_file()
                assert (main_directory / "assess_crystals" / "strong.refl").is_file()

                json_str = json.dumps(space_group_determination, indent=2)
                with open(
                    main_directory / "assess_crystals" / "crystal_assessment.json", "w"
                ) as f:
                    f.write(json_str)
                logger.info(
                    "xia2.ssx: Rerunning indexing for space group and unit cell assessment"
                )
                # do index
                run_indexing(
                    new_directory,
                    nproc=space_group_determination["nproc"],
                    space_group=space_group_determination["space_group"],
                    unit_cell=space_group_determination["unit_cell"],
                )


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
        "space_group": str(params.space_group),
        "unit_cell": ",".join(str(i) for i in params.unit_cell.parameters()),
        # if these are not both given, then below parameters come into effect.
        "N_images_to_index": 1000,
        "images_to_use": None,  # specify which image ranges from imported.expt to use e.g. [0:100,500:600]
        "nproc": params.nproc,
    }  # specify to stop

    reference_geometry = {
        "N_images_to_refine": 1000,
        "images_to_use": None,  # specify which image ranges from imported.expt to use e.g. [0:100,500:600]
    }

    history_tracking = {
        "reimport_with_current_reference": True,
    }

    main_process = {
        "batch_size": 1000,
    }

    run_initial_import(cwd, file_input)

    if (
        space_group_determination["space_group"]
        and space_group_determination["unit_cell"]
    ):
        logger.info("xia2.ssx: Space group and unit cell specified and will be used")
    else:
        assess_crystal_parameters(cwd, space_group_determination)
        logger.info(
            "xia2.ssx: Rerun with space group and unit cell to continue processing"
        )
        exit(0)

    determine_reference_geometry(
        cwd, reference_geometry, space_group_determination, history_tracking
    )

    if history_tracking["reimport_with_current_reference"]:
        run_import_with_reference(cwd, file_input)
    else:  # also allow for fact that input files may have changed.
        determine_if_need_to_import_with_reference(cwd, file_input)
    history_tracking["reimport_with_current_reference"] = False

    setup_main_process(cwd, main_process)
    for batch_dir in main_process["batch_directories"]:
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
