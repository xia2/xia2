from __future__ import annotations

import json
import logging
import pathlib
import subprocess
import sys
import time
import traceback
from collections import Counter
from itertools import accumulate

import h5py
import iotbx.phil
from dials.array_family import flex
from dials.util.options import ArgumentParser
from dxtbx.serialize import load

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations
from xia2.Handlers.Citations import Citations

logger = logging.getLogger("xia2.cli.countrate")

help_message = """
xia2.countrate: Process crystallography data through import and spotfinding.

This program performs the following steps:
1. Runs dials.import to import image data
2. Runs dials.find_spots to find strong spots
3. Analyses pixel intensities from shoeboxes to generate histogram of pixel intensities

Usage examples:
    xia2.countrate /path/to/data/data_master.h5
    xia2.countrate /path/to/data/image_####.cbf
    xia2.countrate image=/path/to/data.h5 spotfinder.filter.min_spot_size=3
"""

phil_scope = iotbx.phil.parse(
    """
input {
    image = None
        .type = str
        .help = "Path to image file (e.g., data_master.h5)"
    template = None
        .type = str
        .help = "Image template (e.g., image_####.cbf)"
    nproc = Auto
        .type = int
        .help = "Number of processes to use for spotfinding"
    target_countrate_pct = 10.0
        .type = float
        .help = "Target percentage of the detector trusted range to scale the reference percentile reflection to"
    ref_percentile = 99.9
        .type = float
        .help = "Percentile value used in transmission recommendation. xia2.countrate will calculate the transmission required to scale this percentile reflection intensity to the desired target_countrate_pct"
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
    histogram = "pixel_counts.json"
        .type = str
        .help = "JSON file containing histogram of pixel intensities and detector trusted range"
}
""",
    process_includes=True,
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
    else:
        raise ValueError(
            "Must provide one of: image file (.h5, .nxs) or template (.cbf)"
        )

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
        "ice_rings.filter=True",
        f"mp.nproc={params.input.nproc}",
    ]

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


def set_input_from_unhandled(params, unhandled: list[str]) -> None:
    """Set the input PHIL parameter from one positional input path."""
    if not unhandled:
        return
    if len(unhandled) > 1:
        raise ValueError("Please provide only one input path")
    if params.input.image or params.input.template:
        raise ValueError(
            "Please provide the input path either positionally or with image=, "
            "template=, or directory="
        )

    input_path = unhandled[0]
    if input_path.endswith(".cbf"):
        params.input.template = input_path
    elif input_path.endswith((".h5", ".nxs")):
        params.input.image = input_path
    else:
        raise ValueError("Input path must be a .cbf template, or a .h5/.nxs image file")


def process_spotfinding_results(
    working_dir: pathlib.Path, params
) -> tuple[dict[int, int], int, int]:
    """Process the spotfinding results and perform additional analysis."""
    logger.info("Processing spotfinding results...")

    # Load the reflections and experiments
    reflections_path = working_dir / params.output.reflections
    experiments_path = working_dir / params.output.experiments

    if not reflections_path.exists():
        raise FileNotFoundError(f"Reflections file not found: {reflections_path}")

    reflections = flex.reflection_table.from_file(str(reflections_path))
    experiment = load.experiment_list(str(experiments_path), check_format=False)[0]
    detector = experiment.detector.to_dict()

    detector_max_trusted_counts = detector["panels"][0]["trusted_range"][1]

    shoeboxes = reflections["shoebox"]
    n_reflections = len(shoeboxes)
    counter: Counter[int] = Counter()
    for shoebox in shoeboxes:
        counter.update(
            int(pixel_intensity)
            for pixel_intensity in shoebox.data.as_numpy_array().ravel()
        )
    sorted_counter = sorted(counter.items())
    histogram: dict[int, int] = dict(sorted_counter)

    return histogram, detector_max_trusted_counts, n_reflections


def save_hist_to_json(hist, max_trusted_value, results_path: pathlib.Path):
    logger.info(f"Saving counts histogram to {str(results_path)}")
    with open(results_path, "w") as f:
        json.dump({"counts": hist, "overload_limit": max_trusted_value}, f, indent=2)


def get_percentile_index(num_pixels, percentile):
    threshold = sum(num_pixels) * percentile

    for i, cum_sum in enumerate(accumulate(num_pixels)):
        if cum_sum >= threshold:
            return i

    return len(num_pixels)


def run(args=None):
    """Main entry point for the CLI program."""
    start_time = time.time()

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
            epilog=help_message,
        )

        params, options, unhandled = parser.parse_args(
            args=args, show_diff_phil=False, return_unhandled=True
        )
        set_input_from_unhandled(params, unhandled)

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
        logger.info("Starting xia2.countrate")
        logger.info("=" * 60)

        # Step 1: Import data
        run_dials_import(working_dir, params)

        experiments_file = working_dir / params.output.experiments
        if not experiments_file.exists():
            raise FileNotFoundError(f"Experiments file not found: {experiments_file}")
        experiment = load.experiment_list(str(experiments_file), check_format=False)[0]

        # Dials does not import experiment transmission from hdf5 files, so need to read it in directly.
        # TODO Fix this in Dials and then remove this code.
        if params.input.image and params.input.image.endswith((".h5", ".nxs")):
            with h5py.File(params.input.image, "r") as f:
                transmission = f[
                    "/entry/instrument/attenuator/attenuator_transmission"
                ][()]
                logger.debug(f"Read transmission from HDF5 file: {transmission:.2f}")
        else:
            transmission = experiment.beam.get_transmission()
            logger.debug(f"Read transmission from experiment: {transmission:.2f}")

        run_dials_find_spots(working_dir, params)

        hist, max_trusted_value, n_reflections = process_spotfinding_results(
            working_dir, params
        )

        save_hist_to_json(hist, max_trusted_value, params.output.histogram)

        max_pixel_count = max(hist.keys())
        max_pixel_percent_of_trusted_range = max_pixel_count * 100 / max_trusted_value

        num_pixels = list(hist.values())
        pixel_intensities = list(hist.keys())
        total_pixels = sum(num_pixels)

        percentiles = [99.999, 99.99, 99.9, 99.0, 90.0]
        percentile_trusted_range_pct: list[float] = []
        for percentile in percentiles:
            percentile_idx = get_percentile_index(num_pixels, percentile / 100)
            percentile_counts = pixel_intensities[percentile_idx]
            percentile_trusted_range_pct.append(
                percentile_counts * 100 / max_trusted_value
            )

        # Calculate transmission needed to scale reference percentile reflection to target countrate
        target_countrate_pct = params.input.target_countrate_pct
        target_counts = max_trusted_value * (target_countrate_pct / 100)
        ref_percentile = params.input.ref_percentile
        ref_percentile_idx = percentile_idx = get_percentile_index(
            num_pixels, ref_percentile / 100
        )
        ref_percentile_counts = pixel_intensities[ref_percentile_idx]
        scale_factor = target_counts / ref_percentile_counts
        recommended_transmission = min(transmission * scale_factor, 1.0)

        # Log summary
        logger.info("=" * 60)
        logger.info("Processing Summary:")
        logger.info(
            f"Found {total_pixels} pixels from {n_reflections} strong reflections\n"
        )
        logger.info(f"Experiment transmission = {transmission:.2f}")
        logger.info(
            f"Max pixel recorded at {max_pixel_percent_of_trusted_range:.2f}% of detector trusted range\n"
        )
        for i, percentile in enumerate(percentiles):
            logger.info(
                f"{percentile}% of pixels <= {percentile_trusted_range_pct[i]:.2f}% of detector trusted range\n"
            )
        logger.info(
            f"Recommended max transmission of {recommended_transmission * 100:.2f}% to keep {ref_percentile}% of pixel intensities below {target_countrate_pct}% of detector trusted range\n"
        )
        logger.info("=" * 60)

        duration = time.time() - start_time

        logger.info(
            f"Processing took {time.strftime('%Hh %Mm %Ss', time.gmtime(duration))}"
        )
        write_citations(program="xia2.countrate")

    except Exception as e:
        with open("xia2-error.txt", "w") as fh:
            traceback.print_exc(file=fh)
        logger.error('Error: "%s"', str(e))
        logger.info(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    run()
