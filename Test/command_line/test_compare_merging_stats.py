from __future__ import absolute_import, division, print_function

import mock
import os
import pytest

import iotbx.merging_statistics

from xia2.command_line import compare_merging_stats


expected_files = [
    "cc_anom.png",
    "cc_one_half.png",
    "cc_one_half_sigma_tau.png",
    "completeness.png",
    "i_over_sigma_mean.png",
    "mean_redundancy.png",
    "r_meas.png",
    "r_merge.png",
    "r_pim.png",
]


@pytest.fixture
def blend_mtz_files(dials_data):
    data_dir = dials_data("blend_tutorial")
    return [
        data_dir.join("dataset_001.mtz").strpath,
        data_dir.join("dataset_002.mtz").strpath,
    ]


def test_compare_merging_stats(blend_mtz_files, run_in_tmpdir):
    compare_merging_stats.run(blend_mtz_files)
    for expected_file in expected_files:
        assert os.path.exists(expected_file)


def test_compare_merging_stats_plot_labels_image_dir(blend_mtz_files, run_in_tmpdir):
    compare_merging_stats.run(
        blend_mtz_files + ["plot_labels=1 2", "image_dir=compare", "size_inches=10,10"]
    )
    for expected_file in expected_files:
        assert os.path.exists(os.path.join("compare", expected_file))


def test_compare_merging_stats_override_space_group(blend_mtz_files, run_in_tmpdir):
    compare_merging_stats.run(blend_mtz_files + ["space_group=P4"])
    for expected_file in expected_files:
        assert os.path.exists(expected_file)


def test_compare_merging_stats_d_min_d_max(blend_mtz_files, run_in_tmpdir, mocker):
    spy = mocker.spy(iotbx.merging_statistics, "dataset_statistics")
    compare_merging_stats.run(blend_mtz_files + ["d_min=2.5", "d_max=50"])
    for expected_file in expected_files:
        assert os.path.exists(expected_file)
    spy.assert_called_with(
        anomalous=False,
        d_max=50.0,
        d_min=2.5,
        eliminate_sys_absent=False,
        i_obs=mock.ANY,
        n_bins=20,
        use_internal_variance=False,
    )


def test_compare_merging_stats_small_multiples(dials_data, run_in_tmpdir, mocker):
    data_dir = dials_data("blend_tutorial")
    blend_mtz_files = [
        data_dir.join("dataset_%03i.mtz" % (i + 1)).strpath for i in range(15)
    ]
    compare_merging_stats.run(blend_mtz_files + ["small_multiples=True"])
    for expected_file in expected_files:
        assert os.path.exists(expected_file)
