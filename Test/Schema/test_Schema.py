import mock
import pytest
import sys
from importlib import reload

from dxtbx.model import ExperimentList
from xia2.Schema import load_imagesets, load_reference_geometries, compare_geometries


@pytest.fixture
def insulin_with_missing_image(dials_data, tmp_path):
    for j in range(1, 46):
        if j == 23:
            continue
        tmp_path.joinpath(f"insulin_1_{j:03d}.img").symlink_to(
            dials_data("insulin").join(f"insulin_1_{j:03d}.img")
        )
    return tmp_path.joinpath("insulin_1_###.img")


def test_load_imageset(insulin_with_missing_image):
    with mock.patch.object(sys, "argv", []):
        # Force reload of CommandLine singleton object to ensure it is clean
        import xia2.Handlers.CommandLine

        reload(xia2.Handlers.CommandLine)
        imagesets = load_imagesets(
            insulin_with_missing_image.name, str(insulin_with_missing_image.parent)
        )
        assert len(imagesets) == 2
        assert tuple(map(len, imagesets)) == (22, 22)


def test_load_imageset_template_missing_images(insulin_with_missing_image):
    # exercise load_imageset in combination read_all_image_headers=False with a missing
    # image which is outside the image range specified on the command line
    template = insulin_with_missing_image.name
    directory = insulin_with_missing_image.parent
    with mock.patch.object(
        sys,
        "argv",
        [
            f"image={directory.joinpath('insulin_1_001.img:1:22')}",
            "read_all_image_headers=False",
        ],
    ):
        # Force reload of CommandLine singleton object with the parameters above
        import xia2.Handlers.CommandLine

        reload(xia2.Handlers.CommandLine)
        imagesets = load_imagesets(template, str(directory))
        assert len(imagesets) == 1
        assert imagesets[0].get_array_range() == (0, 22)


def test_load_imageset_split_sweep(dials_data, run_in_tmpdir):
    directory = dials_data("insulin")
    with mock.patch.object(
        sys,
        "argv",
        [
            f"image={directory.join('insulin_1_001.img:1:22')}",
            f"image={directory.join('insulin_1_001.img:23:45')}",
            "read_all_image_headers=False",
        ],
    ):
        # Force reload of CommandLine singleton object with the parameters above
        import xia2.Handlers.CommandLine

        reload(xia2.Handlers.CommandLine)
        imagesets = load_imagesets(directory.join("insulin_1_###.img"), str(directory))
        assert len(imagesets) == 2
        assert imagesets[0].get_array_range() == (0, 22)
        assert imagesets[1].get_array_range() == (22, 45)


def test_load_reference_geometries(dials_data):
    """
    Test `xia2.Schema.load_reference_geometries`.

    Test the function that finds the set of unique instrument models from a list
    of experiment list files.

    There are eight input instrument models, of which only two are unique.
    """
    files = ["scaled_20_25.expt", "scaled_30.expt", "scaled_35.expt"]
    files = [(dials_data("l_cysteine_4_sweeps_scaled") / f).strpath for f in files]
    files.append((dials_data("l_cysteine_dials_output") / "indexed.expt").strpath)

    num_input = sum(len(ExperimentList.from_file(f, check_format=False)) for f in files)
    assert num_input == 8, "Expected to find eight experiments, one for each sweep."

    unique_geometries = load_reference_geometries(files)
    assert len(unique_geometries) == 2, "Expected to find two unique instrument models."

    detectors = (geom["detector"] for geom in unique_geometries)
    assert not compare_geometries(*detectors), "Unique detectors cannot be equivalent."
