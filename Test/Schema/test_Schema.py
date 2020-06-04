import mock
import sys

from xia2.Schema import load_imagesets


def test_load_imageset(dials_data, tmp_path):

    with mock.patch.object(sys, "argv", []):

        for j in range(1, 46):
            if j == 23:
                continue
            tmp_path.joinpath("insulin_1_%03d.img" % j).symlink_to(
                dials_data("insulin").join("insulin_1_%03d.img" % j)
            )

        imagesets = load_imagesets("insulin_1_###.img", str(tmp_path))
        assert len(imagesets) == 2
        assert tuple(map(len, imagesets)) == (22, 22)
