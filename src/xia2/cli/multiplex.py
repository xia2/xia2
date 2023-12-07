from __future__ import annotations

import logging
import os
import random
import sys

import iotbx.cif
import iotbx.phil
import numpy as np
from dials.array_family import flex
from dials.util.exclude_images import exclude_image_ranges_for_scaling
from dials.util.multi_dataset_handling import (
    assign_unique_identifiers,
    parse_multiple_datasets,
)
from dials.util.options import ArgumentParser, flatten_experiments, flatten_reflections
from dials.util.reference import intensities_from_reference_file
from dials.util.version import dials_version

import xia2.Handlers.Streams
from xia2.Applications.xia2_main import write_citations
from xia2.Handlers.Citations import Citations
from xia2.Modules.MultiCrystal import ScaleAndMerge
from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis

logger = logging.getLogger("xia2.multiplex")

help_message = """
xia2.multiplex performs symmetry analysis, scaling and merging of multi-crystal data
sets, as well as analysis of various pathologies that typically affect multi-crystal
data sets, including non-isomorphism, radiation damage and preferred orientation.

It uses a number of DIALS programs internally, including dials.cosym,
dials.two_theta_refine, dials.scale and dials.symmetry:

- Preliminary filtering of datasets using hierarchical unit cell clustering
- Laue group determination and resolution of indexing ambiguities with dials.cosym
- Determination of "best" overall unit cell with dials.two_theta_refine
- Initial round of scaling with dials.scale
- Estimation of resolution limit with dials.estimate_resolution
- Final round of scaling after application of the resolution limit
- Analysis of systematic absences with dials.symmetry
- Optional ΔCC½ filtering to remove outlier data sets
- Analysis of non-isomorphism, radiation damage and preferred orientation

For further details, and to cite usage, please see:
`Gildea, R. J. et al. (2022) Acta Cryst. D78, 752-769 <https://doi.org/10.1107/S2059798322004399>`_.

Examples use cases
------------------

Multiple integrated experiments and reflections in combined files::

  xia2.multiplex integrated.expt integrated.refl

Integrated experiments and reflections in separate input files::

  xia2.multiplex integrated_1.expt integrated_1.refl \\
    integrated_2.expt integrated_2.refl

Override the automatic space group determination and resolution estimation::

  xia2.multiplex space_group=C2 resolution.d_min=2.5 \\
    integrated_1.expt integrated_1.refl \\
    integrated_2.expt integrated_2.refl

Filter potential outlier data sets using the ΔCC½ method::

  xia2.multiplex filtering.method=deltacchalf \\
    integrated.expt integrated.refl

"""

phil_scope = iotbx.phil.parse(
    """
include scope xia2.Modules.MultiCrystal.ScaleAndMerge.phil_scope

include scope dials.util.exclude_images.phil_scope

wavelength_tolerance = 0.0001
  .type = float
  .help = "Absolute tolerance, in Angstroms, for determining whether to merge data from different"
          "wavelengths in the output mtz/sca files. Increasing this number significantly may reduce"
          "downstream data quality due to loss of information on wavelength."

seed = 42
  .type = int(value_min=0)

max_cluster_height_difference = 0.5
  .type = float
  .short_caption = "Maximum hight difference between clusters"
max_output_clusters = 10
  .type = int
  .short_caption = "Maximum number of important clusters to be output"
min_cluster_size = 5
  .type = int
  .short_caption = "Minimum number of datasets for an important cluster"
output_cluster_number = 0
  .type = int
  .short_caption = "Option to output a specific cluster when re-running the code"

output {
  log = xia2.multiplex.log
    .type = str
}
""",
    process_includes=True,
)

# override default parameters
phil_scope = phil_scope.fetch(
    source=iotbx.phil.parse(
        """\
r_free_flags.extend = True
"""
    )
)


def run(args=sys.argv[1:]):
    Citations.cite("xia2.multiplex")

    usage = "xia2.multiplex [options] [param.phil] integrated.expt integrated.refl"

    # Create the parser
    parser = ArgumentParser(
        usage=usage,
        phil=phil_scope,
        read_reflections=True,
        read_experiments=True,
        check_format=False,
        epilog=help_message,
    )

    # Parse the command line
    params, options = parser.parse_args(args=args, show_diff_phil=False)

    # Configure the logging
    xia2.Handlers.Streams.setup_logging(
        logfile=params.output.log, verbose=options.verbose
    )

    logger.info(dials_version())

    # Log the diff phil
    diff_phil = parser.diff_phil.as_str()
    if diff_phil != "":
        logger.info("The following parameters have been modified:\n")
        logger.info(diff_phil)

    # Try to load the models and data
    if len(params.input.experiments) == 0:
        logger.info("No Experiments found in the input")
        parser.print_help()
        return
    if len(params.input.reflections) == 0:
        logger.info("No reflection data found in the input")
        parser.print_help()
        return
    try:
        assert len(params.input.reflections) == len(params.input.experiments)
    except AssertionError:
        raise sys.exit(
            "The number of input reflections files does not match the "
            "number of input experiments"
        )

    if params.seed is not None:
        flex.set_random_seed(params.seed)
        np.random.seed(params.seed)
        random.seed(params.seed)

    experiments = flatten_experiments(params.input.experiments)
    reflections = flatten_reflections(params.input.reflections)
    if len(experiments) < 2:
        sys.exit("xia2.multiplex requires a minimum of two experiments")
    reflections = parse_multiple_datasets(reflections)
    experiments, reflections = assign_unique_identifiers(experiments, reflections)

    reflections, experiments = exclude_image_ranges_for_scaling(
        reflections, experiments, params.exclude_images
    )

    reflections_all = flex.reflection_table()
    assert len(reflections) == 1 or len(reflections) == len(experiments)
    for i, (expt, refl) in enumerate(zip(experiments, reflections)):
        reflections_all.extend(refl)
    reflections_all.assert_experiment_identifiers_are_consistent(experiments)

    if params.identifiers is not None:
        identifiers = []
        for identifier in params.identifiers:
            identifiers.extend(identifier.split(","))
        params.identifiers = identifiers

    # If a reference file is defined, will make sure that multiplex output is consistent space group
    # dials.reindex is later used on the scaled and merged result to retain consistent setting

    if params.reference is not None:
        intensity_array = intensities_from_reference_file(params.reference)
        if params.symmetry.space_group is not None:
            intensity_sg_no = intensity_array.space_group().type().number()
            params_sg_no = params.symmetry.space_group.type().number()
            if intensity_sg_no != params_sg_no:
                raise sys.exit(
                    f"The input space group (#{params_sg_no}) does not match the reference file (#{intensity_sg_no})"
                )
        else:
            params.symmetry.space_group = intensity_array.space_group_info()
            logger.info(
                f"symmetry.space_group has been set to: {params.symmetry.space_group}"
            )

    if params.cluster_analysis:
        if not params.min_completeness and not params.min_multiplicity:
            raise sys.exit(
                "To perform cluster analysis please set either min_completeness or min_multiplicity to output clusters."
            )
        elif params.reference is None:
            raise sys.exit(
                "For consistent output of clusters please provide a reference."
            )

    try:
        multiplex = ScaleAndMerge.MultiCrystalScale(
            experiments, reflections_all, params
        )
    except ValueError as e:
        sys.exit(str(e))

    # Optional Cluster Analysis

    # Make sure multiplex successful

    if multiplex._params.cluster_analysis:
        if not os.path.exists("xia2.multiplex.html"):
            raise sys.exit("Multiplex did not finish - cannot perform cluster analysis")

        # So the clusters have the same r-free flags as the parent (more or less doing what multiplex would do anyway if clusters were output normally):
        multiplex._params.r_free_flags.reference = os.path.join(
            os.getcwd(), "scaled.mtz"
        )

        (
            file_data,
            list_of_clusters,
        ) = MultiCrystalAnalysis.interesting_cluster_identification(
            multiplex.clusters, params
        )

        print("CLUSTERS")
        print(multiplex.clusters)

        if multiplex._params.output_cluster_number != 0:
            list_of_clusters.append(
                "cluster_%i" % multiplex._params.output_cluster_number
            )
            logger.info(
                "Additional cluster to Scale: cluster_%i"
                % multiplex._params.output_cluster_number
            )

        data_manager = multiplex._data_manager
        identifiers_all = [i.identifier for i in data_manager._experiments]
        el = data_manager._experiments
        ids = list(el.identifiers())

        print("IDENTIFIER LENGTHS")
        print(len(identifiers_all))

        path_to_id = {}

        for item in identifiers_all:
            ex = el[ids.index(item)]
            i = ex.imageset
            path = i.paths()[0]
            path_to_id[path] = item

        print("PATH TO ID")
        print(path_to_id)

        for item in list_of_clusters:
            if not os.path.exists(item):
                os.mkdir(item)
            os.chdir(item)
            logger.info("Scaling: %s" % item)
            for cluster in multiplex.clusters:
                if "cluster_" + str(cluster.cluster_id) == item:
                    identifiers = []
                    for frame in multiplex.cluster_images[cluster.cluster_id]:
                        identifiers.append(path_to_id[frame])
                    # CHECK THIS WITH JAMES
                    free_flags_in_full_set = True
                    print("IDENTIFIERS")
                    print(identifiers)
                    try:
                        multiplex.scale_cluster(
                            data_manager, identifiers, free_flags_in_full_set
                        )
                    except ValueError as e:
                        sys.exit(str(e))
            os.chdir("..")

    write_citations(program="xia2.multiplex")
