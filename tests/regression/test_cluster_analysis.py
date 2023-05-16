from __future__ import annotations

import os

# import pathlib
import subprocess

# import pytest

# from xia2.Modules.MultiCrystalAnalysis import MultiCrystalReport


def test_serial_data(dials_data, tmp_path):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    expt_int = os.fspath(ssx / "integrated.expt")
    refl_int = os.fspath(ssx / "integrated.refl")
    args_generate_scaled = ["xia2.ssx_reduce", expt_int, refl_int]
    expt_scaled = os.fspath(tmp_path / "DataFiles" / "scaled.expt")
    refl_scaled = os.fspath(tmp_path / "DataFiles" / "scaled.refl")
    args_test_clustering = [
        "xia2.cluster_analysis",
        "min_cluster_size=2",
        expt_scaled,
        refl_scaled,
    ]
    result_generate_scaled = subprocess.run(
        args_generate_scaled, cwd=tmp_path, capture_output=True
    )
    assert not result_generate_scaled.returncode and not result_generate_scaled.stderr
    result = subprocess.run(args_test_clustering, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path)


def test_rotation_data(dials_data, tmp_path):
    rot = dials_data("vmxi_proteinase_k_sweeps", pathlib=True)
    expt_1 = os.fspath(rot / "experiments_0.expt")
    expt_2 = os.fspath(rot / "experiments_1.expt")
    expt_3 = os.fspath(rot / "experiments_2.expt")
    expt_4 = os.fspath(rot / "experiments_3.expt")
    refl_1 = os.fspath(rot / "reflections_0.refl")
    refl_2 = os.fspath(rot / "reflections_1.refl")
    refl_3 = os.fspath(rot / "reflections_2.refl")
    refl_4 = os.fspath(rot / "reflections_3.refl")
    expt_scaled = os.fspath(tmp_path / "scaled.expt")
    refl_scaled = os.fspath(tmp_path / "scaled.refl")
    args_multiplex = [
        "xia2.multiplex",
        expt_1,
        refl_1,
        expt_2,
        refl_2,
        expt_3,
        refl_3,
        expt_4,
        refl_4,
    ]
    args_clustering = [
        "xia2.cluster_analysis",
        "min_cluster_size=2",
        expt_scaled,
        refl_scaled,
    ]
    result_multiplex = subprocess.run(args_multiplex, cwd=tmp_path, capture_output=True)
    assert not result_multiplex.returncode and not result_multiplex.stderr
    result = subprocess.run(args_clustering, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path)


def check_output(main_dir):
    assert (main_dir / "cc_clusters").exists()
    assert (main_dir / "cos_angle_clusters").exists()
    assert (main_dir / "intensity_clusters.json").is_file()
    assert (main_dir / "cos_angle_clusters.json").is_file()
    assert (main_dir / "xia2.multi_crystal_analysis.log").is_file()
    assert (main_dir / "xia2.cluster_analysis.html").is_file()


# @pytest.mark.parametrize(("clusters", "expected_interesting"), [({"Cluster Number": ['cluster_1', 'cluster_2', 'cluster_3'], "Height": [], "Datasets": []},'BLAH'),({"Cluster Number": [], "Height": [], "Datasets": []},'BLAH'),({"Cluster Number": [], "Height": [], "Datasets": []},'BLAH')])
# def check_interesting_cluster_algorithm(clusters, expected_interesting):
