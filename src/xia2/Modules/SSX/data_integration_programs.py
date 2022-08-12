from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import dataclass
from functools import reduce
from pathlib import Path
from typing import List, Optional, Tuple

import iotbx.phil
from cctbx import crystal, sgtbx, uctbx
from dials.algorithms.clustering.unit_cell import Cluster
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
from dials.command_line.combine_experiments import CombineWithReference
from dials.command_line.find_spots import working_phil as find_spots_phil
from dials.command_line.refine import run_dials_refine
from dials.command_line.refine import working_phil as refine_phil
from dials.command_line.ssx_index import index
from dials.command_line.ssx_index import phil_scope as indexing_phil
from dials.command_line.ssx_integrate import run_integration
from dials.command_line.ssx_integrate import working_phil as integration_phil
from dials.util.ascii_art import spot_counts_per_image_plot
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Driver.timing import record_step
from xia2.Handlers.Files import FileHandler
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
    phil: Optional[Path] = None

    @classmethod
    def from_phil(cls, params):
        spotfinding_phil = None
        if params.spotfinding.phil:
            spotfinding_phil = Path(params.spotfinding.phil).resolve()
            if not spotfinding_phil.is_file():
                raise FileNotFoundError(os.fspath(spotfinding_phil))
        return cls(
            params.spotfinding.min_spot_size,
            params.spotfinding.max_spot_size,
            params.d_min,
            params.multiprocessing.nproc,
            spotfinding_phil,
        )


@dataclass
class IndexingParams:
    space_group: Optional[sgtbx.space_group] = None
    unit_cell: Optional[uctbx.unit_cell] = None
    max_lattices: int = 1
    nproc: int = 1
    phil: Optional[Path] = None
    output_nuggets_dir: Optional[Path] = None

    @classmethod
    def from_phil(cls, params):
        indexing_phil = None
        if params.indexing.phil:
            indexing_phil = Path(params.indexing.phil).resolve()
            if not indexing_phil.is_file():
                raise FileNotFoundError(os.fspath(indexing_phil))
        if params.indexing.unit_cell and params.space_group:
            try:
                _ = crystal.symmetry(
                    unit_cell=params.indexing.unit_cell,
                    space_group_info=params.space_group,
                    assert_is_compatible_unit_cell=True,
                )
            except AssertionError as e:
                raise ValueError(e)
        return cls(
            params.space_group,
            params.indexing.unit_cell,
            params.indexing.max_lattices,
            params.multiprocessing.nproc,
            indexing_phil,
        )


@dataclass
class RefinementParams:
    phil: Optional[Path] = None

    @classmethod
    def from_phil(cls, params):
        refinement_phil = None
        if params.geometry_refinement.phil:
            refinement_phil = Path(params.geometry_refinement.phil).resolve()
            if not refinement_phil.is_file():
                raise FileNotFoundError(os.fspath(refinement_phil))
        return cls(refinement_phil)


@dataclass
class IntegrationParams:
    algorithm: str = "ellipsoid"
    rlp_mosaicity: str = "angular4"
    d_min: Optional[float] = None
    nproc: int = 1
    phil: Optional[Path] = None
    output_nuggets_dir: Optional[Path] = None

    @classmethod
    def from_phil(cls, params):
        integration_phil = None
        if params.integration.phil:
            integration_phil = Path(params.integration.phil).resolve()
            if not integration_phil.is_file():
                raise FileNotFoundError(os.fspath(integration_phil))
        return cls(
            params.integration.algorithm,
            params.integration.ellipsoid.rlp_mosaicity,
            params.d_min,
            params.multiprocessing.nproc,
            integration_phil,
        )


def ssx_find_spots(
    working_directory: Path,
    spotfinding_params: SpotfindingParams,
) -> flex.reflection_table:
    if not (working_directory / "imported.expt").is_file():
        raise ValueError(f"Data has not yet been imported into {working_directory}")
    xia2_logger.notice(banner("Spotfinding"))  # type: ignore
    logfile = "dials.find_spots.log"
    with run_in_directory(working_directory), log_to_file(
        logfile
    ) as dials_logger, record_step("dials.find_spots"):
        # Set up the input
        imported_expts = load.experiment_list("imported.expt", check_format=True)
        xia2_phil = f"""
          input.experiments = imported.expt
          spotfinder.mp.nproc = {spotfinding_params.nproc}
          spotfinder.filter.max_spot_size = {spotfinding_params.max_spot_size}
          spotfinder.filter.min_spot_size = {spotfinding_params.min_spot_size}
        """
        if spotfinding_params.d_min:
            xia2_phil += f"\nspotfinder.filter.d_min = {spotfinding_params.d_min}"
        if spotfinding_params.phil:
            itpr = find_spots_phil.command_line_argument_interpreter()
            try:
                user_phil = itpr.process(args=[os.fspath(spotfinding_params.phil)])[0]
                working_phil = find_spots_phil.fetch(
                    sources=[user_phil, iotbx.phil.parse(xia2_phil)]
                )
            except Exception as e:
                xia2_logger.warning(
                    f"Unable to interpret {spotfinding_params.phil} as a spotfinding phil file. Error:\n{e}"
                )
                working_phil = find_spots_phil.fetch(
                    sources=[iotbx.phil.parse(xia2_phil)]
                )
        else:
            working_phil = find_spots_phil.fetch(sources=[iotbx.phil.parse(xia2_phil)])
        diff_phil = find_spots_phil.fetch_diff(source=working_phil)
        params = working_phil.extract()
        dials_logger.info(
            "The following parameters have been modified:\n"
            + "input.experiments = imported.expt\n"
            + f"{diff_phil.as_str()}"
        )
        # Do spot-finding
        reflections = flex.reflection_table.from_observations(imported_expts, params)
        good = MaskCode.Foreground | MaskCode.Valid
        reflections["n_signal"] = reflections["shoebox"].count_mask_values(good)

        isets = imported_expts.imagesets()
        if len(isets) > 1:
            for i, imageset in enumerate(isets):
                selected = flex.bool(reflections.nrows(), False)
                for j, experiment in enumerate(imported_expts):
                    if experiment.imageset is not imageset:
                        continue
                    selected.set_selected(reflections["id"] == j, True)
                plot = spot_counts_per_image_plot(reflections.select(selected))
                out_ = f"Histogram of per-image spot count for imageset {i}:\n" + plot
                dials_logger.info(out_)
                xia2_logger.info(out_)
        else:
            plot = spot_counts_per_image_plot(reflections)
            dials_logger.info(plot)
            xia2_logger.info(plot)

    return reflections


def clusters_from_experiments(
    experiments: ExperimentList,
) -> Tuple[dict, List[Cluster]]:
    crystal_symmetries = [
        crystal.symmetry(
            unit_cell=expt.crystal.get_unit_cell(),
            space_group=expt.crystal.get_space_group(),
        )
        for expt in experiments
    ]
    cluster_plots, large_clusters = report_on_crystal_clusters(crystal_symmetries, True)
    return cluster_plots, large_clusters


def ssx_index(
    working_directory: Path,
    indexing_params: IndexingParams,
) -> Tuple[ExperimentList, flex.reflection_table, dict]:
    if not (working_directory / "imported.expt").is_file():
        raise ValueError(f"Data has not yet been imported into {working_directory}")
    if not (working_directory / "strong.refl").is_file():
        raise ValueError(f"Unable to find spotfinding results in {working_directory}")
    xia2_logger.notice(banner("Indexing"))  # type: ignore
    with run_in_directory(working_directory):
        logfile = "dials.ssx_index.log"
        with log_to_file(logfile) as dials_logger, record_step("dials.ssx_index"):
            # Set up the input and log it to the dials log file
            strong_refl = flex.reflection_table.from_file("strong.refl")
            imported_expts = load.experiment_list("imported.expt", check_format=False)
            xia2_phil = f"""
            input.experiments = imported.expt
            input.reflections = strong.refl
            indexing.nproc={indexing_params.nproc}
            """
            if indexing_params.unit_cell:
                uc = ",".join(str(i) for i in indexing_params.unit_cell.parameters())
                xia2_phil += f"\nindexing.known_symmetry.unit_cell={uc}"
            if indexing_params.space_group:
                xia2_phil += f"\nindexing.known_symmetry.space_group={str(indexing_params.space_group)}"
            if indexing_params.max_lattices > 1:
                xia2_phil += f"\nindexing.multiple_lattice_search.max_lattices={indexing_params.max_lattices}"
            if indexing_params.output_nuggets_dir:
                xia2_phil += (
                    f"\noutput.nuggets={os.fspath(indexing_params.output_nuggets_dir)}"
                )

            if indexing_params.phil:
                itpr = indexing_phil.command_line_argument_interpreter()
                try:
                    user_phil = itpr.process(args=[os.fspath(indexing_params.phil)])[0]
                    working_phil = indexing_phil.fetch(
                        sources=[user_phil, iotbx.phil.parse(xia2_phil)]
                    )
                    # Note, the order above makes the xia2_phil take precedent
                    # over the user phil
                except Exception as e:
                    xia2_logger.warning(
                        f"Unable to interpret {indexing_params.phil} as an indexing phil file. Error:\n{e}"
                    )
                    working_phil = indexing_phil.fetch(
                        sources=[iotbx.phil.parse(xia2_phil)]
                    )
            else:
                working_phil = indexing_phil.fetch(
                    sources=[iotbx.phil.parse(xia2_phil)]
                )
            diff_phil = indexing_phil.fetch_diff(source=working_phil)
            params = working_phil.extract()
            dials_logger.info(
                "The following parameters have been modified:\n"
                + "input.experiments = imported.expt\n"
                + "input.reflections = strong.refl\n"
                + f"{diff_phil.as_str()}"
            )

            # Do the indexing
            indexed_experiments, indexed_reflections, summary_data = index(
                imported_expts, strong_refl, params
            )
            n_images = reduce(
                lambda a, v: a + (v[0]["n_indexed"] > 0), summary_data.values(), 0
            )
            indexing_success_per_image = [
                bool(v[0]["n_indexed"]) for v in summary_data.values()
            ]
            report = (
                "Summary of images sucessfully indexed\n"
                + make_summary_table(summary_data)
                + f"\n{indexed_reflections.size()} spots indexed on {n_images} images"
            )

            dials_logger.info(report)

            # Report on clustering, and generate html report and json output
            if indexed_experiments:
                cluster_plots, large_clusters = clusters_from_experiments(
                    indexed_experiments
                )
            else:
                cluster_plots, large_clusters = ({}, [])

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
            summary_for_xia2 = {
                "n_images_indexed": n_images,
                "large_clusters": large_clusters,
                "success_per_image": indexing_success_per_image,
            }
    return indexed_experiments, indexed_reflections, summary_for_xia2


def combine_with_reference(experiments: ExperimentList) -> ExperimentList:
    combine = CombineWithReference(
        detector=experiments[0].detector, beam=experiments[0].beam
    )
    elist = ExperimentList()
    for expt in experiments:
        elist.append(combine(expt))
    return elist


def run_refinement(
    working_directory: Path,
    refinement_params: RefinementParams,
) -> None:
    xia2_logger.notice(banner("Joint refinement"))  # type: ignore

    logfile = "dials.refine.log"
    with run_in_directory(working_directory), log_to_file(
        logfile
    ) as dials_logger, record_step("dials.refine"):

        indexed_refl = flex.reflection_table.from_file("indexed.refl")
        indexed_expts = load.experiment_list("indexed.expt", check_format=False)

        extra_defaults = """
            refinement.parameterisation.beam.fix="all"
            refinement.parameterisation.auto_reduction.action="fix"
            refinement.parameterisation.detector.fix_list="Tau1"
            refinement.refinery.engine=SparseLevMar
            refinement.reflections.outlier.algorithm=sauter_poon
        """

        if refinement_params.phil:
            itpr = refine_phil.command_line_argument_interpreter()
            try:
                user_phil = itpr.process(args=[os.fspath(refinement_params.phil)])[0]
                working_phil = refine_phil.fetch(
                    sources=[iotbx.phil.parse(extra_defaults), user_phil]
                )
                # Note, the order above makes the user phil take precedent over the extra defaults
            except Exception as e:
                xia2_logger.warning(
                    f"Unable to interpret {refinement_params.phil} as a refinement phil file. Error:\n{e}"
                )
                working_phil = refine_phil.fetch(
                    sources=[iotbx.phil.parse(extra_defaults)]
                )
        else:
            working_phil = refine_phil.fetch(sources=[iotbx.phil.parse(extra_defaults)])
        diff_phil = refine_phil.fetch_diff(source=working_phil)
        params = working_phil.extract()
        dials_logger.info(
            "The following parameters have been modified:\n"
            + "input.experiments = indexed.expt\n"
            + "input.reflections = indexed.refl\n"
            + f"{diff_phil.as_str()}"
        )

        expts, refls, refiner, _ = run_dials_refine(indexed_expts, indexed_refl, params)
        dials_logger.info("Saving refined experiments to refined.expt")
        expts.as_file("refined.expt")
        dials_logger.info("Saving reflections with updated predictions to refined.refl")
        refls.as_file("refined.refl")
        FileHandler.record_data_file(working_directory / "refined.expt")
        FileHandler.record_log_file(
            "dials.refine", working_directory / "dials.refine.log"
        )
        step_table = generate_refinement_step_table(refiner)
        xia2_logger.info("Summary of joint refinement steps:\n" + step_table)


def ssx_integrate(
    working_directory: Path, integration_params: IntegrationParams
) -> dict:
    if not (
        (working_directory / "indexed.expt").is_file()
        and (working_directory / "indexed.refl").is_file()
    ):
        raise ValueError(f"Unable to find indexing results in {working_directory}")

    xia2_logger.notice(banner("Integrating"))  # type: ignore
    with run_in_directory(working_directory):
        logfile = "dials.ssx_integrate.log"
        with log_to_file(logfile) as dials_logger, record_step("dials.ssx_integrate"):
            # Set up the input and log it to the dials log file
            indexed_refl = flex.reflection_table.from_file(
                "indexed.refl"
            ).split_by_experiment_id()
            indexed_expts = load.experiment_list("indexed.expt", check_format=True)

            xia2_phil = f"""
                nproc={integration_params.nproc}
                algorithm={integration_params.algorithm}
            """
            if integration_params.algorithm == "ellipsoid":
                model = integration_params.rlp_mosaicity
                xia2_phil += f"\nprofile.ellipsoid.rlp_mosaicity.model={model}"
            d_min = integration_params.d_min
            if d_min:
                xia2_phil += f"\nprediction.d_min={d_min}"
                if integration_params.algorithm == "ellipsoid":
                    xia2_phil += f"\nprofile.ellipsoid.prediction.d_min={d_min}"
            if integration_params.output_nuggets_dir:
                xia2_phil += f"\noutput.nuggets={os.fspath(integration_params.output_nuggets_dir)}"

            extra_defaults = """
                output.batch_size=1000
            """
            if integration_params.algorithm == "ellipsoid":
                extra_defaults += """
                profile.ellipsoid.refinement.outlier_probability=0.95
                profile.ellipsoid.refinement.max_separation=1
                profile.ellipsoid.prediction.probability=0.95
            """

            if integration_params.phil:
                itpr = integration_phil.command_line_argument_interpreter()
                try:
                    user_phil = itpr.process(args=[os.fspath(integration_params.phil)])[
                        0
                    ]
                    working_phil = integration_phil.fetch(
                        sources=[
                            iotbx.phil.parse(extra_defaults),
                            user_phil,
                            iotbx.phil.parse(xia2_phil),
                        ]
                    )
                    # Note, the order above makes the xia2_phil take precedent
                    # over the user phil, which takes precedent over the extra defaults
                except Exception as e:
                    xia2_logger.warning(
                        f"Unable to interpret {integration_params.phil} as an integration phil file. Error:\n{e}"
                    )
                    working_phil = integration_phil.fetch(
                        sources=[
                            iotbx.phil.parse(extra_defaults),
                            iotbx.phil.parse(xia2_phil),
                        ]
                    )
            else:
                working_phil = integration_phil.fetch(
                    sources=[
                        iotbx.phil.parse(extra_defaults),
                        iotbx.phil.parse(xia2_phil),
                    ]
                )
            diff_phil = integration_phil.fetch_diff(source=working_phil)
            params = working_phil.extract()
            dials_logger.info(
                "The following parameters have been modified:\n"
                + "input.experiments = indexed.expt\n"
                + "input.reflections = indexed.refl\n"
                + f"{diff_phil.as_str()}"
            )
            # Run the integration
            # Record the datafiles so that the information can be passed
            # out in the case of processing on multiple nodes, as adding to
            # the FileHandler won't work here.
            summary_for_xia2: dict = {"DataFiles": {"tags": [], "filenames": []}}
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
                summary_for_xia2["DataFiles"]["tags"].append(
                    f"integrated_{i+1} {working_directory.name}"
                )
                summary_for_xia2["DataFiles"]["filenames"].append(
                    working_directory / f"integrated_{i+1}.refl"
                )
                summary_for_xia2["DataFiles"]["tags"].append(
                    f"integrated_{i+1} {working_directory.name}"
                )
                summary_for_xia2["DataFiles"]["filenames"].append(
                    working_directory / f"integrated_{i+1}.expt"
                )
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
            plots = {}
            if integrated_crystal_symmetries:
                cluster_plots, large_clusters = report_on_crystal_clusters(
                    integrated_crystal_symmetries,
                    make_plots=True,
                )
            else:
                cluster_plots, large_clusters = ({}, {})
            if integrated_crystal_symmetries:
                plots = aggregator.make_plots()
                plots.update(cluster_plots)
                generate_integration_html_report(plots, "dials.ssx_integrate.html")
                with open("dials.ssx_integrate.json", "w") as outfile:
                    json.dump(plots, outfile, indent=2)

            summary_for_xia2["n_cryst_integrated"] = n_cryst
            summary_for_xia2["large_clusters"] = large_clusters
    return summary_for_xia2


def best_cell_from_cluster(cluster: Cluster) -> Tuple:

    input_symmetry = crystal.symmetry(
        unit_cell=uctbx.unit_cell(cluster.median_cell[0:6]), space_group_symbol="P 1"
    )
    group = sgtbx.lattice_symmetry.metric_subgroups(input_symmetry, 3.00).result_groups[
        0
    ]
    uc_params_conv = group["best_subsym"].unit_cell().parameters()
    sg = group["best_subsym"].space_group_info().symbol_and_number()
    return sg, uc_params_conv
