from __future__ import annotations

import os
import subprocess

import pytest

from libtbx.phil import scope_extract

from xia2.cli.multiplex import run as run_multiplex
from xia2.Modules.MultiCrystal import ClusterInfo
from xia2.Modules.MultiCrystalAnalysis import MultiCrystalAnalysis

# Setup Test Clusters
# Test 1 - test rejects staircasing
# Test 2 - test only looks for ones with none in common AND min height threshold
# test 3 - checks min cluster size - rejects pairs where it's too small
# test 4 - test only outputs defined number of clusters
data_1 = [
    ClusterInfo(1, [1, 2, 3], 5, 100, [1, 1, 1, 90, 90, 90], 0.3),
    ClusterInfo(2, [1, 2, 3, 4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.35),
]
params_1 = scope_extract("test", "test", "test")
params_1.__inject__("max_cluster_height_difference", 0.1)
params_1.__inject__("max_output_clusters", 10)
params_1.__inject__("min_cluster_size", 2)

data_2 = [
    ClusterInfo(1, [1, 2, 3], 5, 100, [1, 1, 1, 90, 90, 90], 0.32),
    ClusterInfo(2, [4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.33),
    ClusterInfo(3, [1, 2, 3, 4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.35),
]
params_2 = scope_extract("test", "test", "test")
params_2.__inject__("max_cluster_height_difference", 0.0005)
params_2.__inject__("max_output_clusters", 10)
params_2.__inject__("min_cluster_size", 2)

params_2_5 = scope_extract("test", "test", "test")
params_2_5.__inject__("max_cluster_height_difference", 0.5)
params_2_5.__inject__("max_output_clusters", 10)
params_2_5.__inject__("min_cluster_size", 2)

data_3 = [
    ClusterInfo(1, [1, 2], 5, 100, [1, 1, 1, 90, 90, 90], 0.32),
    ClusterInfo(2, [4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.33),
    ClusterInfo(3, [1, 2, 3, 4, 5], 5, 100, [1, 1, 1, 90, 90, 90], 0.35),
    ClusterInfo(4, [1, 2, 3, 4, 5, 6, 7], 5, 100, [1, 1, 1, 90, 90, 90], 0.37),
    ClusterInfo(5, [8, 9, 10], 5, 100, [1, 1, 1, 90, 90, 90], 0.375),
    ClusterInfo(
        6, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5, 100, [1, 1, 1, 90, 90, 90], 0.39
    ),
]
params_3 = scope_extract("test", "test", "test")
params_3.__inject__("max_cluster_height_difference", 0.5)
params_3.__inject__("max_output_clusters", 10)
params_3.__inject__("min_cluster_size", 3)

data_4 = [
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
params_4 = scope_extract("test", "test", "test")
params_4.__inject__("max_cluster_height_difference", 0.5)
params_4.__inject__("max_output_clusters", 2)
params_4.__inject__("min_cluster_size", 2)


@pytest.mark.parametrize("run_cluster_identification", [True, False])
def test_serial_data(dials_data, tmp_path, run_cluster_identification):
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
        "min_cluster_size=2",
        expt_scaled,
        refl_scaled,
        f"run_cluster_identification={run_cluster_identification}",
    ]
    result_generate_scaled = subprocess.run(
        args_generate_scaled, cwd=tmp_path, capture_output=True
    )
    assert not result_generate_scaled.returncode and not result_generate_scaled.stderr
    result = subprocess.run(args_test_clustering, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, run_cluster_identification)


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
    args_clustering = [
        "xia2.cluster_analysis",
        "min_cluster_size=2",
        expt_scaled,
        refl_scaled,
    ]
    result = subprocess.run(args_clustering, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(run_in_tmp_path)


def check_output(main_dir, run_cluster_identification=True):
    assert (main_dir / "cc_clusters").exists() is run_cluster_identification
    assert (main_dir / "cos_angle_clusters").exists() is run_cluster_identification
    assert (main_dir / "intensity_clusters.json").is_file()
    assert (main_dir / "cos_angle_clusters.json").is_file()
    assert (main_dir / "xia2.cluster_analysis.log").is_file()
    assert (main_dir / "xia2.cluster_analysis.html").is_file()


@pytest.mark.parametrize(
    "clusters,params,expected",
    [
        (data_1, params_1, []),
        (data_2, params_2, []),
        (data_2, params_2_5, ["cluster_1", "cluster_2"]),
        (data_3, params_3, ["cluster_4", "cluster_5"]),
        (data_4, params_4, ["cluster_3", "cluster_4", "cluster_6", "cluster_7"]),
    ],
)
def test_interesting_cluster_algorithm(clusters, params, expected):
    (
        file_data,
        list_of_clusters,
    ) = MultiCrystalAnalysis.interesting_cluster_identification(clusters, params)

    assert list_of_clusters == expected
