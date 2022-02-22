from __future__ import annotations

import contextlib
import copy
import json
import logging
import os
from pathlib import Path
from typing import List, Tuple

from cctbx import crystal, sgtbx, uctbx
from dials.algorithms.indexing.ssx.analysis import (
    generate_html_report,
    generate_plots,
    make_summary_table,
    report_on_crystal_clusters,
)
from dials.algorithms.integration.ssx.ssx_integrate import (
    generate_html_report as generate_integration_html_report,
)
from dials.algorithms.shoebox import MaskCode
from dials.array_family import flex
from dials.command_line.find_spots import working_phil as find_spots_phil
from dials.command_line.ssx_index import index, phil_scope
from dials.command_line.ssx_integrate import run_integration, working_phil
from dials.util.ascii_art import spot_counts_per_image_plot
from dxtbx.model import ExperimentList
from dxtbx.serialize import load
from xfel.clustering.cluster import Cluster

from xia2.Handlers.Streams import banner

logger = logging.getLogger("dials")


@contextlib.contextmanager
def run_in_directory(directory):
    owd = os.getcwd()
    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(owd)


def ssx_find_spots(working_directory: Path) -> flex.reflection_table:

    loggers_to_disable = [
        "dials.algorithms.spot_finding.finder",
        "dials.algorithms.spot_finding.factory",
        "dials.array_family.flex_ext",
    ]

    for name in loggers_to_disable:
        logging.getLogger(name).disabled = True

    with run_in_directory(working_directory):
        imported_expts = load.experiment_list("imported.expt", check_format=True)
        params = find_spots_phil.extract()

        # Do spot-finding
        logger.notice(banner("Spotfinding"))
        reflections = flex.reflection_table.from_observations(imported_expts, params)
        good = MaskCode.Foreground | MaskCode.Valid
        reflections["n_signal"] = reflections["shoebox"].count_mask_values(good)
        logger.info(spot_counts_per_image_plot(reflections))
    return reflections


def ssx_index(
    working_directory: Path,
    nproc: int = 1,
    space_group: sgtbx.space_group = None,
    unit_cell: uctbx.unit_cell = None,
) -> Tuple[ExperimentList, flex.reflection_table, List[Cluster]]:
    with run_in_directory(working_directory):
        strong_refl = flex.reflection_table.from_file("strong.refl")
        imported_expts = load.experiment_list("imported.expt", check_format=False)
        params = phil_scope.extract()
        params.indexing.nproc = nproc
        if unit_cell:
            params.indexing.known_symmetry.unit_cell = unit_cell
        if space_group:
            params.indexing.known_symmetry.space_group = space_group
        logger.notice(banner("Indexing"))
        indexed_experiments, indexed_reflections, summary_data = index(
            imported_expts, strong_refl, params
        )
        logger.info(
            "\nSummary of images sucessfully indexed\n"
            + make_summary_table(summary_data)
        )
        n_images = len({e.imageset.get_path(0) for e in indexed_experiments})
        logger.info(
            f"{indexed_reflections.size()} spots indexed on {n_images} images\n"
        )

        crystal_symmetries = [
            crystal.symmetry(
                unit_cell=expt.crystal.get_unit_cell(),
                space_group=expt.crystal.get_space_group(),
            )
            for expt in indexed_experiments
        ]

        cluster_plots, large_clusters = report_on_crystal_clusters(
            crystal_symmetries, True
        )

        summary_plots = generate_plots(summary_data)
        summary_plots.update(cluster_plots)
        generate_html_report(summary_plots, "dials.ssx_index.html")
        with open("dials.ssx_index.json", "w") as outfile:
            json.dump(summary_plots, outfile)
    return indexed_experiments, indexed_reflections, large_clusters


def ssx_integrate(working_directory, integration_params):
    with run_in_directory(working_directory):
        indexed_refl = flex.reflection_table.from_file(
            "indexed.refl"
        ).split_by_experiment_id()
        indexed_expts = load.experiment_list("indexed.expt", check_format=True)
        params = working_phil.extract()
        params.output.batch_size = 100
        params.algorithm = integration_params.algorithm

        if integration_params.algorithm == "ellipsoid":
            params.profile.ellipsoid.refinement.outlier_probability = 0.95
            params.profile.ellipsoid.refinement.max_separation = 1
            params.profile.ellipsoid.prediction.probability = 0.95
            params.profile.ellipsoid.rlp_mosaicity.model == integration_params.ellipsoid.rlp_mosaicity

        # Run the integration
        logger.notice(banner("Integrating"))
        integrated_crystal_symmetries = []
        for i, (int_expt, int_refl, aggregator) in enumerate(
            run_integration(indexed_refl, indexed_expts, params)
        ):
            reflections_filename = f"integrated_{i+1}.refl"
            experiments_filename = f"integrated_{i+1}.expt"
            logger.info(
                f"Saving {int_refl.size()} reflections to {reflections_filename}"
            )
            int_refl.as_file(reflections_filename)
            logger.info(f"Saving the experiments to {experiments_filename}")
            int_expt.as_file(experiments_filename)

            integrated_crystal_symmetries.extend(
                [
                    crystal.symmetry(
                        unit_cell=copy.deepcopy(cryst.get_unit_cell()),
                        space_group=copy.deepcopy(cryst.get_space_group()),
                    )
                    for cryst in int_expt.crystals()
                ]
            )
        # Report on clustering, and generate html report and json output
        plots = {}
        cluster_plots, _ = report_on_crystal_clusters(
            integrated_crystal_symmetries,
            make_plots=True,
        )
        plots = aggregator.make_plots()
        plots.update(cluster_plots)
        generate_integration_html_report(plots, "dials.ssx_integrate.html")
        with open("dials.ssx_integrate.json", "w") as outfile:
            json.dump(plots, outfile, indent=2)


def best_cell_from_cluster(cluster: Cluster) -> Tuple:
    from cctbx import crystal
    from cctbx.sgtbx.lattice_symmetry import metric_subgroups
    from cctbx.uctbx import unit_cell

    input_symmetry = crystal.symmetry(
        unit_cell=unit_cell(cluster.medians[0:6]), space_group_symbol="P 1"
    )
    group = metric_subgroups(input_symmetry, 3.00).result_groups[0]
    uc_params_conv = group["best_subsym"].unit_cell().parameters()
    sg = group["best_subsym"].space_group_info().symbol_and_number()
    return sg, uc_params_conv
