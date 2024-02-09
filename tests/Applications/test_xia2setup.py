from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from xia2.Handlers.XInfo import XInfo


@pytest.fixture
def insulin_with_missing_image(dials_data, tmp_path):
    for j in range(1, 46):
        if j == 23:
            continue
        try:
            tmp_path.joinpath(f"insulin_1_{j:03d}.img").symlink_to(
                dials_data("insulin", pathlib=True) / f"insulin_1_{j:03d}.img"
            )
        except OSError:
            shutil.copy(
                dials_data("insulin", pathlib=True) / f"insulin_1_{j:03d}.img", tmp_path
            )
    return tmp_path / "insulin_1_###.img"


def test_write_xinfo_insulin_with_missing_image(insulin_with_missing_image, tmp_path):
    cmd = "xia2.setup"
    if os.name == "nt":
        cmd += ".bat"
    result = subprocess.run(
        [
            cmd,
            f"image={insulin_with_missing_image.parent.joinpath('insulin_1_001.img')}",
        ],
        env={"CCP4": str(tmp_path), **os.environ},
        cwd=tmp_path,
    )
    assert not result.returncode
    assert not result.stderr
    xinfo = tmp_path / "automatic.xinfo"
    assert xinfo.is_file()
    x = XInfo(xinfo)
    assert len(x.get_crystals()["DEFAULT"]["sweeps"]) == 2
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP1"]["start_end"] == [1, 22]
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP2"]["start_end"] == [24, 45]


def test_write_xinfo_template_missing_images(insulin_with_missing_image, tmp_path):
    cmd = "xia2.setup"
    if os.name == "nt":
        cmd += ".bat"
    result = subprocess.run(
        [
            cmd,
            f"image={insulin_with_missing_image.parent.joinpath('insulin_1_001.img:1:22')}",
            "read_all_image_headers=False",
        ],
        env={"CCP4": str(tmp_path), **os.environ},
        cwd=tmp_path,
    )
    assert not result.returncode
    assert not result.stderr
    xinfo = tmp_path / "automatic.xinfo"
    assert xinfo.is_file()
    x = XInfo(xinfo)
    assert len(x.get_crystals()["DEFAULT"]["sweeps"]) == 1
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP1"]["start_end"] == [1, 22]


def test_write_xinfo_split_sweep(dials_data, tmp_path):
    cmd = "xia2.setup"
    if os.name == "nt":
        cmd += ".bat"
    result = subprocess.run(
        [
            cmd,
            f"image={dials_data('insulin', pathlib=True) / 'insulin_1_001.img:1:22'}",
            f"image={dials_data('insulin', pathlib=True) / 'insulin_1_001.img:23:45'}",
            "read_all_image_headers=False",
        ],
        env={"CCP4": str(tmp_path), **os.environ},
        cwd=tmp_path,
    )
    assert not result.returncode
    assert not result.stderr
    xinfo = tmp_path / "automatic.xinfo"
    assert xinfo.is_file()
    x = XInfo(xinfo)
    assert len(x.get_crystals()["DEFAULT"]["sweeps"]) == 2
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP1"]["start_end"] == [1, 22]
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP2"]["start_end"] == [23, 45]


def test_write_xinfo_unroll(dials_data, tmp_path):
    # This test partially exercises the fix to https://github.com/xia2/xia2/issues/498 with a different syntax
    cmd = "xia2.setup"
    if os.name == "nt":
        cmd += ".bat"
    result = subprocess.run(
        [
            cmd,
            f"image={dials_data('insulin', pathlib=True) / 'insulin_1_001.img:1:45:15'}",
            "read_all_image_headers=False",
        ],
        env={"CCP4": str(tmp_path), **os.environ},
        cwd=tmp_path,
    )
    assert not result.returncode
    assert not result.stderr
    xinfo = tmp_path / "automatic.xinfo"
    assert xinfo.is_file()
    x = XInfo(xinfo)
    assert len(x.get_crystals()["DEFAULT"]["sweeps"]) == 3
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP1"]["start_end"] == [1, 15]
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP2"]["start_end"] == [16, 30]
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP3"]["start_end"] == [31, 45]
