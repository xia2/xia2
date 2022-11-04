from __future__ import annotations

import functools
import json
import logging
import math
import os
import pathlib
import subprocess
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Tuple

import numpy as np

import libtbx.easy_mp
from dials.algorithms.clustering.unit_cell import Cluster
from dials.algorithms.indexing.ssx.analysis import generate_html_report
from dials.array_family import flex
from dials.util.image_grouping import ParsedYAML
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration_programs import (
    IndexingParams,
    IntegrationParams,
    RefinementParams,
    SpotfindingParams,
    best_cell_from_cluster,
    clusters_from_experiments,
    combine_with_reference,
    run_refinement,
    ssx_find_spots,
    ssx_index,
    ssx_integrate,
)
from xia2.Modules.SSX.reporting import condensed_unit_cell_info
from xia2.Modules.SSX.util import redirect_xia2_logger

xia2_logger = logging.getLogger(__name__)


@dataclass
class FileInput:
    images: List[str] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)
    directories: List[str] = field(default_factory=list)
    mask: Optional[pathlib.Path] = None
    reference_geometry: Optional[pathlib.Path] = None
    import_phil: Optional[pathlib.Path] = None


@dataclass
class AlgorithmParams:
    assess_images_to_use: Optional[Tuple[int, int]] = None
    refinement_images_to_use: Optional[Tuple[int, int]] = None
    assess_crystals_n_crystals: int = 250
    geometry_refinement_n_crystals: int = 250
    batch_size: int = 1000
    steps: List[str] = field(default_factory=list)
    nproc: int = 1
    njobs: int = 1
    multiprocessing_method: str = "multiprocessing"
    enable_live_reporting: bool = False
    parsed_grouping: Optional[ParsedYAML] = None


def process_batch(
    working_directory: pathlib.Path,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    integration_params: IntegrationParams,
    options: AlgorithmParams,
) -> dict:
    """Run find_spots, index and integrate in the working directory."""
    number = working_directory.name.split("_")[-1]
    xia2_logger.notice(banner(f"Processing batch {number}"))  # type: ignore
    data = {
        "n_images_indexed": None,
        "n_cryst_integrated": None,
        "directory": str(working_directory),
    }
    if options.enable_live_reporting:
        nuggets_dir = working_directory / "nuggets"
        if not nuggets_dir.is_dir():
            pathlib.Path.mkdir(nuggets_dir)
        indexing_params.output_nuggets_dir = nuggets_dir
        integration_params.output_nuggets_dir = nuggets_dir

    if "find_spots" in options.steps:
        strong = ssx_find_spots(working_directory, spotfinding_params)
        strong.as_file(working_directory / "strong.refl")

    summary: dict = {}
    integration_summary: dict = {}

    if "index" in options.steps:
        expt, refl, summary = ssx_index(working_directory, indexing_params)
        large_clusters = summary["large_clusters"]
        data["n_images_indexed"] = summary["n_images_indexed"]
        expt.as_file(working_directory / "indexed.expt")
        refl.as_file(working_directory / "indexed.refl")
        if large_clusters:
            xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
        if not (expt and refl):
            xia2_logger.warning(
                f"No images successfully indexed in {str(working_directory)}"
            )
            return data
    if "integrate" in options.steps:
        integration_summary = ssx_integrate(working_directory, integration_params)
        large_clusters = integration_summary["large_clusters"]
        if large_clusters:
            xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
        data["n_cryst_integrated"] = integration_summary["n_cryst_integrated"]
        data["DataFiles"] = integration_summary["DataFiles"]

    return data


def setup_main_process(
    main_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    batch_size: int,
) -> Tuple[List[pathlib.Path], dict]:
    """
    Slice data from the imported data according to the batch size,
    saving each into its own subdirectory for batch processing.
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


def inspect_existing_batch_directories(
    main_directory: pathlib.Path,
) -> Tuple[List[pathlib.Path], dict]:
    batch_directories: List[pathlib.Path] = []
    setup_data: dict = {"images_per_batch": {}}
    # use glob to find batch_*
    dirs_list = []
    numbers = []
    n_images = []
    for dir_ in list(main_directory.glob("batch_*")):
        name = dir_.name
        dirs_list.append(dir_)
        numbers.append(int(name.split("_")[-1]))
        if not (dir_ / "imported.expt").is_file():
            raise ValueError("Unable to find imported.expt in existing batch directory")
        n_images.append(
            len(load.experiment_list(dir_ / "imported.expt", check_format=False))
        )
    if not dirs_list:
        raise ValueError("Unable to find any batch_* directories")
    order = np.argsort(np.array(numbers))
    for idx in order:
        batch_directories.append(dirs_list[idx])
        setup_data["images_per_batch"][str(dirs_list[idx])] = n_images[idx]

    return batch_directories, setup_data


class NoMoreImages(Exception):
    pass


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
    if start >= len(expts):
        raise NoMoreImages
    if end > len(expts):
        end = len(expts)
    new_expts = expts[start:end]
    new_expts.as_file(destination_directory / "imported.expt")
    xia2_logger.info(
        f"Saved images {start+1} to {end} into {destination_directory / 'imported.expt'}"
    )
    output = {"input": os.fspath(imported_expts), "slice": images}
    outfile = destination_directory / "file_input.json"
    with (outfile).open(mode="w") as f:
        json.dump(output, f, indent=2)


def check_previous_import(
    working_directory: pathlib.Path, file_input: FileInput
) -> Tuple[bool, dict]:
    same_as_previous = False
    previous = {}
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
        same_phil = False
        if not file_input.import_phil:
            if previous["import_phil"] is None:
                same_phil = True
        else:
            if str(file_input.import_phil) == previous["import_phil"]:
                same_phil = True

        if same_reference and same_mask and same_phil:
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
                    return (True, previous)
    return (same_as_previous, previous)


def run_import(working_directory: pathlib.Path, file_input: FileInput) -> None:
    """
    Run dials.import with either images, templates or directories.
    After running dials.import, the options are saved to file_input.json

    If dials.import has previously been run in this directory, then try
    to load the previous file_input.json and see what options were used.
    If the options are the same as the current options, then don't rerun
    dials.import and just return.

    Returns True if dials.import was run, False if dials.import wasn't run due
    to options being identical to previous run.
    """

    if not working_directory.is_dir():
        pathlib.Path.mkdir(working_directory)

    xia2_logger.info("New images or geometry detected, running import")
    import_command = [
        "dials.import",
        "output.experiments=imported.expt",
        "convert_stills_to_sequences=True",
    ]
    if file_input.import_phil:
        import_command.insert(1, os.fspath(file_input.import_phil))
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
        result = subprocess.run(
            import_command, cwd=working_directory, capture_output=True, encoding="utf-8"
        )
        if result.returncode or result.stderr:
            raise ValueError(
                "dials.import returned error status:\n"
                + result.stderr
                + "\nHint: To import data from a .h5 file use e.g. image=/path/to/data/data_master.h5"
                + "\n      To import data from cbf files, use e.g. template=/path/to/data/name_#####.cbf"
                + "\n      The option directory=/path/to/data/ can also be used."
                + "\nPlease recheck the input path/file names for your data files."
            )
    outfile = working_directory / "file_input.json"
    outfile.touch()
    file_input_dict = asdict(file_input)
    if file_input.reference_geometry:
        file_input_dict["reference_geometry"] = str(file_input.reference_geometry)
    if file_input.mask:
        file_input_dict["mask"] = str(file_input.mask)
    if file_input.import_phil:
        file_input_dict["import_phil"] = str(file_input.import_phil)
    with (outfile).open(mode="w") as f:
        json.dump(file_input_dict, f, indent=2)


def assess_crystal_parameters_from_images(
    working_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    images_to_use: Tuple[int, int],
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
) -> None:
    """
    Run spotfinding and indexing and report on the properties of
    the largest cluster.

    Generates a unit cell clustering html report if any clusters are found.
    Always outputs a assess_crystals.json containing at least the success_per_image.
    """
    large_clusters: List[Cluster] = []
    cluster_plots: dict = {}
    success_per_image: List[bool] = []

    slice_images_from_experiments(imported_expts, working_directory, images_to_use)

    # now run find spots and index
    strong = ssx_find_spots(working_directory, spotfinding_params)
    strong.as_file(working_directory / "strong.refl")
    expts, __, summary = ssx_index(working_directory, indexing_params)
    success_per_image = summary["success_per_image"]

    if expts:
        cluster_plots, large_clusters = clusters_from_experiments(expts)
        if large_clusters:
            xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")

    if cluster_plots:
        generate_html_report(
            cluster_plots, working_directory / "dials.cell_clusters.html"
        )
    cluster_plots["success_per_image"] = success_per_image
    with open(working_directory / "assess_crystals.json", "w") as outfile:
        json.dump(cluster_plots, outfile, indent=2)

    _report_on_assess_crystals(expts, large_clusters)


def cumulative_assess_crystal_parameters(
    working_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    options: AlgorithmParams,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
):
    large_clusters: List[Cluster] = []
    cluster_plots: dict = {}
    success_per_image: List[bool] = []

    n_xtal = 0
    first_image = 0
    all_expts = ExperimentList()
    while n_xtal < options.assess_crystals_n_crystals:
        try:
            slice_images_from_experiments(
                imported_expts,
                working_directory,
                (first_image, first_image + options.batch_size),
            )
        except NoMoreImages:
            break
        strong = ssx_find_spots(working_directory, spotfinding_params)
        strong.as_file(working_directory / "strong.refl")
        expts, _, summary_this = ssx_index(working_directory, indexing_params)
        n_xtal += len(expts)
        xia2_logger.info(f"Indexed {n_xtal} crystals in total")
        all_expts.extend(expts)
        first_image += options.batch_size
        success_per_image.extend(summary_this["success_per_image"])

        if all_expts:
            # generate up-to-date cluster plots and lists
            cluster_plots, large_clusters = clusters_from_experiments(all_expts)
            if large_clusters:
                xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")

    if cluster_plots:
        generate_html_report(
            cluster_plots, working_directory / "dials.cell_clusters.html"
        )
    cluster_plots["success_per_image"] = success_per_image
    with open(working_directory / "assess_crystals.json", "w") as outfile:
        json.dump(cluster_plots, outfile, indent=2)

    _report_on_assess_crystals(all_expts, large_clusters)


def _report_on_assess_crystals(
    experiments: ExperimentList, large_clusters: List[Cluster]
) -> None:

    if experiments:
        if large_clusters:
            sg, uc = best_cell_from_cluster(large_clusters[0])
            xia2_logger.info(
                "Properties of largest cluster:\n"
                "Highest possible metric unit cell: "
                + ", ".join(f"{i:.3f}" for i in uc)
                + f"\nHighest possible metric symmetry: {sg}"
            )
        else:
            xia2_logger.info(
                "Some imaged indexed, but no significant unit cell clusters found.\n"
                + "Please try adjusting indexing parameters or try crystal assessment on different images"
            )
    else:
        xia2_logger.warning(
            "No successfully indexed images.\n"
            + "Please try adjusting indexing parameters or try crystal assessment on different images"
        )


def determine_reference_geometry_from_images(
    working_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    images_to_use: Tuple[int, int],
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    refinement_params: RefinementParams,
) -> None:
    """Run find spots, indexing and joint refinement in the working directory."""
    slice_images_from_experiments(imported_expts, working_directory, images_to_use)

    xia2_logger.notice(banner("Joint-refinement of experimental geometry"))  # type: ignore
    cluster_plots: dict = {}
    success_per_image: List[bool] = []

    strong = ssx_find_spots(working_directory, spotfinding_params)
    strong.as_file(working_directory / "strong.refl")
    expts, refl, summary = ssx_index(working_directory, indexing_params)
    success_per_image = summary["success_per_image"]

    if expts:
        cluster_plots, large_clusters = clusters_from_experiments(expts)
        if large_clusters:
            xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    if cluster_plots:
        generate_html_report(
            cluster_plots, working_directory / "dials.cell_clusters.html"
        )
    cluster_plots["success_per_image"] = success_per_image
    with open(working_directory / "geometry_refinement.json", "w") as outfile:
        json.dump(cluster_plots, outfile, indent=2)

    if not (expts and refl):
        raise ValueError(
            "No images successfully indexed, unable to run geometry refinement"
        )

    # now do geom refinement.
    expts.as_file(working_directory / "indexed.expt")
    refl.as_file(working_directory / "indexed.refl")

    run_refinement(working_directory, refinement_params)
    xia2_logger.info(
        f"Refined reference geometry saved to {working_directory}/refined.expt"
    )


def cumulative_determine_reference_geometry(
    working_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    options: AlgorithmParams,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    refinement_params: RefinementParams,
) -> None:
    xia2_logger.notice(banner("Joint-refinement of experimental geometry"))  # type: ignore
    cluster_plots: dict = {}
    success_per_image: List[bool] = []

    n_xtal = 0
    first_image = 0
    all_expts = ExperimentList()
    all_tables = []
    while n_xtal < options.geometry_refinement_n_crystals:
        try:
            slice_images_from_experiments(
                imported_expts,
                working_directory,
                (first_image, first_image + options.batch_size),
            )
        except NoMoreImages:
            break
        strong = ssx_find_spots(working_directory, spotfinding_params)
        strong.as_file(working_directory / "strong.refl")
        expts, refl, summary_this = ssx_index(working_directory, indexing_params)
        n_xtal += len(expts)
        xia2_logger.info(f"Indexed {n_xtal} crystals in total")
        if refl.size():
            all_expts.extend(expts)
            all_tables.append(refl)
        first_image += options.batch_size
        success_per_image.extend(summary_this["success_per_image"])

        if all_expts:
            cluster_plots, large_clusters = clusters_from_experiments(all_expts)
            if large_clusters:
                xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
    if cluster_plots:
        generate_html_report(
            cluster_plots, working_directory / "dials.cell_clusters.html"
        )
    cluster_plots["success_per_image"] = success_per_image
    with open(working_directory / "geometry_refinement.json", "w") as outfile:
        json.dump(cluster_plots, outfile, indent=2)

    if not all_expts:
        raise ValueError(
            "No images successfully indexed, unable to run geometry refinement"
        )

    # now do geom refinement.
    joint_table = flex.reflection_table.concat(all_tables)
    all_expts = combine_with_reference(all_expts)
    all_expts.as_file(working_directory / "indexed.expt")
    joint_table.as_file(working_directory / "indexed.refl")

    run_refinement(working_directory, refinement_params)
    xia2_logger.info(
        f"Refined reference geometry saved to {working_directory}/refined.expt"
    )


class ProcessBatch(object):

    """A processing class as required for multi_node_parallel_map"""

    def __init__(
        self,
        spotfinding_params: SpotfindingParams,
        indexing_params: IndexingParams,
        integration_params: IntegrationParams,
        options: AlgorithmParams,
    ):
        self.spotfinding_params = spotfinding_params
        self.indexing_params = indexing_params
        self.integration_params = integration_params
        self.options = options
        self.function = process_batch

    def __call__(self, directory: pathlib.Path) -> dict:
        with redirect_xia2_logger() as iostream:
            summary_data = self.function(
                directory,
                self.spotfinding_params,
                self.indexing_params,
                self.integration_params,
                self.options,
            )
            s = iostream.getvalue()
        xia2_logger.info(s)
        return summary_data


def process_batches(
    batch_directories: List[pathlib.Path],
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    integration_params: IntegrationParams,
    setup_data: dict,
    options: AlgorithmParams,
):
    class ProgressReport(object):
        def __init__(self):
            self.cumulative_images: int = 0
            self.cumulative_images_indexed: int = 0
            self.cumulative_crystals_integrated: int = 0

        def add(self, summary_data: dict) -> None:
            self.cumulative_images += setup_data["images_per_batch"][
                summary_data["directory"]
            ]
            xia2_logger.info(
                f"Cumulative number of images processed: {self.cumulative_images}"
            )
            if summary_data["n_images_indexed"] is not None:
                self.cumulative_images_indexed += summary_data["n_images_indexed"]
                pc_indexed = (
                    self.cumulative_images_indexed * 100 / self.cumulative_images
                )
                xia2_logger.info(f"Cumulative % of images indexed: {pc_indexed:.2f}%")
            if summary_data["n_cryst_integrated"] is not None:
                self.cumulative_crystals_integrated += summary_data[
                    "n_cryst_integrated"
                ]
                xia2_logger.info(
                    f"Total number of integrated crystals: {self.cumulative_crystals_integrated}"
                )

    progress = ProgressReport()

    def process_output(summary_data):
        progress.add(summary_data)
        if "DataFiles" in summary_data:
            for tag, file in zip(
                summary_data["DataFiles"]["tags"],
                summary_data["DataFiles"]["filenames"],
            ):
                FileHandler.record_more_data_file(tag, file)

    if options.njobs > 1:
        njobs = min(options.njobs, len(batch_directories))
        xia2_logger.info(
            f"Submitting processing in {len(batch_directories)} batches across {njobs} cores, each with nproc={options.nproc}."
        )
        libtbx.easy_mp.parallel_map(
            func=ProcessBatch(
                spotfinding_params, indexing_params, integration_params, options
            ),
            iterable=batch_directories,
            qsub_command=f"qsub -pe smp {options.nproc}",
            processes=njobs,
            method=options.multiprocessing_method,
            callback=process_output,
            preserve_order=False,
        )
    else:
        for batch_dir in batch_directories:
            summary_data = process_batch(
                batch_dir,
                spotfinding_params,
                indexing_params,
                integration_params,
                options,
            )
            process_output(summary_data)


def check_for_gaps_in_steps(steps: List[str]) -> bool:
    if "find_spots" not in steps:
        if "index" in steps or "integrate" in steps:
            return True
    else:
        if "index" not in steps:
            if "integrate" in steps:
                return True
    return False


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

    # First do a bit of input validation
    has_gaps = check_for_gaps_in_steps(options.steps)
    if not file_input.reference_geometry and has_gaps:
        raise ValueError(
            "Some processing steps are missing, and no reference geometry specified. Please adjust input."
        )
    # Note, it is allowed in general to not have to have index or find_spots, as
    # one may be rerunning in a stepwise manner.

    # Start by importing the data
    import_wd = root_working_directory / "import"
    same_as_previous, previous = check_previous_import(import_wd, file_input)
    if previous and not same_as_previous:
        xia2_logger.info(
            "Previous import options:\n"
            + "\n".join(f"  {k} : {v}" for k, v in previous.items())
        )
    if same_as_previous:
        xia2_logger.info("Import options identical to previous run")
    if not same_as_previous and has_gaps:
        raise ValueError(
            "Some processing steps, specified by workflow.steps, are missing and a new import was required "
            "due to first run or rerun with different options. Please adjust input."
        )

    import_was_run = False
    if not same_as_previous:
        # Run the first import, or reimport if options different
        run_import(import_wd, file_input)
        import_was_run = True

    imported_expts = import_wd / "imported.expt"
    if not imported_expts.is_file():
        raise ValueError(
            "Unable to successfully import images, please check input filepaths"
        )

    # If space group and unit cell not both given, then assess the crystals
    if not (indexing_params.space_group and indexing_params.unit_cell):
        assess_wd = root_working_directory / "assess_crystals"
        if options.assess_images_to_use:
            assess_crystal_parameters_from_images(
                assess_wd,
                imported_expts,
                options.assess_images_to_use,
                spotfinding_params,
                indexing_params,
            )
        else:
            cumulative_assess_crystal_parameters(
                assess_wd, imported_expts, options, spotfinding_params, indexing_params
            )

        xia2_logger.info(
            "Rerun with a space group and unit cell to continue processing"
        )
        return []

    # Do joint geometry refinement if a reference geometry was not specified.
    if not file_input.reference_geometry:
        geom_ref_wd = root_working_directory / "geometry_refinement"

        if options.refinement_images_to_use:
            determine_reference_geometry_from_images(
                geom_ref_wd,
                imported_expts,
                options.refinement_images_to_use,
                spotfinding_params,
                indexing_params,
                refinement_params,
            )
        else:
            cumulative_determine_reference_geometry(
                geom_ref_wd,
                imported_expts,
                options,
                spotfinding_params,
                indexing_params,
                refinement_params,
            )

        # Reimport with this reference geometry to prepare for the main processing
        file_input.reference_geometry = geom_ref_wd / "refined.expt"
        run_import(import_wd, file_input)
        import_was_run = True

    if not options.steps:
        return []

    # Now do the main processing using reference geometry
    if import_was_run and has_gaps:
        raise ValueError(
            "New data was imported, but there are gaps in the processing steps. Please adjust input."
        )
    try:
        batch_directories, setup_data = inspect_existing_batch_directories(
            root_working_directory
        )
    except ValueError:  # if existing batches weren't found
        batch_directories, setup_data = setup_main_process(
            root_working_directory,
            imported_expts,
            options.batch_size,
        )
    if not batch_directories:
        raise ValueError("Unable to determine directories for processing.")

    process_batches(
        batch_directories,
        spotfinding_params,
        indexing_params,
        integration_params,
        setup_data,
        options,
    )

    return batch_directories
