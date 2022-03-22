from __future__ import annotations

import functools
import json
import logging
import math
import os
import pathlib
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Tuple

import procrunner

from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration_programs import (
    IndexingParams,
    IntegrationParams,
    RefinementParams,
    SpotfindingParams,
    best_cell_from_cluster,
    run_refinement,
    ssx_find_spots,
    ssx_index,
    ssx_integrate,
)
from xia2.Modules.SSX.reporting import condensed_unit_cell_info

xia2_logger = logging.getLogger(__name__)


@dataclass
class FileInput:
    images: List[str] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)
    directories: List[str] = field(default_factory=list)
    mask: Optional[pathlib.Path] = None
    reference_geometry: Optional[pathlib.Path] = None


@dataclass
class AlgorithmParams:
    assess_images_to_use: Tuple[int, int] = (0, 1000)
    refinement_images_to_use: Tuple[int, int] = (0, 1000)
    batch_size: int = 1000
    stop_after_geometry_refinement: bool = False


def process_batch(
    working_directory: pathlib.Path,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    integration_params: IntegrationParams,
) -> None:
    """Run find_spots, index and integrate in the working directory."""
    strong = ssx_find_spots(working_directory, spotfinding_params)
    strong.as_file(working_directory / "strong.refl")
    expt, refl, large_clusters = ssx_index(working_directory, indexing_params)
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


def run_import(working_directory: pathlib.Path, file_input: FileInput) -> None:
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
            if not file_input.reference_geometry:
                if previous["reference_geometry"] is None:
                    same_reference = True
            else:
                if str(file_input.reference_geometry) == previous["reference_geometry"]:
                    same_reference = True
            same_mask = False
            if not file_input.mask:
                if previous["mask"] is None:
                    same_mask = True
            else:
                if str(file_input.mask) == previous["mask"]:
                    same_mask = True
            if same_reference and same_mask:
                inputs = [
                    file_input.images,
                    file_input.templates,
                    file_input.directories,
                ]
                previous_inputs = [
                    previous["images"],
                    previous["templates"],
                    previous["directories"],
                ]
                for this, other in zip(inputs, previous_inputs):
                    if this and (this == other):
                        xia2_logger.info(
                            f"Images already imported in previous run of xia2.ssx:\n  {', '.join(other)}"
                        )
                        return

    xia2_logger.info("New images or geometry detected, running import")
    import_command = ["dials.import", "output.experiments=imported.expt"]
    if file_input.images:
        import_command += file_input.images
    elif file_input.templates:
        for t in file_input.templates:
            import_command.append(f"template={t}")
    elif file_input.directories:
        for d in file_input.directories:
            import_command.append(f"directory={d}")
    if file_input.mask:
        import_command.append(f"mask={os.fspath(file_input.mask)}")
    if file_input.reference_geometry:
        import_command += [
            f"reference_geometry={os.fspath(file_input.reference_geometry)}",
            "use_gonio_reference=False",
        ]
        xia2_logger.notice(banner("Importing with reference geometry"))  # type: ignore
    else:
        xia2_logger.notice(banner("Importing"))  # type: ignore
    with record_step("dials.import"):
        result = procrunner.run(import_command, working_directory=working_directory)
        if result.returncode or result.stderr:
            raise ValueError(
                "dials.import returned error status:\n" + str(result.stderr)
            )
    outfile = working_directory / "file_input.json"
    outfile.touch()
    file_input_dict = asdict(file_input)
    if file_input.reference_geometry:
        file_input_dict["reference_geometry"] = str(file_input.reference_geometry)
    if file_input.mask:
        file_input_dict["mask"] = str(file_input.mask)
    with (outfile).open(mode="w") as f:
        json.dump(file_input_dict, f, indent=2)


def assess_crystal_parameters(
    working_directory: pathlib.Path,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
) -> None:
    """
    Using the options in the space_group_determination dict, run
    spotfinding and indexing and report on the properties of
    the largest cluster.
    """

    # now run find spots and index
    strong = ssx_find_spots(working_directory, spotfinding_params)
    strong.as_file(working_directory / "strong.refl")
    _, __, largest_clusters = ssx_index(working_directory, indexing_params)
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
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    refinement_params: RefinementParams,
) -> None:
    """Run find spots, indexing and joint refinement in the working directory."""

    strong = ssx_find_spots(working_directory, spotfinding_params)
    strong.as_file(working_directory / "strong.refl")

    expt, refl, large_clusters = ssx_index(working_directory, indexing_params)
    expt.as_file(working_directory / "indexed.expt")
    refl.as_file(working_directory / "indexed.refl")
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    run_refinement(working_directory, refinement_params)


def run_data_integration(
    root_working_directory: pathlib.Path,
    file_input: FileInput,
    options: AlgorithmParams,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    refinement_params: RefinementParams,
    integration_params: IntegrationParams,
) -> List[pathlib.Path]:
    """
    The main data integration processing function.
    Import the data, followed by option crystal assessment (if the unit cell and
    space group were not given) and geometry refinement (if a reference geometry
    was not given). Then prepare and run data integration in batches with the
    given/determined reference geometry.
    """
    # Start by importing the data
    initial_import_wd = root_working_directory / "initial_import"
    run_import(initial_import_wd, file_input)
    imported_expts = initial_import_wd / "imported.expt"

    # If space group and unit cell not both given, then assess the crystals
    if not (indexing_params.space_group and indexing_params.unit_cell):
        assess_wd = root_working_directory / "assess_crystals"
        slice_images_from_experiments(
            imported_expts,
            assess_wd,
            options.assess_images_to_use,
        )
        assess_crystal_parameters(assess_wd, spotfinding_params, indexing_params)
        xia2_logger.info(
            "Rerun with a space group and unit cell to continue processing"
        )
        return []

    # Do joint geometry refinement if a reference geometry was not specified.
    if not file_input.reference_geometry:
        geom_ref_wd = root_working_directory / "geometry_refinement"
        slice_images_from_experiments(
            imported_expts,
            geom_ref_wd,
            options.refinement_images_to_use,
        )
        determine_reference_geometry(
            geom_ref_wd, spotfinding_params, indexing_params, refinement_params
        )
        if options.stop_after_geometry_refinement:
            return []

        # Reimport with this reference geometry to prepare for the main processing
        reimport_wd = root_working_directory / "reimported_with_reference"
        file_input.reference_geometry = geom_ref_wd / "refined.expt"
        run_import(reimport_wd, file_input)
        imported_expts = reimport_wd / "imported.expt"

    # Now do the main processing using reference geometry
    batch_directories = setup_main_process(
        root_working_directory,
        imported_expts,
        options.batch_size,
    )
    for i, batch_dir in enumerate(batch_directories):
        xia2_logger.notice(banner(f"Processing batch {i+1}"))  # type: ignore
        process_batch(
            batch_dir, spotfinding_params, indexing_params, integration_params
        )
    return batch_directories
