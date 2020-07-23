import mock
import os
import sys
from importlib import reload

from xia2.Handlers.XInfo import XInfo


def test_write_xinfo_split_sweep(dials_data, tmp_path):
    # This test partially exercises the fix to https://github.com/xia2/xia2/issues/498
    xinfo = tmp_path.joinpath("test.xinfo")

    with mock.patch.object(
        sys,
        "argv",
        [
            f"image={dials_data('insulin').join('insulin_1_001.img:1:22')}",
            f"image={dials_data('insulin').join('insulin_1_001.img:23:45')}",
            "read_all_image_headers=False",
        ],
    ):
        # Force reload of CommandLine singleton object with the parameters above
        import xia2.Handlers.CommandLine

        reload(xia2.Handlers.CommandLine)

        template = xia2.Handlers.CommandLine.CommandLine.get_template()
        directories = [os.path.split(p) for p in template]

        from xia2.Applications.xia2setup import write_xinfo

        write_xinfo(
            xinfo, directories, template=template,
        )
        assert xinfo.exists()
        x = XInfo(xinfo)
        assert len(x.get_crystals()["DEFAULT"]["sweeps"]) == 2
        x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP1"]["start_end"] == [1, 22]
        x.get_crystals()["DEFAULT"]["sweeps"]["SWEEP2"]["start_end"] == [23, 45]