from __future__ import annotations

import warnings

import pytest

from xia2.Modules.Analysis import phil_scope
from xia2.Modules.Report import Report
from xia2.XIA2Version import VersionNumber


@pytest.fixture(scope="session")
def report(dials_data, tmp_path_factory):
    data_dir = dials_data("pychef", pathlib=True)
    mtz = data_dir / "insulin_dials_scaled_unmerged.mtz"
    tmp_path = tmp_path_factory.mktemp("test_report")

    params = phil_scope.extract()
    params.batch = []
    params.dose.batch = []
    return Report.from_unmerged_mtz(mtz, params, report_dir=tmp_path)


def test_multiplicity_plots(report, tmp_path):
    multiplicity_plots = report.multiplicity_plots(dest_path=tmp_path)
    assert set(multiplicity_plots) == {
        "multiplicity_h",
        "multiplicity_k",
        "multiplicity_l",
    }


def test_symmetry_table_html(report):
    assert (
        report.symmetry_table_html()
        == """
  <p>
    <b>Unit cell:</b> I 2 3 (No. 197)
    <br>
    <b>Space group:</b> (78.1047, 78.1047, 78.1047, 90, 90, 90)
  </p>
"""
    )


def test_xtriage(report):
    xtriage_report = report.xtriage_report()
    assert len(xtriage_report) == 3
    assert set(xtriage_report[0][0]) == {"text", "summary", "header", "level"}


def test_batch_dependent_plots(report):
    plots = report.batch_dependent_plots()
    assert set(plots) == {"i_over_sig_i_vs_batch", "scale_rmerge_vs_batch"}
    assert plots["scale_rmerge_vs_batch"]["data"][0]["x"] == list(range(1, 46))
    assert plots["i_over_sig_i_vs_batch"]["data"][0]["x"] == list(range(1, 46))


def test_resolution_plots_and_stats(report):
    (
        overall_stats_table,
        merging_stats_table,
        stats_plots,
    ) = report.resolution_plots_and_stats()
    assert len(overall_stats_table) == 11
    assert overall_stats_table[0] == [
        "",
        "Overall",
        "Low resolution",
        "High resolution",
    ]
    assert report.n_bins == 20
    assert len(merging_stats_table) == 21
    assert merging_stats_table[0] == [
        "Resolution (\xc5)",
        "N(obs)",
        "N(unique)",
        "Multiplicity",
        "Completeness",
        "Mean I",
        "Mean I/\u03c3(I)",
        "R<sub>merge</sub>",
        "R<sub>meas</sub>",
        "R<sub>pim</sub>",
        "R<sub>anom</sub>",
        "CC<sub>\xbd</sub>",
        "CC<sub>ano</sub>",
    ]
    assert merging_stats_table[1] == [
        "24.70 - 4.36",
        2765,
        543,
        "5.09",
        "96.11",
        "7201.0",
        "72.9",
        "0.027",
        "0.030",
        "0.013",
        "0.046",
        "0.998*",
        "0.598*",
    ]
    assert set(stats_plots) == {
        "multiplicity_vs_resolution",
        "completeness",
        "r_pim",
        "i_over_sig_i",
        "cc_one_half",
    }


def test_deprecated_resolution_bins(dials_data, tmp_path, caplog):
    """
    Test the mechanism for deprecating the 'report.resolution_bins' paramter.

    The parameter 'xia2.settings.report.resolution_bins' is deprecated.  By default,
    it is not set, and the value of 'xia2.settings.merging_statistics.n_bins' is used
    instead.  For the duration of the deprecation period, we should continue to support
    the case where the user sets 'resolution_bins', allowing their preference to take
    precedence over 'n_bins', but show a warning.  The deprecated option will be
    removed in version 3.10.

    From version 3.10, running this test will produce a warning, as a reminder to
    remove both the 'resolution_bins' parameter and this test itself.
    """
    major, minor, *_ = VersionNumber.split(".")
    if tuple(map(int, (major, minor))) > (3, 9):
        warnings.warn(
            "Remove 'report.resolution_bins' parameter and test.", DeprecationWarning
        )

    mtz = dials_data("pychef", pathlib=True) / "insulin_dials_scaled_unmerged.mtz"

    # Test normal behaviour — number of bins is taken from 'n_bins'.  No warning.
    params = phil_scope.extract()
    params.batch = []
    params.dose.batch = []
    Report.from_unmerged_mtz(mtz, params, report_dir=tmp_path)

    assert not caplog.records

    # Test support for deprecated behaviour — 'resolution_bins' is respected.
    # A warning is logged.
    params.resolution_bins = 15
    report = Report.from_unmerged_mtz(mtz, params, report_dir=tmp_path)

    (record,) = caplog.records  # Make sure that there is only one log record.
    assert record.name == "xia2.Modules.Report"
    assert record.levelname == "WARNING"
    assert "'xia2.settings.report.resolution_bins' is deprecated" in record.message

    assert report.n_bins == 15
    (_, merging_stats_table, _) = report.resolution_plots_and_stats()
    assert merging_stats_table[1] == [
        "24.70 - 3.97",
        3672,
        717,
        "5.12",
        "96.76",
        "7772.7",
        "75.3",
        "0.025",
        "0.028",
        "0.012",
        "0.043",
        "0.998*",
        "0.622*",
    ]


def test_intensity_stats_plots(report):
    plots = report.intensity_stats_plots()
    assert set(plots) == {
        "wilson_intensity_plot",
        "multiplicities",
        "second_moments",
        "cumulative_intensity_distribution",
        "l_test",
    }


def test_pychef(report):
    plots = report.pychef_plots()
    assert set(plots) == {
        "rcp_vs_dose",
        "scp_vs_dose",
        "completeness_vs_dose",
        "rd_vs_batch_difference",
    }
