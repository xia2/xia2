import procrunner

from xia2.Handlers.XInfo import XInfo


def test_write_xinfo_split_sweep(dials_data, tmpdir):
    result = procrunner.run(
        [
            "xia2.setup",
            f"image={dials_data('insulin').join('insulin_1_001.img:1:22')}",
            f"image={dials_data('insulin').join('insulin_1_001.img:23:45')}",
            "read_all_image_headers=False",
        ],
        working_directory=tmpdir,
        environment_override={"CCP4": tmpdir},
    )
    assert not result.returncode
    assert not result.stderr
    xinfo = tmpdir.join("automatic.xinfo")
    assert xinfo.check(file=1)
    x = XInfo(xinfo)
    assert len(x.get_crystals()["DEFAULT"]["sweeps"]) == 2
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP1"]["start_end"] == [1, 22]
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP2"]["start_end"] == [23, 45]


def test_write_xinfo_unroll(dials_data, tmpdir):
    # This test partially exercises the fix to https://github.com/xia2/xia2/issues/498 with a different syntax
    result = procrunner.run(
        [
            "xia2.setup",
            f"image={dials_data('insulin').join('insulin_1_001.img:1:45:15')}",
            "read_all_image_headers=False",
        ],
        working_directory=tmpdir,
        environment_override={"CCP4": tmpdir},
    )
    assert not result.returncode
    assert not result.stderr
    xinfo = tmpdir.join("automatic.xinfo")
    assert xinfo.check(file=1)
    x = XInfo(xinfo)
    assert len(x.get_crystals()["DEFAULT"]["sweeps"]) == 3
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP1"]["start_end"] == [1, 15]
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP2"]["start_end"] == [16, 30]
    assert x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP3"]["start_end"] == [31, 45]
