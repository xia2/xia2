from __future__ import absolute_import, division, print_function

import procrunner


def test(dials_data, tmpdir):
    images = dials_data("centroid_test_data").listdir("centroid*.cbf")

    result = procrunner.run(["xia2.overload"] + images, working_directory=tmpdir)
    assert not result.returncode and not result.stderr
    assert tmpdir.join("overload.json").check()
