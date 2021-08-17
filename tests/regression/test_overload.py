import procrunner


def test(dials_data, tmp_path):
    images = list(dials_data("centroid_test_data", pathlib=True).glob("centroid*.cbf"))

    result = procrunner.run(["xia2.overload"] + images, working_directory=tmp_path)
    assert not result.returncode and not result.stderr
    assert (tmp_path / "overload.json").is_file()
