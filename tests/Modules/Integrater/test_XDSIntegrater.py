from __future__ import annotations

import os
import sys
from unittest import mock

import pytest
from dxtbx.model import ExperimentList
from iotbx.reflection_file_reader import any_reflection_file

from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.Indexer.XDSIndexer import XDSIndexer
from xia2.Modules.Integrater.XDSIntegrater import XDSIntegrater
from xia2.Modules.Refiner.XDSRefiner import XDSRefiner
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XSample import XSample
from xia2.Schema.XSweep import XSweep
from xia2.Schema.XWavelength import XWavelength


def _exercise_xds_integrater(dials_data, tmp_path):
    PhilIndex.params.xia2.settings.multiprocessing.nproc = 1

    template = dials_data("centroid_test_data", pathlib=True) / "centroid_####.cbf"

    indexer = XDSIndexer()
    indexer.set_working_directory(os.fspath(tmp_path))

    experiments = ExperimentList.from_templates([template])
    imageset = experiments.imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    cryst = XCrystal("CRYST1", None)
    wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())
    samp = XSample("X1", cryst)
    directory, image = os.path.split(imageset.get_path(1))
    sweep = XSweep("SWEEP1", wav, samp, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)

    refiner = XDSRefiner()
    refiner.set_working_directory(os.fspath(tmp_path))
    refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)
    # refiner.refine()

    integrater = XDSIntegrater()
    integrater.set_working_directory(os.fspath(tmp_path))
    integrater.setup_from_image(imageset.get_path(1))
    integrater.set_integrater_refiner(refiner)
    integrater.set_integrater_sweep(sweep)
    integrater.integrate()

    integrater_intensities = integrater.get_integrater_intensities()
    assert os.path.exists(integrater_intensities)
    reader = any_reflection_file(integrater_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert mtz_object.n_reflections() == pytest.approx(1409, abs=12)
    assert mtz_object.column_labels() == [
        "H",
        "K",
        "L",
        "M_ISYM",
        "BATCH",
        "I",
        "SIGI",
        "FRACTIONCALC",
        "XDET",
        "YDET",
        "ROT",
        "LP",
        "FLAG",
    ]

    corrected_intensities = integrater.get_integrater_corrected_intensities()
    assert os.path.exists(corrected_intensities)
    reader = any_reflection_file(corrected_intensities)
    assert reader.file_type() == "xds_ascii"
    ma = reader.as_miller_arrays(merge_equivalents=False)[0]
    assert ma.size() == pytest.approx(1409, abs=30)

    assert integrater.get_integrater_wedge() == (1, 9)
    assert integrater.get_integrater_cell() == pytest.approx(
        (42.175, 42.175, 39.652, 90, 90, 90), abs=1
    )
    assert integrater.get_integrater_mosaic_min_mean_max() == pytest.approx(
        (0.187, 0.187, 0.187), abs=0.1
    )

    # test serialization of integrater
    json_str = integrater.as_json()
    # print(json_str)
    integrater2 = XDSIntegrater.from_json(string=json_str)
    integrater2.set_integrater_sweep(sweep, reset=False)
    integrater2_intensities = integrater.get_integrater_intensities()
    assert integrater2_intensities == integrater_intensities

    integrater2.set_integrater_finish_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert mtz_object.n_reflections() == pytest.approx(1409, abs=12)

    integrater2.set_integrater_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert mtz_object.n_reflections() == pytest.approx(1413, abs=12)

    integrater2.set_integrater_prepare_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert mtz_object.n_reflections() == pytest.approx(1420, abs=20)


def test_xds_integrater_serial(ccp4, xds, dials_data, run_in_tmp_path):
    with mock.patch.object(sys, "argv", []):
        _exercise_xds_integrater(dials_data, run_in_tmp_path)
