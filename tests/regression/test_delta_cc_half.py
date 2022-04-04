from __future__ import annotations

import itertools
import os

import pytest_mock

from xia2.cli.delta_cc_half import run
from xia2.Modules.DeltaCcHalf import DeltaCcHalf


def test_from_experiments_reflections(dials_data, tmpdir, capsys, mocker):
    data_dir = dials_data("l_cysteine_4_sweeps_scaled", pathlib=True)
    input_files = sorted(
        itertools.chain(data_dir.glob("scaled_*.expt"), data_dir.glob("scaled_*.refl"))
    )
    mocker.spy(DeltaCcHalf, "get_table")
    with tmpdir.as_cwd():
        run([os.fspath(f) for f in input_files])
        if getattr(pytest_mock, "version", "").startswith("1."):
            rv = DeltaCcHalf.get_table.return_value
        else:
            rv = DeltaCcHalf.get_table.spy_return
        assert rv == [
            ["Dataset", "Batches", "CC½", "ΔCC½", "σ", "Compl. (%)"],
            ["0", "8 to 1795", " 0.995", " 0.000", "-1.11", "94.4"],
            ["3", "5 to 1694", " 0.995", " 0.000", "-0.59", "93.1"],
            ["2", "4 to 1696", " 0.994", " 0.001", " 0.84", "92.3"],
            ["1", "5 to 1694", " 0.994", " 0.001", " 0.85", "94.8"],
        ]

        assert tmpdir.join("delta_cc_hist.png").check()
        assert tmpdir.join("normalised_scores.png").check()


def test_image_groups_from_unmerged_mtz(dials_data, tmpdir, capsys, mocker):
    data_dir = dials_data("x4wide_processed", pathlib=True)
    mocker.spy(DeltaCcHalf, "get_table")
    with tmpdir.as_cwd():
        run(
            [
                os.fspath(data_dir / "AUTOMATIC_DEFAULT_scaled_unmerged.mtz"),
                "group_size=10",
            ]
        )
        if getattr(pytest_mock, "version", "").startswith("1."):
            rv = DeltaCcHalf.get_table.return_value
        else:
            rv = DeltaCcHalf.get_table.spy_return
        assert rv == [
            ["Dataset", "Batches", "CC½", "ΔCC½", "σ", "Compl. (%)"],
            ["0", "11 to 20", " 0.922", " 0.007", "-0.95", "99.4"],
            ["0", "31 to 40", " 0.922", " 0.007", "-0.84", "99.8"],
            ["0", "1 to 10", " 0.921", " 0.007", "-0.67", "99.3"],
            ["0", "21 to 30", " 0.921", " 0.007", "-0.59", "99.8"],
            ["0", "81 to 90", " 0.921", " 0.007", "-0.48", "100.0"],
            ["0", "61 to 70", " 0.920", " 0.008", " 0.17", "99.3"],
            ["0", "71 to 80", " 0.920", " 0.008", " 0.51", "99.9"],
            ["0", "41 to 50", " 0.920", " 0.009", " 0.72", "99.9"],
            ["0", "51 to 60", " 0.918", " 0.010", " 2.13", "99.4"],
        ]
        assert tmpdir.join("delta_cc_hist.png").check()
        assert tmpdir.join("normalised_scores.png").check()
