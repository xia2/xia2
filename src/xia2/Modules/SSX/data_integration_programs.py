from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass
from functools import reduce
from pathlib import Path
from typing import List, Optional, Tuple

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
from dials.command_line.refine import run_dials_refine
from dials.command_line.refine import working_phil as refine_working_phil
from dials.command_line.ssx_index import index, phil_scope
from dials.command_line.ssx_integrate import run_integration, working_phil
from dials.util.ascii_art import spot_counts_per_image_plot
from dxtbx.model import ExperimentList
from dxtbx.serialize import load
from xfel.clustering.cluster import Cluster

from xia2.Driver.timing import record_step
from xia2.Handlers.Streams import banner
from xia2.Modules.SSX.reporting import (
    generate_refinement_step_table,
    indexing_summary_output,
)
from xia2.Modules.SSX.util import log_to_file, run_in_directory

xia2_logger = logging.getLogger(__name__)


@dataclass
class SpotfindingParams:
    min_spot_size: int = 2
    max_spot_size: int = 10
    d_min: Optional[float] = None
    nproc: int = 1


@dataclass
class IndexingParams:
    space_group: Optional[sgtbx.space_group] = None
    unit_cell: Optional[uctbx.unit_cell] = None
    max_lattices: int = 1
    nproc: int = 1


@dataclass
class RefinementParams:
    outlier_algorithm: str = "sauter_poon"


@dataclass
class IntegrationParams:
    algorithm: str = "ellipsoid"
    rlp_mosaicity: str = "angular4"
    d_min: Optional[float] = None
    nproc: int = 1


def ssx_find_spots(
    working_directory: Path, spotfinding_params: SpotfindingParams
) -> flex.reflection_table:

    xia2_logger.notice(banner("Spotfinding"))  # type: ignore
    logfile = "dials.find_spots.log"
    with run_in_directory(working_directory), log_to_file(
        logfile
    ) as dials_logger, record_step("dials.find_spots"):
        # Set up the input
        imported_expts = load.experiment_list("imported.expt", check_format=True)
        params = find_spots_phil.extract()
        params.spotfinder.filter.max_spot_size = spotfinding_params.max_spot_size
        params.spotfinder.filter.min_spot_size = spotfinding_params.min_spot_size
        params.spotfinder.mp.nproc = spotfinding_params.nproc
        input_ = (
            "Input parameters:\n  experiments = imported.expt\n"
            + f"  spotfinder.mp.nproc = {spotfinding_params.nproc}\n"
            + f"  spotfinder.filter.max_spot_size = {spotfinding_params.max_spot_size}\n"
            + f"  spotfinder.filter.min_spot_size = {spotfinding_params.min_spot_size}\n"
        )
        if spotfinding_params.d_min:
            params.spotfinder.filter.d_min = spotfinding_params.d_min
            input_ += f"  spotfinder.filter.d_min = {spotfinding_params.d_min}"
        dials_logger.info(input_)
        # Do spot-finding
        reflections = flex.reflection_table.from_observations(imported_expts, params)
        good = MaskCode.Foreground | MaskCode.Valid
        reflections["n_signal"] = reflections["shoebox"].count_mask_values(good)
        plot = spot_counts_per_image_plot(reflections)
        dials_logger.info(plot)
        xia2_logger.info(plot)
    return reflections


def ssx_index(
    working_directory: Path,
    indexing_params: IndexingParams,
) -> Tuple[ExperimentList, flex.reflection_table, List[Cluster]]:

    xia2_logger.notice(banner("Indexing"))  # type: ignore
    with run_in_directory(working_directory):
        logfile = "dials.ssx_index.log"
        with log_to_file(logfile) as dials_logger, record_step(
            "dials.ssx_index (indexing)"
        ):
            # Set up the input and log it to the dials log file
            strong_refl = flex.reflection_table.from_file("strong.refl")
            imported_expts = load.experiment_list("imported.expt", check_format=False)
            params = phil_scope.extract()
            params.indexing.nproc = indexing_params.nproc
            input_ = (
                "Input parameters:\n  reflections = strong.refl\n"
                + f"  experiments = imported.expt\n  indexing.nproc = {indexing_params.nproc}\n"
            )
            if indexing_params.unit_cell:
                params.indexing.known_symmetry.unit_cell = indexing_params.unit_cell
                uc = ",".join(str(i) for i in indexing_params.unit_cell.parameters())
                input_ += f"  indexing.known_symmetry.unit_cell = {uc}\n"
            if indexing_params.space_group:
                params.indexing.known_symmetry.space_group = indexing_params.space_group
                input_ += f"  indexing.known_symmetry.space_group = {str(indexing_params.space_group)}\n"
            if indexing_params.max_lattices > 1:
                params.indexing.multiple_lattice_search.max_lattices = (
                    indexing_params.max_lattices
                )
                input_ += f"  indexing.multiple_lattice_search.max_lattices = {indexing_params.max_lattices}\n"
            dials_logger.info(input_)

            # Do the indexing
            indexed_experiments, indexed_reflections, summary_data = index(
                imported_expts, strong_refl, params
            )
            n_images = reduce(
                lambda a, v: a + (v[0]["n_indexed"] > 0), summary_data.values(), 0
            )
            report = (
                "Summary of images sucessfully indexed\n"
                + make_summary_table(summary_data)
                + f"\n{indexed_reflections.size()} spots indexed on {n_images} images"
            )

            dials_logger.info(report)

        with record_step("dials.ssx_index (clustering)"):
            # Report on clustering, and generate html report and json output
            if indexed_experiments:
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
            else:
                cluster_plots, large_clusters = ({}, {})
        with record_step("dials.ssx_index (reporting)"):
            summary_plots = {}
            if indexed_experiments:
                summary_plots = generate_plots(summary_data)
            output_ = (
                f"{indexed_reflections.size()} spots indexed on {n_images} images\n"
                + f"{indexing_summary_output(summary_data, summary_plots)}"
            )
            xia2_logger.info(output_)
            summary_plots.update(cluster_plots)
            if summary_plots:
                generate_html_report(summary_plots, "dials.ssx_index.html")
                with open("dials.ssx_index.json", "w") as outfile:
                    json.dump(summary_plots, outfile, indent=2)
    return indexed_experiments, indexed_reflections, large_clusters


def run_refinement(
    working_directory: Path,
    refinement_params: RefinementParams,
) -> None:
    xia2_logger.notice(banner("Joint refinement"))  # type: ignore

    logfile = "dials.refine.log"
    with run_in_directory(working_directory), log_to_file(
        logfile
    ) as dials_logger, record_step("dials.refine"):
        params = refine_working_phil.extract()
        indexed_refl = flex.reflection_table.from_file("indexed.refl")
        indexed_expts = load.experiment_list("indexed.expt", check_format=False)
        params.refinement.parameterisation.beam.fix = ["all"]
        params.refinement.parameterisation.auto_reduction.action = "fix"
        params.refinement.parameterisation.detector.fix_list = ["Tau1"]
        params.refinement.refinery.engine = "SparseLevMar"
        params.refinement.reflections.outlier.algorithm = (
            refinement_params.outlier_algorithm
        )
        input_ = (
            "Input parameters:\n  reflections = indexed.refl\n  experiments = indexed.expt\n"
            + "  refinement.parameterisation.beam.fix = all\n"
            + "  refinement.parameterisation.auto_reduction.action = fix\n"
            + "  refinement.parameterisation.detector.fix_list = Tau1\n"
            + "  refinement.refinery.engine = SparseLevMar\n"
            + f" refinement.reflections.outlier.algorithm = {refinement_params.outlier_algorithm}\n"
        )
        dials_logger.info(input_)
        expts, refls, refiner, _ = run_dials_refine(indexed_expts, indexed_refl, params)
        dials_logger.info("Saving refined experiments to refined.expt")
        expts.as_file("refined.expt")
        dials_logger.info("Saving reflections with updated predictions to refined.refl")
        refls.as_file("refined.refl")
        step_table = generate_refinement_step_table(refiner)
        xia2_logger.info("Summary of joint refinement steps:\n" + step_table)


def ssx_integrate(
    working_directory: Path, integration_params: IntegrationParams
) -> List[Cluster]:

    xia2_logger.notice(banner("Integrating"))  # type: ignore
    with run_in_directory(working_directory):
        logfile = "dials.ssx_integrate.log"
        with log_to_file(logfile) as dials_logger, record_step(
            "dials.ssx_integrate (integration)"
        ):
            # Set up the input and log it to the dials log file
            indexed_refl = flex.reflection_table.from_file(
                "indexed.refl"
            ).split_by_experiment_id()
            indexed_expts = load.experiment_list("indexed.expt", check_format=True)
            params = working_phil.extract()
            params.output.batch_size = 1000
            params.algorithm = integration_params.algorithm
            params.nproc = integration_params.nproc
            input_ = (
                "Input parameters:\n  reflections = indexed.refl\n"
                + f"  nproc = {integration_params.nproc}\n"
                + f"  experiments = indexed.expt\n  algorithm = {integration_params.algorithm}\n"
                + "  output.batch_size = 1000\n"
            )
            if integration_params.algorithm == "ellipsoid":
                model = integration_params.rlp_mosaicity
                params.profile.ellipsoid.refinement.outlier_probability = 0.95
                params.profile.ellipsoid.refinement.max_separation = 1
                params.profile.ellipsoid.prediction.probability = 0.95
                params.profile.ellipsoid.rlp_mosaicity.model = model
                input_ += "  profile.ellipsoid.refinement.outlier_probability = 0.95\n"
                input_ += "  profile.ellipsoid.refinement.max_separation = 1\n"
                input_ += "  profile.ellipsoid.prediction.probability = 0.95\n"
                input_ += f"  profile.ellipsoid.rlp_mosaicity.model = {model}\n"
            d_min = integration_params.d_min
            if d_min:
                params.prediction.d_min = d_min
                input_ += f"  params.prediction.d_min = {d_min}\n"
                if integration_params.algorithm == "ellipsoid":
                    params.profile.ellipsoid.prediction.d_min = d_min
                    input_ += f"  params.profile.ellipsoid.prediction.d_min = {d_min}\n"
            dials_logger.info(input_)

            # Run the integration
            integrated_crystal_symmetries = []
            n_refl, n_cryst = (0, 0)
            for i, (int_expt, int_refl, aggregator) in enumerate(
                run_integration(indexed_refl, indexed_expts, params)
            ):
                reflections_filename = f"integrated_{i+1}.refl"
                experiments_filename = f"integrated_{i+1}.expt"
                n_refl += int_refl.size()
                dials_logger.info(
                    f"Saving {int_refl.size()} reflections to {reflections_filename}"
                )
                int_refl.as_file(reflections_filename)
                n_cryst += len(int_expt)
                dials_logger.info(f"Saving the experiments to {experiments_filename}")
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
            xia2_logger.info(f"{n_refl} reflections integrated from {n_cryst} crystals")

            # Report on clustering, and generate html report and json output
        with record_step("dials.ssx_integrate (clustering)"):
            plots = {}
            if integrated_crystal_symmetries:
                cluster_plots, large_clusters = report_on_crystal_clusters(
                    integrated_crystal_symmetries,
                    make_plots=True,
                )
            else:
                cluster_plots, large_clusters = ({}, {})
        with record_step("dials.ssx_integrate (reporting)"):
            if integrated_crystal_symmetries:
                plots = aggregator.make_plots()
                plots.update(cluster_plots)
                generate_integration_html_report(plots, "dials.ssx_integrate.html")
                with open("dials.ssx_integrate.json", "w") as outfile:
                    json.dump(plots, outfile, indent=2)
    return large_clusters


def best_cell_from_cluster(cluster: Cluster) -> Tuple:

    input_symmetry = crystal.symmetry(
        unit_cell=uctbx.unit_cell(cluster.medians[0:6]), space_group_symbol="P 1"
    )
    group = sgtbx.lattice_symmetry.metric_subgroups(input_symmetry, 3.00).result_groups[
        0
    ]
    uc_params_conv = group["best_subsym"].unit_cell().parameters()
    sg = group["best_subsym"].space_group_info().symbol_and_number()
    return sg, uc_params_conv
