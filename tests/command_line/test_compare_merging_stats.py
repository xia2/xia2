import os
import pytest

from xia2.cli import compare_merging_stats


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


@pytest.mark.parametrize(
    "anomalous",
    [
        False,
        True,
    ],
)
def test_compare_merging_stats(anomalous, blend_mtz_files, run_in_tmpdir):
    compare_merging_stats.run(blend_mtz_files + [f"anomalous={anomalous}"])
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


def test_compare_merging_stats_d_min_d_max(blend_mtz_files, run_in_tmpdir):
    results = compare_merging_stats.run(blend_mtz_files + ["d_min=2.5", "d_max=50"])
    for expected_file in expected_files:
        assert os.path.exists(expected_file)
    for result in results:
        assert result.overall.d_min > 2.5
        assert result.overall.d_max < 50


def test_compare_merging_stats_small_multiples(dials_data, run_in_tmpdir):
    data_dir = dials_data("blend_tutorial")
    blend_mtz_files = [
        data_dir.join("dataset_%03i.mtz" % (i + 1)).strpath for i in range(15)
    ]
    compare_merging_stats.run(blend_mtz_files + ["small_multiples=True"])
    for expected_file in expected_files:
        assert os.path.exists(expected_file)
