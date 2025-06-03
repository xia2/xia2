from __future__ import annotations

import functools
import json
import logging
import math
import os
import pathlib
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any

import libtbx.easy_mp
import numpy as np
from dials.algorithms.clustering.unit_cell import Cluster
from dials.algorithms.indexing import DialsIndexError
from dials.algorithms.indexing.ssx.analysis import generate_html_report
from dials.array_family import flex
from dials.util.image_grouping import ParsedYAML
from dxtbx import flumpy
from dxtbx.model import ExperimentList
from dxtbx.serialize import load
from libtbx import phil

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.data_integration_programs import (
    IndexingParams,
    IntegrationParams,
    RefinementParams,
    SpotfindingParams,
    clusters_from_experiments,
    combine_with_reference,
    run_refinement,
    ssx_find_spots,
    ssx_index,
    ssx_integrate,
)
from xia2.Modules.SSX.reporting import (
    condensed_metric_unit_cell_info,
    condensed_unit_cell_info,
)
from xia2.Modules.SSX.util import redirect_xia2_logger

xia2_logger = logging.getLogger(__name__)


@dataclass
class FileInput:
    images: list[str] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)
    directories: list[str] = field(default_factory=list)
    mask: pathlib.Path | None = None
    reference_geometry: pathlib.Path | None = None
    starting_geometry: pathlib.Path | None = None
    import_phil: pathlib.Path | None = None

    def resolve_paths(self):
        for filetype in [self.images, self.templates]:
            for i, obj in enumerate(filetype):
                if len(obj.split(":")) > 2:
                    # Do it like this to avoid issues when calling pathlib on strings with ':' in
                    name = ":".join(obj.split(":")[:-2])
                    splits = ":".join(obj.split(":")[-2:])
                    filetype[i] = str(pathlib.Path(name).resolve()) + ":" + splits
                else:
                    filetype[i] = str(pathlib.Path(obj).resolve())


@dataclass
class AlgorithmParams:
    assess_images_to_use: tuple[int, int] | None = None
    refinement_images_to_use: tuple[int, int] | None = None
    assess_crystals_n_crystals: int = 250
    geometry_refinement_n_crystals: int = 250
    batch_size: int = 1000
    steps: list[str] = field(default_factory=list)
    nproc: int = 1
    njobs: int = 1
    multiprocessing_method: str = "multiprocessing"
    enable_live_reporting: bool = False
    parsed_grouping: ParsedYAML | None = None


def process_batch(
    working_directory: pathlib.Path,
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    integration_params: IntegrationParams,
    options: AlgorithmParams,
    progress_reporter=None,
) -> dict:
    """Run find_spots, index and integrate in the working directory."""
    number = working_directory.name.split("_")[-1]
    xia2_logger.notice(banner(f"Processing batch {number}"))  # type: ignore
    data: dict[str, Any] = {
        "n_images_indexed": None,
        "n_cryst_integrated": None,
        "directory": working_directory,
    }
    if options.enable_live_reporting:
        nuggets_dir = working_directory / "nuggets"
        if not nuggets_dir.is_dir():
            pathlib.Path.mkdir(nuggets_dir)
        indexing_params.output_nuggets_dir = nuggets_dir
        integration_params.output_nuggets_dir = nuggets_dir

    if "find_spots" in options.steps:
        strong = ssx_find_spots(working_directory, spotfinding_params)
        if not strong:  # No strong spots, rare but could happen (e.g. blank images)
            # Make sure correct metadata returned to allow reporting for the batch
            data["n_hits"] = 0
            data["n_images_indexed"] = 0
            if progress_reporter:
                progress_reporter.add_find_spots_result(data)
                if "index" in options.steps:
                    progress_reporter.add_index_result(data)
                if "integrate" in options.steps:
                    progress_reporter.add_integration_result(data)
            return data
        strong.as_file(working_directory / "strong.refl")
        n_hits = np.sum(
            np.bincount(flumpy.to_numpy(strong["id"])) >= indexing_params.min_spots
        )
        data["n_hits"] = n_hits
        if progress_reporter:
            progress_reporter.add_find_spots_result(data)

    summary: dict = {}
    integration_summary: dict = {}

    if "index" in options.steps:
        if not (
            working_directory / "strong.refl"
        ).is_file():  # Could happen if running in stepwise mode.
            expt, refl, large_clusters = (None, None, None)
            data["n_hits"] = 0
        else:
            expt, refl, summary = ssx_index(working_directory, indexing_params)
            large_clusters = summary["large_clusters"]
            data["n_images_indexed"] = summary["n_images_indexed"]
        if "n_hits" not in data:  # e.g. if just doing indexing step
            data["n_hits"] = summary["n_hits"]
        if refl and expt:  # Only save non-empty datastructures
            expt.as_file(working_directory / "indexed.expt")
            refl.as_file(working_directory / "indexed.refl")
        if large_clusters:
            xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
        if progress_reporter:
            progress_reporter.add_index_result(data)
        if not (expt and refl):
            xia2_logger.warning(
                f"No images successfully indexed in {str(working_directory)}"
            )
            if (
                "integrate" in options.steps
            ):  # make sure integration rate is reported correctly
                progress_reporter.add_integration_result(data)
            return data
    if "integrate" in options.steps:
        integration_summary = ssx_integrate(working_directory, integration_params)
        large_clusters = integration_summary["large_clusters"]
        if large_clusters:
            xia2_logger.info(f"{condensed_unit_cell_info(large_clusters)}")
        data["n_cryst_integrated"] = integration_summary["n_cryst_integrated"]
        data["DataFiles"] = integration_summary["DataFiles"]
        if progress_reporter:
            progress_reporter.add_integration_result(data)

    return data


def setup_main_process(
    main_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    batch_size: int,
) -> tuple[list[pathlib.Path], dict]:
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
    batch_directories: list[pathlib.Path] = []
    setup_data: dict = {"images_per_batch": {}}
    for i in range(len(splits) - 1):
        subdir = main_directory / template(index=i + 1)
        if not subdir.is_dir():
            pathlib.Path.mkdir(subdir)
            # now copy file and run
        sub_expt = expts[splits[i] : splits[i + 1]]
        sub_expt.as_file(subdir / "imported.expt")
        batch_directories.append(subdir)
        setup_data["images_per_batch"][subdir] = splits[i + 1] - splits[i]
    return batch_directories, setup_data


def inspect_existing_batch_directories(
    main_directory: pathlib.Path,
) -> tuple[list[pathlib.Path], dict]:
    batch_directories: list[pathlib.Path] = []
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
        setup_data["images_per_batch"][dirs_list[idx]] = n_images[idx]

    return batch_directories, setup_data


class NoMoreImages(Exception):
    pass


def slice_images_from_experiments(
    imported_expts: pathlib.Path,
    destination_directory: pathlib.Path,
    images: tuple[int, int],
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
        f"Saved images {start + 1} to {end} into {destination_directory / 'imported.expt'}"
    )
    output = {"input": os.fspath(imported_expts), "slice": images}
    outfile = destination_directory / "file_input.json"
    with (outfile).open(mode="w") as f:
        json.dump(output, f, indent=2)


def check_previous_import(
    working_directory: pathlib.Path, file_input: FileInput
) -> tuple[bool, dict]:
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


def _handle_slices(images_or_templates, path_type="image"):
    assert path_type == "image" or path_type == "template"
    # We want to allow image/template slicing e.g. image.h5:1:100, but only if there is a single image (
    # except for multiple images if all the slices are the same)
    starts = []
    ends = []
    import_command = []
    for obj in images_or_templates:
        # here we only care about ':' which are later than C:\
        drive, tail = os.path.splitdrive(obj)
        if ":" in tail:
            tokens = tail.split(":")
            if len(tokens) != 3:
                raise RuntimeError("/path/to/image.h5:start:end")
            dataset = drive + tokens[0]
            starts.append(int(tokens[1]))
            ends.append(int(tokens[2]))
            import_command.append(
                dataset if path_type == "image" else f"template={dataset}"
            )
        else:
            import_command.append(obj if path_type == "image" else f"template={obj}")
    if len(starts) and (len(starts) != len(images_or_templates)):
        raise ValueError(
            f"Can't import multiple {path_type}s with slices, unless the slices are the same"
        )
    if len(set(starts)) > 1 or len(set(ends)) > 1:
        raise ValueError(
            f"Can't import multiple {path_type}s with slices, unless the slices are the same"
        )
    if starts and ends:
        import_command.append(f"image_range={starts[0]},{ends[0]}")
    return import_command


def run_import(
    working_directory: pathlib.Path,
    file_input: FileInput,
    ignore_manual_detector_phil_options: bool = False,
) -> None:
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
    assert (cmd := shutil.which("dials.import"))
    import_command = [
        cmd,
        "output.experiments=imported.expt",
        "convert_stills_to_sequences=True",
    ]
    if file_input.import_phil:
        if ignore_manual_detector_phil_options:
            # remove any geometry options from the user phil, if we are now using the refined
            # reference geometry
            with open(file_input.import_phil) as f:
                params = phil.parse(input_string=f.read())
            non_detector_phil = ""
            for obj in params.objects:
                if obj.name == "geometry" and hasattr(obj.extract(), "detector"):
                    xia2_logger.info(
                        f"Removing manual detector geometry option from import phil: {obj.as_str()}"
                    )
                else:
                    non_detector_phil += obj.as_str()
            if non_detector_phil:
                fname = working_directory / "import_tmp.phil"
                with open(fname, "w") as f:
                    f.write(non_detector_phil)
                import_command.insert(1, os.fspath(fname))
        else:
            import_command.insert(1, os.fspath(file_input.import_phil))
    if file_input.images:
        import_command += _handle_slices(file_input.images, path_type="image")
    elif file_input.templates:
        import_command += _handle_slices(file_input.templates, path_type="template")
    elif file_input.directories:
        for d in file_input.directories:
            import_command.append(f"directory={d}")
    if file_input.mask:
        import_command.append(f"mask={os.fspath(file_input.mask)}")
    if file_input.reference_geometry or file_input.starting_geometry:
        if file_input.reference_geometry:
            cmd = f"reference_geometry={os.fspath(file_input.reference_geometry)}"
        elif file_input.starting_geometry:
            cmd = f"reference_geometry={os.fspath(file_input.starting_geometry)}"
        import_command += [cmd, "use_gonio_reference=False", "use_beam_reference=False"]
    if file_input.reference_geometry:
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
    if file_input.starting_geometry:
        file_input_dict["starting_geometry"] = str(file_input.starting_geometry)
    if file_input.mask:
        file_input_dict["mask"] = str(file_input.mask)
    if file_input.import_phil:
        file_input_dict["import_phil"] = str(file_input.import_phil)
    with (outfile).open(mode="w") as f:
        json.dump(file_input_dict, f, indent=2)


def assess_crystal_parameters_from_images(
    working_directory: pathlib.Path,
    imported_expts: pathlib.Path,
    images_to_use: tuple[int, int],
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
) -> None:
    """
    Run spotfinding and indexing and report on the properties of
    the largest cluster.

    Generates a unit cell clustering html report if any clusters are found.
    Always outputs a assess_crystals.json containing at least the success_per_image.
    """
    xia2_logger.notice(banner("Assess crystal parameters"))  # type: ignore
    large_clusters: list[Cluster] = []
    cluster_plots: dict = {}
    success_per_image: list[bool] = []

    slice_images_from_experiments(imported_expts, working_directory, images_to_use)

    progress_reporter = ProgressReport({"images_per_batch": {}})

    # now run find spots and index
    strong = ssx_find_spots(working_directory, spotfinding_params)
    if not strong:  # No strong spots, rare but could happen (e.g. blank images)
        xia2_logger.info("No spots found in selected image range.")
        return
    strong.as_file(working_directory / "strong.refl")

    data = {
        "n_hits": np.sum(
            np.bincount(flumpy.to_numpy(strong["id"])) >= indexing_params.min_spots
        )
    }
    # NB ideally count is formatted the same as batch numbering e.g 01 if >9 batches
    dir_placeholder = pathlib.Path("assess")
    data["directory"] = dir_placeholder
    progress_reporter.setup_data["images_per_batch"][dir_placeholder] = len(
        strong.experiment_identifiers()
    )
    progress_reporter.add_find_spots_result(data)
    try:
        expts, __, summary = ssx_index(working_directory, indexing_params)
    except DialsIndexError as e:
        data["n_images_indexed"] = 0
        xia2_logger.info(e)
        expts = ExperimentList([])
    else:
        success_per_image = summary["success_per_image"]
        data["n_images_indexed"] = summary["n_images_indexed"]

    progress_reporter.add_index_result(data)
    if expts:
        cluster_plots, large_clusters = clusters_from_experiments(
            expts, threshold="auto"
        )
        if large_clusters:
            cell_clustering = f"{condensed_unit_cell_info(large_clusters)}"
            progress_reporter.add_latest_clustering(cell_clustering)
        expts.as_file(working_directory / "indexed_all.expt")

    progress_reporter.summarise()
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
    xia2_logger.notice(banner("Assess crystal parameters"))  # type: ignore
    large_clusters: list[Cluster] = []
    cluster_plots: dict = {}
    success_per_image: list[bool] = []

    n_xtal = 0
    first_image = 0
    all_expts = ExperimentList()
    progress_reporter = ProgressReport({"images_per_batch": {}})
    count = 0

    while n_xtal < options.assess_crystals_n_crystals:
        count += 1
        try:
            slice_images_from_experiments(
                imported_expts,
                working_directory,
                (first_image, first_image + options.batch_size),
            )
        except NoMoreImages:
            break
        strong = ssx_find_spots(working_directory, spotfinding_params)
        # NB ideally count is formatted the same as batch numbering e.g 01 if >9 batches
        dir_placeholder = pathlib.Path(f"assess_batch_{count}")
        data: dict[str, Any] = {"directory": dir_placeholder}
        if not strong:  # No strong spots, rare but could happen (e.g. blank images)
            data["n_hits"] = 0
            progress_reporter.setup_data["images_per_batch"][dir_placeholder] = len(
                load.experiment_list(
                    working_directory / "imported.expt", check_format=False
                )
            )
            progress_reporter.add_find_spots_result(data)
            data["n_images_indexed"] = 0
            progress_reporter.add_index_result(data)
            progress_reporter.summarise()
            first_image += options.batch_size
            continue
        strong.as_file(working_directory / "strong.refl")
        data["n_hits"] = np.sum(
            np.bincount(flumpy.to_numpy(strong["id"])) >= indexing_params.min_spots
        )
        progress_reporter.setup_data["images_per_batch"][dir_placeholder] = len(
            strong.experiment_identifiers()
        )
        progress_reporter.add_find_spots_result(data)

        try:
            expts, _, summary_this = ssx_index(working_directory, indexing_params)
        except DialsIndexError as e:
            data["n_images_indexed"] = 0
            xia2_logger.info(e)
            expts = None
            success_per_image.extend([False] * options.batch_size)
        else:
            data["n_images_indexed"] = summary_this["n_images_indexed"]
            n_xtal += len(expts)
            success_per_image.extend(summary_this["success_per_image"])
            if expts:
                all_expts.extend(expts)
        progress_reporter.add_index_result(data)

        if all_expts:
            # generate up-to-date cluster plots and lists
            cluster_plots, large_clusters = clusters_from_experiments(
                all_expts, threshold="auto"
            )
            if large_clusters:
                cell_clustering = f"{condensed_unit_cell_info(large_clusters)}"
                progress_reporter.add_latest_clustering(cell_clustering)

        first_image += options.batch_size
        progress_reporter.summarise()

    if all_expts:
        all_expts.as_file(working_directory / "indexed_all.expt")

    if cluster_plots:
        generate_html_report(
            cluster_plots, working_directory / "dials.cell_clusters.html"
        )
    cluster_plots["success_per_image"] = success_per_image
    with open(working_directory / "assess_crystals.json", "w") as outfile:
        json.dump(cluster_plots, outfile, indent=2)

    _report_on_assess_crystals(all_expts, large_clusters)


def _report_on_assess_crystals(
    experiments: ExperimentList, large_clusters: list[Cluster]
) -> None:
    if experiments:
        if large_clusters:
            xia2_logger.info(condensed_metric_unit_cell_info(large_clusters))
        else:
            xia2_logger.info(
                "Some images indexed, but no significant unit cell clusters found.\n"
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
    images_to_use: tuple[int, int],
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    refinement_params: RefinementParams,
) -> None:
    """Run find spots, indexing and joint refinement in the working directory."""
    xia2_logger.notice(banner("Joint-refinement of experimental geometry"))  # type: ignore
    slice_images_from_experiments(imported_expts, working_directory, images_to_use)

    cluster_plots: dict = {}
    success_per_image: list[bool] = []
    progress_reporter = ProgressReport({"images_per_batch": {}})

    strong = ssx_find_spots(working_directory, spotfinding_params)
    if not strong:  # No strong spots, rare but could happen (e.g. blank images)
        xia2_logger.info("No spots found in selected image range.")
        raise ValueError(
            "No images successfully indexed, unable to run geometry refinement"
        )
    strong.as_file(working_directory / "strong.refl")
    data = {
        "n_hits": np.sum(
            np.bincount(flumpy.to_numpy(strong["id"])) >= indexing_params.min_spots
        )
    }
    # NB ideally count is formatted the same as batch numbering e.g 01 if >9 batches
    dir_placeholder = pathlib.Path("refinement")
    data["directory"] = dir_placeholder
    progress_reporter.setup_data["images_per_batch"][dir_placeholder] = len(
        strong.experiment_identifiers()
    )
    progress_reporter.add_find_spots_result(data)
    try:
        expts, refl, summary = ssx_index(working_directory, indexing_params)
    except DialsIndexError as e:
        data["n_images_indexed"] = 0
        xia2_logger.info(e)
        expts, refl = (None, None)
    else:
        success_per_image = summary["success_per_image"]
        data["n_images_indexed"] = summary["n_images_indexed"]

    progress_reporter.add_index_result(data)
    if expts:
        cluster_plots, large_clusters = clusters_from_experiments(expts)
        if large_clusters:
            cell_clustering = f"{condensed_unit_cell_info(large_clusters)}"
            progress_reporter.add_latest_clustering(cell_clustering)

    progress_reporter.summarise()
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
    assert (cmd := shutil.which("dxtbx.plot_detector_models"))
    command_line = [
        cmd,
        "imported.expt",
        "refined.expt",
        "pdf_file=detector_models.pdf",
    ]
    subprocess.run(
        command_line,
        cwd=working_directory,
        capture_output=False,
        encoding="utf-8",
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
    success_per_image: list[bool] = []

    n_xtal = 0
    first_image = 0
    all_expts = ExperimentList()
    all_tables = []
    progress_reporter = ProgressReport({"images_per_batch": {}})
    count = 0
    while n_xtal < options.geometry_refinement_n_crystals:
        count += 1
        try:
            slice_images_from_experiments(
                imported_expts,
                working_directory,
                (first_image, first_image + options.batch_size),
            )
        except NoMoreImages:
            break
        strong = ssx_find_spots(working_directory, spotfinding_params)
        # NB ideally count is formatted the same as batch numbering e.g 01 if >9 batches
        dir_placeholder = pathlib.Path(f"refinement_batch_{count}")
        data: dict[str, Any] = {"directory": dir_placeholder}
        if not strong:  # No strong spots, rare but could happen (e.g. blank images)
            data["n_hits"] = 0
            progress_reporter.setup_data["images_per_batch"][dir_placeholder] = len(
                load.experiment_list(
                    working_directory / "imported.expt", check_format=False
                )
            )
            progress_reporter.add_find_spots_result(data)
            data["n_images_indexed"] = 0
            progress_reporter.add_index_result(data)
            progress_reporter.summarise()
            first_image += options.batch_size
            continue
        strong.as_file(working_directory / "strong.refl")
        data["n_hits"] = np.sum(
            np.bincount(flumpy.to_numpy(strong["id"])) >= indexing_params.min_spots
        )
        data["directory"] = dir_placeholder
        progress_reporter.setup_data["images_per_batch"][dir_placeholder] = len(
            strong.experiment_identifiers()
        )
        progress_reporter.add_find_spots_result(data)

        try:
            expts, refl, summary_this = ssx_index(working_directory, indexing_params)
        except DialsIndexError as e:
            data["n_images_indexed"] = 0
            xia2_logger.info(e)
            success_per_image.extend([False] * options.batch_size)
        else:
            data["n_images_indexed"] = summary_this["n_images_indexed"]
            n_xtal += len(expts)
            success_per_image.extend(summary_this["success_per_image"])
            if refl.size():
                all_expts.extend(expts)
                all_tables.append(refl)
        progress_reporter.add_index_result(data)

        if all_expts:
            cluster_plots, large_clusters = clusters_from_experiments(all_expts)
            if large_clusters:
                cell_clustering = f"{condensed_unit_cell_info(large_clusters)}"
                progress_reporter.add_latest_clustering(cell_clustering)

        first_image += options.batch_size
        progress_reporter.summarise()

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
    assert (cmd := shutil.which("dxtbx.plot_detector_models"))
    command_line = [
        cmd,
        "imported.expt",
        "refined.expt",
        "pdf_file=detector_models.pdf",
    ]
    subprocess.run(
        command_line,
        cwd=working_directory,
        capture_output=False,
        encoding="utf-8",
    )


class ProcessBatch:
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


class ProgressReport:
    # class to store progress for reporting.
    # Either add and report after each step, or add all at the end (so can
    # distribute batch processing and not have mixed up reporting)
    # Then at the end of each batch report the cumulative processing stats.
    # Also allow reporting for stepwise processsing (e.g only find_spots, index or integrate)

    def __init__(self, setup_data):
        self.setup_data = setup_data
        self.cumulative_images_spotfinding: int = 0
        self.cumulative_images_indexing: int = 0
        self.cumulative_images_integration: int = 0
        self.cumulative_hits: int = 0
        self.cumulative_images_indexed: int = 0
        self.cumulative_crystals_integrated: int = 0
        self.cell_clustering: str = ""

    def add_find_spots_result(self, summary_data):
        n_images_this_batch = self.setup_data["images_per_batch"][
            summary_data["directory"]
        ]
        self.cumulative_images_spotfinding += n_images_this_batch
        self.cumulative_hits += summary_data["n_hits"]
        this_hit_rate = f"{100.0 * summary_data['n_hits'] / n_images_this_batch:.1f}"
        overall_hit_rate = (
            f"{100.0 * self.cumulative_hits / self.cumulative_images_spotfinding:.1f}"
        )
        name = summary_data["directory"].name.replace("_", " ")
        xia2_logger.info(
            f"{name} hit rate {this_hit_rate}%, overall hit rate {overall_hit_rate}%"
        )

    def add_index_result(self, summary_data):
        n_images_this_batch = self.setup_data["images_per_batch"][
            summary_data["directory"]
        ]
        self.cumulative_images_indexing += n_images_this_batch
        if summary_data["n_images_indexed"] is not None:
            self.cumulative_images_indexed += summary_data["n_images_indexed"]
        pc_indexed = f"{self.cumulative_images_indexed * 100 / self.cumulative_images_indexing:.1f}"
        if self.cumulative_images_spotfinding:
            pc_indexed_of_hits = (
                f"{self.cumulative_images_indexed * 100 / self.cumulative_hits:.1f}"
                if self.cumulative_hits
                else "-"
            )
        else:
            self.cumulative_hits += summary_data["n_hits"]
            pc_indexed_of_hits = (
                f"{self.cumulative_images_indexed * 100 / self.cumulative_hits:.1f}"
                if self.cumulative_hits
                else "-"
            )
        xia2_logger.info(
            f"{self.cumulative_images_indexed} indexed images overall ({pc_indexed_of_hits}% of hits, {pc_indexed}% of overall)"
        )

    def add_integration_result(self, summary_data):
        n_images_this_batch = self.setup_data["images_per_batch"][
            summary_data["directory"]
        ]
        self.cumulative_images_integration += n_images_this_batch
        if summary_data["n_cryst_integrated"] is not None:
            self.cumulative_crystals_integrated += summary_data["n_cryst_integrated"]
        pc_integrated = f"{100 * self.cumulative_crystals_integrated / self.cumulative_images_integration:.1f}%"
        xia2_logger.info(
            f"{self.cumulative_crystals_integrated} integrated crystals overall ({pc_integrated})"
        )

    def add_latest_clustering(self, condensed_cell_info):
        self.cell_clustering = condensed_cell_info

    def summarise(self):
        # We might just have done one processing step, so can't assume we have all the required quantities to report.
        n_images = max(
            [
                self.cumulative_images_spotfinding,
                self.cumulative_images_indexing,
                self.cumulative_images_integration,
            ]
        )
        msg = f"Progress summary:\n  {n_images} processed images"
        if self.cumulative_images_spotfinding or self.cumulative_images_indexing:
            if self.cumulative_images_spotfinding:
                overall_hit_rate = f"{100.0 * self.cumulative_hits / self.cumulative_images_spotfinding:.1f}"
            else:
                overall_hit_rate = f"{100.0 * self.cumulative_hits / self.cumulative_images_indexing:.1f}"
            msg += f", {self.cumulative_hits} hits ({overall_hit_rate}%)"
        if self.cumulative_images_indexing:
            pc_indexed = f"{self.cumulative_images_indexed * 100 / self.cumulative_images_indexing:.1f}"
            pc_indexed_of_hits = (
                f"{self.cumulative_images_indexed * 100 / self.cumulative_hits:.1f}"
                if self.cumulative_hits
                else "-"
            )
            msg += f"\n  {self.cumulative_images_indexed} indexed images ({pc_indexed_of_hits}% of hits, {pc_indexed}% of overall)"
        if self.cumulative_images_integration:
            pc_integrated = f"{100 * self.cumulative_crystals_integrated / self.cumulative_images_integration:.1f}%"
            msg += f"\n  {self.cumulative_crystals_integrated} integrated crystals ({pc_integrated})"
        if self.cell_clustering:
            msg += "\n" + "\n".join("  " + l for l in self.cell_clustering.split("\n"))
        xia2_logger.info(msg)

    def add_all(self, summary_data: dict) -> None:
        # Add complete summary data for a batch, in preparation for summarised report.
        self.cumulative_images_spotfinding += self.setup_data["images_per_batch"][
            summary_data["directory"]
        ]
        self.cumulative_images_indexing = self.cumulative_images_spotfinding
        self.cumulative_images_integration = self.cumulative_images_spotfinding
        if "n_hits" in summary_data:
            self.cumulative_hits += summary_data["n_hits"]
        if summary_data["n_images_indexed"] is not None:
            self.cumulative_images_indexed += summary_data["n_images_indexed"]
        if summary_data["n_cryst_integrated"] is not None:
            self.cumulative_crystals_integrated += summary_data["n_cryst_integrated"]


def process_batches(
    batch_directories: list[pathlib.Path],
    spotfinding_params: SpotfindingParams,
    indexing_params: IndexingParams,
    integration_params: IntegrationParams,
    setup_data: dict,
    options: AlgorithmParams,
):
    progress = ProgressReport(setup_data)

    def process_output(summary_data, add_all_to_progress=True):
        if add_all_to_progress:
            progress.add_all(summary_data)
        progress.summarise()
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
                progress,
            )
            process_output(summary_data, add_all_to_progress=False)


def check_for_gaps_in_steps(steps: list[str]) -> bool:
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
) -> list[pathlib.Path]:
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
        # at this point, we want the reference detector geometry to take
        # precedence over any initial manually specified options.
        run_import(import_wd, file_input, ignore_manual_detector_phil_options=True)
        import_was_run = True

    if not options.steps:
        return []

    # Now do the main processing using reference geometry
    if import_was_run and has_gaps:
        raise ValueError(
            "New data was imported, but there are gaps in the processing steps. Please adjust input."
        )
    if import_was_run:  # need to setup the batch folders again with new imported.expt
        batch_directories, setup_data = setup_main_process(
            root_working_directory,
            imported_expts,
            options.batch_size,
        )
    else:
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
