"""
xia2.countrate: Process crystallography data through import and spotfinding.

This program performs the following steps:
1. Runs dials.import to import image data
2. Runs dials.find_spots to find strong spots
3. Performs additional processing on the spotfinding results

Usage examples:
    xia2.countrate image=/path/to/data/data_master.h5
    xia2.countrate template=/path/to/data/image_####.cbf
    xia2.countrate directory=/path/to/data/
    xia2.countrate image=/path/to/data.h5 spotfinder.filter.min_spot_size=3
"""

from __future__ import annotations

import logging
import pathlib
import subprocess
import sys
import traceback

import iotbx.phil
from dials.array_family import flex
from dials.util.options import ArgumentParser
from dxtbx.serialize import load

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations
from xia2.Handlers.Citations import Citations

logger = logging.getLogger("xia2.cli.countrate")

phil_scope = iotbx.phil.parse(
    """
input {
    image = None
        .type = str
        .help = "Path to image file (e.g., data_master.h5)"
    template = None
        .type = str
        .help = "Image template (e.g., image_####.cbf)"
    directory = None
        .type = str
        .help = "Directory containing image files"
}

spotfinder {
    min_spot_size = 2
        .type = int
        .help = "Minimum spot size in pixels"
    max_spot_size = 10
        .type = int
        .help = "Maximum spot size in pixels"
    d_min = None
        .type = float
        .help = "Minimum d-spacing to consider for spotfinding (Angstroms)"
    d_max = None
        .type = float
        .help = "Maximum d-spacing to consider for spotfinding (Angstroms)"
    nproc = 1
        .type = int
        .help = "Number of processors for spotfinding"
}

processing {
    min_spots_per_image = 0
        .type = int
        .help = "Minimum number of spots required per image"
    output_html_report = False
        .type = bool
        .help = "Generate HTML report of spotfinding results"
}

output {
    experiments = "imported.expt"
        .type = str
        .help = "Output experiments file from dials.import"
    reflections = "strong.refl"
        .type = str
        .help = "Output reflections file from dials.find_spots"
    log = "xia2.countrate.log"
        .type = str
        .help = "Log file for processing"
}
"""
)


def run_dials_import(working_dir: pathlib.Path, params) -> None:
    """Run dials.import on the input data."""
    logger.info("Running dials.import...")

    import_cmd = [
        "dials.import",
        f"output.experiments={params.output.experiments}",
    ]

    # Add input data source
    # Images are passed as positional arguments, templates use template=, directories use directory=
    if params.input.image:
        import_cmd.append(params.input.image)
    elif params.input.template:
        import_cmd.append(f"template={params.input.template}")
    elif params.input.directory:
        import_cmd.append(f"directory={params.input.directory}")
    else:
        raise ValueError("Must provide one of: image, template, or directory")

    logger.debug(f"Running: {' '.join(import_cmd)}")

    result = subprocess.run(
        import_cmd, cwd=working_dir, capture_output=True, encoding="utf-8"
    )

    if result.returncode != 0:
        logger.error("dials.import failed:")
        logger.error(result.stderr)
        raise RuntimeError(f"dials.import failed with return code {result.returncode}")

    logger.info("dials.import completed successfully")


def run_dials_find_spots(working_dir: pathlib.Path, params) -> None:
    """Run dials.find_spots on the imported data."""
    logger.info("Running dials.find_spots...")

    experiments_file = working_dir / params.output.experiments
    if not experiments_file.exists():
        raise FileNotFoundError(f"Experiments file not found: {experiments_file}")

    find_spots_cmd = [
        "dials.find_spots",
        str(experiments_file),
        f"output.reflections={params.output.reflections}",
        f"spotfinder.filter.min_spot_size={params.spotfinder.min_spot_size}",
        f"spotfinder.filter.max_spot_size={params.spotfinder.max_spot_size}",
        f"spotfinder.mp.nproc={params.spotfinder.nproc}",
    ]

    if params.spotfinder.d_min is not None:
        find_spots_cmd.append(f"spotfinder.filter.d_min={params.spotfinder.d_min}")

    if params.spotfinder.d_max is not None:
        find_spots_cmd.append(f"spotfinder.filter.d_max={params.spotfinder.d_max}")

    logger.debug(f"Running: {' '.join(find_spots_cmd)}")

    result = subprocess.run(
        find_spots_cmd, cwd=working_dir, capture_output=True, encoding="utf-8"
    )

    if result.returncode != 0:
        logger.error("dials.find_spots failed:")
        logger.error(result.stderr)
        raise RuntimeError(
            f"dials.find_spots failed with return code {result.returncode}"
        )

    logger.info("dials.find_spots completed successfully")


def process_spotfinding_results(working_dir: pathlib.Path, params) -> dict:
    """Process the spotfinding results and perform additional analysis."""
    logger.info("Processing spotfinding results...")

    # Load the reflections and experiments
    reflections_path = working_dir / params.output.reflections
    experiments_path = working_dir / params.output.experiments

    if not reflections_path.exists():
        raise FileNotFoundError(f"Reflections file not found: {reflections_path}")

    reflections = flex.reflection_table.from_file(str(reflections_path))
    experiments = load.experiment_list(str(experiments_path), check_format=False)

    # Basic statistics
    n_experiments = len(experiments)
    n_reflections = len(reflections)

    logger.info(f"Found {n_experiments} experiments")
    logger.info(f"Found {n_reflections} total reflections")

    # Per-image spot counts
    spot_counts = {}
    if n_reflections > 0 and "id" in reflections:
        for expt_id in range(n_experiments):
            n_spots = (reflections["id"] == expt_id).count(True)
            spot_counts[expt_id] = n_spots
            logger.info(f"  Experiment {expt_id}: {n_spots} spots")

    # Filter based on minimum spots per image
    if params.processing.min_spots_per_image > 0:
        selected = flex.bool(n_reflections, True)
        for i in range(n_reflections):
            if "id" in reflections:
                expt_id = reflections["id"][i]
                if spot_counts.get(expt_id, 0) < params.processing.min_spots_per_image:
                    selected[i] = False

        n_filtered = selected.count(True)
        logger.info(
            f"After filtering: {n_filtered} reflections "
            f"(removed {n_reflections - n_filtered})"
        )

        # Save filtered reflections if any were removed
        if n_filtered < n_reflections:
            filtered_reflections = reflections.select(selected)
            filtered_path = working_dir / "strong_filtered.refl"
            filtered_reflections.as_file(str(filtered_path))
            logger.info(f"Saved filtered reflections to {filtered_path}")

    # Generate summary statistics
    summary = {
        "n_experiments": n_experiments,
        "n_reflections": n_reflections,
        "spot_counts": spot_counts,
        "reflections_per_experiment": (
            n_reflections / n_experiments if n_experiments > 0 else 0
        ),
    }

    return summary


def run(args=None):
    """Main entry point for the CLI program."""
    if args is None:
        args = sys.argv[1:]

    try:
        Citations.cite("dials-general")

        # Parse command line arguments
        parser = ArgumentParser(
            usage="xia2.countrate [options] [param.phil]",
            phil=phil_scope,
            read_reflections=False,
            read_experiments=False,
            check_format=False,
            epilog=__doc__,
        )

        params, options = parser.parse_args(args=args, show_diff_phil=False)

        # Setup logging
        xia2.Handlers.Streams.setup_logging(
            logfile=params.output.log,
            verbose=options.verbose,
            debugfile="xia2.countrate.debug.log",
        )

        # Get current working directory
        working_dir = pathlib.Path.cwd()

        # Show parsed parameters
        diff_phil = parser.diff_phil.as_str()
        if diff_phil:
            logger.info("Parameters:\n%s", diff_phil)

        # Run the processing pipeline
        logger.info("=" * 60)
        logger.info("Starting data processing pipeline")
        logger.info("=" * 60)

        # Step 1: Import data
        run_dials_import(working_dir, params)

        # Step 2: Find spots
        run_dials_find_spots(working_dir, params)

        # Step 3: Process results
        summary = process_spotfinding_results(working_dir, params)

        # Log summary
        logger.info("=" * 60)
        logger.info("Processing Summary:")
        logger.info(f"  Experiments: {summary['n_experiments']}")
        logger.info(f"  Total reflections: {summary['n_reflections']}")
        logger.info(
            f"  Average spots per experiment: "
            f"{summary['reflections_per_experiment']:.1f}"
        )
        logger.info("=" * 60)

        write_citations(program="xia2.countrate")

    except Exception as e:
        with open("xia2-error.txt", "w") as fh:
            traceback.print_exc(file=fh)
        logger.error('Error: "%s"', str(e))
        logger.info(traceback.format_exc())
        sys.exit(1)
