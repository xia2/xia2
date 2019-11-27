from __future__ import absolute_import, division, print_function

from xia2.command_line.delta_cc_half import run
from xia2.Modules.DeltaCcHalf import DeltaCcHalf, DeltaCcHalfImageGroups


def test_from_experiments_reflections(dials_data, tmpdir, capsys, mocker):
    data_dir = dials_data("l_cysteine_4_sweeps_scaled")
    input_files = data_dir.listdir("scaled_*.refl") + data_dir.listdir("scaled_*.expt")
    input_files = sorted(f.strpath for f in input_files)
    mocker.spy(DeltaCcHalf, "get_table")
    with tmpdir.as_cwd():
        run(input_files)
        assert DeltaCcHalf.get_table.return_value == [
            ["Dataset", "Batches", u"Delta CC\xbd", u"\u03c3"],
            ["0", "8 to 1795", "-0.002", "-1.26"],
            ["3", "5 to 1694", "-0.001", "-0.13"],
            ["1", "5 to 1694", "-0.001", " 0.22"],
            ["2", "4 to 1696", "-0.001", " 1.16"],
        ]
        assert tmpdir.join("delta_cc_hist.png").check()
        assert tmpdir.join("normalised_scores.png").check()


def test_image_groups_from_unmerged_mtz(dials_data, tmpdir, capsys, mocker):
    data_dir = dials_data("x4wide_processed")
    mocker.spy(DeltaCcHalfImageGroups, "get_table")
    with tmpdir.as_cwd():
        run(
            [
                data_dir.join("AUTOMATIC_DEFAULT_scaled_unmerged.mtz").strpath,
                "group_size=10",
            ]
        )
        assert DeltaCcHalfImageGroups.get_table.return_value == [
            ["Dataset", "Batches", u"Delta CC\xbd", u"\u03c3"],
            ["0", "51 to 61", " 0.004", "-1.74"],
            ["0", "61 to 71", " 0.005", "-1.38"],
            ["0", "31 to 41", " 0.006", "-0.27"],
            ["0", "1 to 11", " 0.006", " 0.24"],
            ["0", "21 to 31", " 0.006", " 0.29"],
            ["0", "41 to 51", " 0.006", " 0.32"],
            ["0", "11 to 21", " 0.006", " 0.37"],
            ["0", "81 to 90", " 0.006", " 0.71"],
            ["0", "71 to 81", " 0.007", " 1.46"],
        ]
        assert tmpdir.join("delta_cc_hist.png").check()
        assert tmpdir.join("normalised_scores.png").check()
