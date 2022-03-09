from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def report(dials_data, tmpdir_factory):
    data_dir = dials_data("pychef")
    mtz = data_dir.join("insulin_dials_scaled_unmerged.mtz").strpath
    temp_path = tmpdir_factory.mktemp("test_report")
    with temp_path.as_cwd():
        from xia2.Modules.Analysis import (  # import creates /xia2-debug.txt dropping
            phil_scope,
        )
        from xia2.Modules.Report import Report  # import creates /DEFAULT/ dropping

        params = phil_scope.extract()
        params.batch = []
        params.dose.batch = []
        yield Report.from_unmerged_mtz(mtz, params, report_dir=temp_path.strpath)


def test_multiplicity_plots(report):
    multiplicity_plots = report.multiplicity_plots(dest_path=".")
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
