from __future__ import absolute_import, division, print_function

from xia2.command_line.delta_cc_half import run
from xia2.Modules.DeltaCcHalf import DeltaCcHalf


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
    mocker.spy(DeltaCcHalf, "get_table")
    with tmpdir.as_cwd():
        run(
            [
                data_dir.join("AUTOMATIC_DEFAULT_scaled_unmerged.mtz").strpath,
                "group_size=10",
            ]
        )
        assert DeltaCcHalf.get_table.return_value == [
            ["Dataset", "Batches", u"Delta CC\xbd", u"\u03c3"],
            ["0", "51 to 60", " 0.004", "-1.73"],
            ["0", "61 to 70", " 0.005", "-1.38"],
            ["0", "31 to 40", " 0.006", "-0.28"],
            ["0", "1 to 10", " 0.006", " 0.22"],
            ["0", "21 to 30", " 0.006", " 0.28"],
            ["0", "41 to 50", " 0.006", " 0.31"],
            ["0", "11 to 20", " 0.006", " 0.36"],
            ["0", "81 to 90", " 0.007", " 0.78"],
            ["0", "71 to 80", " 0.007", " 1.44"],
        ]
        assert tmpdir.join("delta_cc_hist.png").check()
        assert tmpdir.join("normalised_scores.png").check()
