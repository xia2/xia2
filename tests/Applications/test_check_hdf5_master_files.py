from __future__ import annotations

import pytest

from xia2.Applications.xia2_main import check_hdf5_master_files


def test_check_hdf5_master_files_works_on_master_file(dials_data):
    master = dials_data("vmxi_thaumatin", pathlib=True) / "image_15799_master.h5"
    check_hdf5_master_files([master])


def test_check_hdf5_master_files_fails_on_data_file(dials_data):
    data = dials_data("vmxi_thaumatin", pathlib=True) / "image_15799_data_000001.h5"
    with pytest.raises(SystemExit):
        check_hdf5_master_files([data])
