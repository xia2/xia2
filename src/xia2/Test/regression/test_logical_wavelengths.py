import procrunner


def split_xinfo(data_dir, tmpdir):
    split_xinfo_template = """/
BEGIN PROJECT PNAME
BEGIN CRYSTAL XNAME

BEGIN WAVELENGTH NATIVE1
WAVELENGTH 0.979500
END WAVELENGTH NATIVE1

BEGIN WAVELENGTH NATIVE2
WAVELENGTH 0.979500
END WAVELENGTH NATIVE2

BEGIN WAVELENGTH NATIVE3
WAVELENGTH 0.979500
END WAVELENGTH NATIVE3

BEGIN SWEEP SWEEP1
WAVELENGTH NATIVE1
DIRECTORY {0}
IMAGE X4_wide_M1S4_2_0001.cbf
START_END 1 30
BEAM 219.84 212.65
END SWEEP SWEEP1

BEGIN SWEEP SWEEP2
WAVELENGTH NATIVE2
DIRECTORY {0}
IMAGE X4_wide_M1S4_2_0001.cbf
START_END 31 60
BEAM 219.84 212.65
END SWEEP SWEEP2

BEGIN SWEEP SWEEP3
WAVELENGTH NATIVE3
DIRECTORY {0}
IMAGE X4_wide_M1S4_2_0001.cbf
START_END 61 90
BEAM 219.84 212.65
END SWEEP SWEEP3

END CRYSTAL XNAME
END PROJECT PNAME
"""
    xinfo_file = tmpdir / "split.xinfo"
    xinfo_file.write(
        split_xinfo_template.format(data_dir.strpath.replace("\\", "\\\\"))
    )
    return xinfo_file.strpath


def test_logical_wavelength_default(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "nproc=2",
        "njob=3",
        "mode=parallel",
        "trust_beam_centre=True",
        "xinfo=%s" % split_xinfo(dials_data("x4wide"), tmpdir),
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    assert result.returncode == 0


def test_logical_wavelength_3dii(regression_test, dials_data, tmpdir, ccp4):
    command_line = [
        "xia2",
        "pipeline=3dii",
        "nproc=2",
        "njob=3",
        "mode=parallel",
        "trust_beam_centre=True",
        "xinfo=%s" % split_xinfo(dials_data("x4wide"), tmpdir),
    ]
    result = procrunner.run(command_line, working_directory=tmpdir)
    assert result.returncode == 0
