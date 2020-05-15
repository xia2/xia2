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
            ["0", "8 to 1795", "-0.002", "-1.32"],
            ["3", "5 to 1694", "-0.001", "-0.15"],
            ["1", "5 to 1694", "-0.001", " 0.44"],
            ["2", "4 to 1696", "-0.001", " 1.02"],
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
            ["0", "51 to 60", " 0.005", "-1.67"],
            ["0", "61 to 70", " 0.005", "-1.32"],
            ["0", "31 to 40", " 0.006", "-0.38"],
            ["0", "21 to 30", " 0.006", "-0.04"],
            ["0", "1 to 10", " 0.006", " 0.17"],
            ["0", "11 to 20", " 0.006", " 0.30"],
            ["0", "41 to 50", " 0.006", " 0.63"],
            ["0", "81 to 90", " 0.007", " 0.85"],
            ["0", "71 to 80", " 0.007", " 1.45"],
        ]
        assert tmpdir.join("delta_cc_hist.png").check()
        assert tmpdir.join("normalised_scores.png").check()
