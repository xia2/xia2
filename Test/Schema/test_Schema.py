import mock
import sys

from xia2.Schema import load_imagesets


def test_load_imageset(dials_data, tmp_path):

    with mock.patch.object(sys, "argv", []):

        for j in range(1, 46):
            if j == 23:
                continue
            tmp_path.joinpath(f"insulin_1_{j:03d}.img").symlink_to(
                dials_data("insulin").join(f"insulin_1_{j:03d}.img")
            )

        imagesets = load_imagesets("insulin_1_###.img", str(tmp_path))
        assert len(imagesets) == 2
        assert tuple(map(len, imagesets)) == (22, 22)
