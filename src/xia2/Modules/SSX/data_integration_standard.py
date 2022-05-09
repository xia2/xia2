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
    phil: Optional[pathlib.Path] = None


@dataclass
class AlgorithmParams:
    assess_images_to_use: Tuple[int, int] = (0, 1000)
    refinement_images_to_use: Tuple[int, int] = (0, 1000)
    batch_size: int = 1000
    stop_after_geometry_refinement: bool = False
    nproc: int = 1
    njobs: int = 1
    multiprocessing_method: str = "multiprocessing"


def process_batch(
    working_directory: pathlib.Path,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    integration_params: IntegrationParams,
) -> dict:
    """Run find_spots, index and integrate in the working directory."""
    strong = ssx_find_spots(working_directory, spotfinding_params)
    strong.as_file(working_directory / "strong.refl")
    expt, refl, summary = ssx_index(working_directory, indexing_params)
    large_clusters = summary["large_clusters"]
    expt.as_file(working_directory / "indexed.expt")
    refl.as_file(working_directory / "indexed.refl")
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    if not (expt and refl):
        xia2_logger.warning(
            f"No images successfully indexed in {str(working_directory)}"
        )
        return {"n_images_indexed": 0}
    integration_summary = ssx_integrate(working_directory, integration_params)
    large_clusters = integration_summary["large_clusters"]
    data = {
        "n_images_indexed": summary["n_images_indexed"],
        "n_cryst_integrated": integration_summary["n_cryst_integrated"],
        "directory": str(working_directory),
    }
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    return data


def setup_main_process(
    main_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    batch_size: int,
) -> Tuple[List[pathlib.Path], dict]:
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
    setup_data: dict = {"images_per_batch": {}}
    for i in range(len(splits) - 1):
        subdir = main_directory / template(index=i + 1)
        if not subdir.is_dir():
            pathlib.Path.mkdir(subdir)
            # now copy file and run
        sub_expt = expts[splits[i] : splits[i + 1]]
        sub_expt.as_file(subdir / "imported.expt")
        batch_directories.append(subdir)
        setup_data["images_per_batch"][str(subdir)] = splits[i + 1] - splits[i]
    return batch_directories, setup_data


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
        with (working_directory / "file_input.json").open(mode="r") as f:
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
    if file_input.phil:
        import_command.insert(1, os.fspath(file_input.phil))
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
    if file_input.phil:
        file_input_dict["phil"] = str(file_input.phil)
    with (outfile).open(mode="w") as f:
        json.dump(file_input_dict, f, indent=2)


def assess_crystal_parameters(
    working_directory: pathlib.Path,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
) -> None:
    """
    Run spotfinding and indexing and report on the properties of
    the largest cluster.
    """

    # now run find spots and index
    strong = ssx_find_spots(working_directory, spotfinding_params)
    strong.as_file(working_directory / "strong.refl")
    _, __, summary = ssx_index(working_directory, indexing_params)
    largest_clusters = summary["large_clusters"]
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

    expt, refl, summary = ssx_index(working_directory, indexing_params)
    large_clusters = summary["large_clusters"]
    expt.as_file(working_directory / "indexed.expt")
    refl.as_file(working_directory / "indexed.refl")
    if large_clusters:
        xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    if not (expt and refl):
        raise ValueError(
            "No images successfully indexed, unable to run geometry refinement"
        )
    run_refinement(working_directory, refinement_params)


class ProcessBatch(object):
    def __init__(self, spotfinding_params, indexing_params, integration_params):
        self.spotfinding_params = spotfinding_params
        self.indexing_params = indexing_params
        self.integration_params = integration_params
        self.function = process_batch

    def __call__(self, directory):
        summary_data = self.function(
            directory,
            self.spotfinding_params,
            self.indexing_params,
            self.integration_params,
        )
        return summary_data


def process_batches(input_):
    batch_directories = input_[0]
    spotfinding_params = input_[1]
    indexing_params = input_[2]
    integration_params = input_[3]
    setup_data = input_[4]
    options = input_[5]

    from dials.util.mp import multi_node_parallel_map

    class ProgressReport(object):
        def __init__(self):
            self.cumulative_images: int = 0
            self.cumulative_images_indexed: int = 0
            self.cumulative_crystals_integrated: int = 0

        def add(self, summary_data):
            self.cumulative_images += setup_data["images_per_batch"][
                summary_data["directory"]
            ]
            self.cumulative_images_indexed += summary_data["n_images_indexed"]
            self.cumulative_crystals_integrated += summary_data["n_cryst_integrated"]
            pc_indexed = self.cumulative_images_indexed * 100 / self.cumulative_images
            xia2_logger.info(
                f"Cumulative number of images processed: {self.cumulative_images}"
            )
            xia2_logger.info(f"Cumulative % of images indexed: {pc_indexed:.2f}%")
            xia2_logger.info(
                f"Total number of integrated crystals: {self.cumulative_crystals_integrated}"
            )

    progress = ProgressReport()

    def process_output(summary_data):
        progress.add(summary_data)

    if options.njobs > 1:
        multi_node_parallel_map(
            func=ProcessBatch(spotfinding_params, indexing_params, integration_params),
            iterable=batch_directories,
            nproc=options.nproc,
            njobs=options.njobs,
            cluster_method=options.multiprocessing_method,
            callback=process_output,
        )
    else:
        for i, batch_dir in enumerate(batch_directories):
            xia2_logger.notice(banner(f"Processing batch {i+1}"))  # type: ignore
            summary_data = process_batch(
                batch_dir, spotfinding_params, indexing_params, integration_params
            )
            progress.add(summary_data)


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
    if not imported_expts.is_file():
        raise ValueError(
            "Unable to successfully import images, please check input filepaths"
        )

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
    batch_directories, setup_data = setup_main_process(
        root_working_directory,
        imported_expts,
        options.batch_size,
    )

    input_ = (
        batch_directories,
        spotfinding_params,
        indexing_params,
        integration_params,
        setup_data,
        options,
    )
    process_batches(input_)

    return batch_directories
