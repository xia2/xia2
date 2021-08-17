import pytest

from xia2.Applications.xia2_main import check_hdf5_master_files


def test_check_hdf5_master_files(dials_data):

    master = dials_data("vmxi_thaumatin").join("image_15799_master.h5").strpath
    data = dials_data("vmxi_thaumatin").join("image_15799_data_000001.h5").strpath

    with pytest.raises(SystemExit):
        check_hdf5_master_files([data])

    check_hdf5_master_files([master])
