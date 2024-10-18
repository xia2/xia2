from __future__ import annotations

import os
import subprocess

import pytest
from dials.algorithms.correlation.cluster import ClusterInfo
from dials.util.options import ArgumentParser
from libtbx import phil

from xia2.cli.multiplex import run as run_multiplex
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
    "output_clusters,interesting_clusters",
    [(False, False), (True, False), (True, True)],
)
def test_serial_data(dials_data, tmp_path, output_clusters, interesting_clusters):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    expt_int = os.fspath(ssx / "integrated.expt")
    refl_int = os.fspath(ssx / "integrated.refl")
    cmd = "xia2.ssx_reduce"
    if os.name == "nt":
        cmd += ".bat"
    args_generate_scaled = [cmd, expt_int, refl_int]
    expt_scaled = os.fspath(tmp_path / "DataFiles" / "scaled.expt")
    refl_scaled = os.fspath(tmp_path / "DataFiles" / "scaled.refl")
    cmd = "xia2.cluster_analysis"
    if os.name == "nt":
        cmd += ".bat"
    args_test_clustering = [
        cmd,
        "clustering.min_cluster_size=2",
        expt_scaled,
        refl_scaled,
        f"distinct_clusters={interesting_clusters}",
        "clustering.hierarchical.method=cos_angle+correlation",
        f"clustering.output_clusters={output_clusters}",
    ]
    result_generate_scaled = subprocess.run(
        args_generate_scaled, cwd=tmp_path, capture_output=True
    )
    assert not result_generate_scaled.returncode and not result_generate_scaled.stderr
    result = subprocess.run(args_test_clustering, cwd=tmp_path, capture_output=True)
    assert not result.returncode  # and not result.stderr
    check_output(tmp_path, output_clusters, interesting_clusters)


def test_rotation_data(dials_data, run_in_tmp_path):
    rot = dials_data("vmxi_proteinase_k_sweeps", pathlib=True)
    expt_1 = os.fspath(rot / "experiments_0.expt")
    expt_2 = os.fspath(rot / "experiments_1.expt")
    expt_3 = os.fspath(rot / "experiments_2.expt")
    expt_4 = os.fspath(rot / "experiments_3.expt")
    refl_1 = os.fspath(rot / "reflections_0.refl")
    refl_2 = os.fspath(rot / "reflections_1.refl")
    refl_3 = os.fspath(rot / "reflections_2.refl")
    refl_4 = os.fspath(rot / "reflections_3.refl")
    expt_scaled = os.fspath(run_in_tmp_path / "scaled.expt")
    refl_scaled = os.fspath(run_in_tmp_path / "scaled.refl")
    run_multiplex(
        [
            expt_1,
            refl_1,
            expt_2,
            refl_2,
            expt_3,
            refl_3,
            expt_4,
            refl_4,
        ]
    )
    cmd = "xia2.cluster_analysis"
    if os.name == "nt":
        cmd += ".bat"
    args_clustering = [
        cmd,
        "distinct_clusters=True",
        "clustering.min_cluster_size=2",
        "clustering.hierarchical.method=cos_angle+correlation",
        "clustering.output_clusters=True",
        expt_scaled,
        refl_scaled,
        "output.json=xia2.cluster_analysis.json",
    ]
    result = subprocess.run(args_clustering, capture_output=True)
    assert not result.returncode  # and not result.stderr
    assert (run_in_tmp_path / "xia2.cluster_analysis.json").is_file()
    assert (run_in_tmp_path / "xia2.cluster_analysis.log").is_file()
    assert (run_in_tmp_path / "xia2.cluster_analysis.html").is_file()
    assert (run_in_tmp_path / "cc_clusters" / "cluster_2").exists()


def check_output(main_dir, output_clusters=True, interesting_clusters=False):
    if output_clusters and not interesting_clusters:
        assert (main_dir / "cc_clusters" / "cluster_2").exists()
        assert (main_dir / "cos_clusters" / "cluster_2").exists()
    if output_clusters and interesting_clusters:
        assert (main_dir / "cc_clusters" / "cluster_2").exists()
        assert (main_dir / "cos_clusters" / "cluster_2").exists()
    assert (main_dir / "xia2.cluster_analysis.json").is_file()
    assert (main_dir / "xia2.cluster_analysis.log").is_file()
    assert (main_dir / "xia2.cluster_analysis.html").is_file()


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
    ) = MultiCrystalAnalysis.interesting_cluster_identification(clusters, params)

    assert list_of_clusters == expected
