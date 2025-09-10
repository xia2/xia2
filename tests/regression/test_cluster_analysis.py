from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from dials.algorithms.correlation.cluster import ClusterInfo
from dials.util.options import ArgumentParser
from dxtbx.model import ExperimentList
from libtbx import phil

from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis

phil_scope = phil.parse(
    """include scope xia2.cli.cluster_analysis.mca_phil""", process_includes=True
)
parser = ArgumentParser(phil=phil_scope, check_format=False)
params, _ = parser.parse_args(args=[], quick_parse=True)

#  Setup Test Clusters
# Test 1 - test rejects staircasing
# test 2 - checks min cluster size - rejects pairs where it's too small
# test 3 - test only outputs defined number of clusters
data_1 = [
    ClusterInfo(1, [1, 2, 3], 5, 100, [1, 1, 1, 90, 90, 90], 0.3),
    ClusterInfo(2, [1, 2, 3, 4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.35),
]

params_1 = params
params_1.clustering.max_output_clusters = 10
params_1.clustering.min_cluster_size = 2

data_2 = [
    ClusterInfo(1, [1, 2], 5, 100, [1, 1, 1, 90, 90, 90], 0.32),
    ClusterInfo(2, [4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.33),
    ClusterInfo(3, [1, 2, 3, 4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.35),
    ClusterInfo(4, [1, 2, 3, 4, 5, 6, 7], 5, 100, [1, 1, 1, 90, 90, 90], 0.37),
    ClusterInfo(5, [8, 9, 10], 5, 100, [1, 1, 1, 90, 90, 90], 0.375),
    ClusterInfo(
        6, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5, 100, [1, 1, 1, 90, 90, 90], 0.39
    ),
]

params_2 = params
params_2.clustering.max_output_clusters = 10
params_2.clustering.min_cluster_size = 3

data_3 = [
    ClusterInfo(1, [1, 2, 3], 5, 100, [1, 1, 1, 90, 90, 90], 0.32),
    ClusterInfo(2, [4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.33),
    ClusterInfo(3, [1, 2, 3, 4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.34),
    ClusterInfo(4, [6, 7, 8, 9, 10], 5, 100, [1, 1, 1, 90, 90, 90], 0.35),
    ClusterInfo(
        5,
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        5,
        100,
        [1, 1, 1, 90, 90, 90],
        0.36,
    ),
    ClusterInfo(
        6,
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        5,
        100,
        [1, 1, 1, 90, 90, 90],
        0.37,
    ),
    ClusterInfo(7, [14, 15, 16, 17], 5, 100, [1, 1, 1, 90, 90, 90], 0.375),
    ClusterInfo(
        8,
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
        5,
        100,
        [1, 1, 1, 90, 90, 90],
        0.39,
    ),
]

params_3 = params
params_3.clustering.max_output_clusters = 2
params_3.clustering.min_cluster_size = 2


@pytest.mark.parametrize(
    "output_clusters,interesting_clusters,output_correlation_cluster_number,exclude_correlation_cluster_number",
    [
        (False, False, None, None),
        (True, False, None, None),
        (True, True, None, None),
        (True, False, 1, None),
        (
            True,
            False,
            1,
            1,
        ),  # do this to check that the excluded cluster is actually different to cluster 1
    ],
)
def test_serial_data(
    dials_data,
    tmp_path,
    output_clusters,
    interesting_clusters,
    output_correlation_cluster_number,
    exclude_correlation_cluster_number,
):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    expt_int = os.fspath(ssx / "integrated.expt")
    refl_int = os.fspath(ssx / "integrated.refl")
    args_generate_scaled = [shutil.which("xia2.ssx_reduce"), expt_int, refl_int]
    expt_scaled = os.fspath(tmp_path / "DataFiles" / "scaled.expt")
    refl_scaled = os.fspath(tmp_path / "DataFiles" / "scaled.refl")
    args_test_clustering = [
        shutil.which("xia2.cluster_analysis"),
        "clustering.min_cluster_size=2",
        expt_scaled,
        refl_scaled,
        f"clustering.hierarchical.distinct_clusters={interesting_clusters}",
        "clustering.hierarchical.method=cos_angle+correlation",
        f"clustering.output_clusters={output_clusters}",
        f"output_correlation_cluster_number={output_correlation_cluster_number}",
        f"exclude_correlation_cluster_number={exclude_correlation_cluster_number}",
        "d_min=1.0",
    ]
    result_generate_scaled = subprocess.run(
        args_generate_scaled, cwd=tmp_path, capture_output=True
    )
    assert not result_generate_scaled.returncode and not result_generate_scaled.stderr
    result = subprocess.run(args_test_clustering, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(
        tmp_path,
        output_clusters,
        interesting_clusters,
        output_correlation_cluster_number,
        exclude_correlation_cluster_number,
    )


def test_rotation_data(dials_data, run_in_tmp_path):
    rot = dials_data("vmxi_proteinase_k_sweeps", pathlib=True)

    # First scale the data to get suitable input
    cmd = (
        [
            shutil.which("dials.scale"),
        ]
        + [rot / f"experiments_{i}.expt" for i in range(0, 4)]
        + [rot / f"reflections_{i}.refl" for i in range(0, 4)]
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
    )
    assert not result.returncode

    args_clustering = [
        shutil.which("xia2.cluster_analysis"),
        "clustering.hierarchical.distinct_clusters=True",
        "clustering.min_cluster_size=2",
        "clustering.hierarchical.method=cos_angle+correlation",
        "clustering.output_clusters=True",
        "scaled.expt",
        "scaled.refl",
        "output.json=xia2.cluster_analysis.json",
    ]
    result = subprocess.run(args_clustering, capture_output=True)
    assert not result.returncode and not result.stderr
    assert (run_in_tmp_path / "xia2.cluster_analysis.json").is_file()
    assert (run_in_tmp_path / "xia2.cluster_analysis.log").is_file()
    assert (run_in_tmp_path / "xia2.cluster_analysis.html").is_file()
    assert (run_in_tmp_path / "cc_clusters" / "cc_cluster_2").exists()
    assert not (run_in_tmp_path / "coordinate_clusters").exists()
    # now run coordinate clustering
    args_clustering = [
        shutil.which("xia2.cluster_analysis"),
        "clustering.method=coordinate",
        "clustering.min_cluster_size=2",
        "clustering.output_clusters=True",
        "scaled.expt",
        "scaled.refl",
        "output.json=xia2.cluster_analysis.json",
    ]
    result = subprocess.run(args_clustering, capture_output=True)
    assert not result.returncode and not result.stderr
    assert (run_in_tmp_path / "coordinate_clusters" / "cluster_0").exists()
    assert (
        run_in_tmp_path / "coordinate_clusters" / "cluster_0" / "cluster.refl"
    ).exists()
    assert (
        run_in_tmp_path / "coordinate_clusters" / "cluster_0" / "cluster.expt"
    ).exists()


def check_output(
    main_dir,
    output_clusters=True,
    interesting_clusters=False,
    output_correlation_cluster_number=None,
    exclude_correlation_cluster_number=None,
):
    if output_clusters and not any(
        [
            interesting_clusters,
            output_correlation_cluster_number,
            exclude_correlation_cluster_number,
        ]
    ):
        assert (main_dir / "cc_clusters" / "cc_cluster_2").exists()
        assert (main_dir / "cos_clusters" / "cos_cluster_2").exists()
    if output_clusters and interesting_clusters:
        assert (main_dir / "cc_clusters" / "cc_cluster_2").exists()
        assert (main_dir / "cos_clusters" / "cos_cluster_2").exists()
    assert (main_dir / "xia2.cluster_analysis.json").is_file()
    assert (main_dir / "xia2.cluster_analysis.log").is_file()
    assert (main_dir / "xia2.cluster_analysis.html").is_file()
    if output_correlation_cluster_number:
        assert (
            main_dir / "cc_clusters" / f"cluster_{output_correlation_cluster_number}"
        ).exists()
        expts = ExperimentList.from_file(
            main_dir
            / "cc_clusters"
            / f"cluster_{output_correlation_cluster_number}"
            / "cluster.expt",
            check_format=False,
        )
        assert len(expts.imagesets()) == 2
    if exclude_correlation_cluster_number:
        assert (
            main_dir
            / "cc_clusters"
            / f"excluded_cluster_{exclude_correlation_cluster_number}"
        ).exists()
        expts_ex = ExperimentList.from_file(
            main_dir
            / "cc_clusters"
            / f"excluded_cluster_{exclude_correlation_cluster_number}"
            / "cluster.expt",
            check_format=False,
        )
        expts_inc = ExperimentList.from_file(
            main_dir
            / "cc_clusters"
            / f"cluster_{exclude_correlation_cluster_number}"
            / "cluster.expt",
            check_format=False,
        )
        assert len(expts_ex.imagesets()) == 3
        assert len(expts_inc.imagesets()) == 2
        list_ex = []
        list_inc = []
        for i in expts_ex.imagesets():
            list_ex.append(i.paths()[0])
        for i in expts_inc.imagesets():
            list_inc.append(i.paths()[0])
        set_ex = set(list_ex)
        set_inc = set(list_inc)
        assert len(set_ex.intersection(set_inc)) == 0


@pytest.mark.parametrize(
    "clusters,params,expected",
    [
        (data_1, params_1, []),
        (data_2, params_2, ["cluster_4", "cluster_5"]),
        (data_3, params_3, ["cluster_3", "cluster_4", "cluster_6", "cluster_7"]),
    ],
)
def test_interesting_cluster_algorithm(clusters, params, expected):
    (
        file_data,
        list_of_clusters,
    ) = MultiCrystalAnalysis.interesting_cluster_identification(
        clusters, params.clustering
    )

    assert list_of_clusters == expected
