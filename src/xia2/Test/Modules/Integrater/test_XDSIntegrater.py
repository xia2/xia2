from unittest import mock
import os
import pytest
import sys

from iotbx.reflection_file_reader import any_reflection_file
from dxtbx.model.experiment_list import ExperimentListTemplateImporter

from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.Indexer.XDSIndexer import XDSIndexer
from xia2.Modules.Integrater.XDSIntegrater import XDSIntegrater
from xia2.Modules.Refiner.XDSRefiner import XDSRefiner
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XWavelength import XWavelength
from xia2.Schema.XSweep import XSweep
from xia2.Schema.XSample import XSample


def exercise_xds_integrater(dials_data, tmp_dir, nproc=None):
    if nproc:
        PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

    template = dials_data("insulin").join("insulin_1_###.img").strpath

    indexer = XDSIndexer()
    indexer.set_working_directory(tmp_dir)

    importer = ExperimentListTemplateImporter([template])
    experiments = importer.experiments
    imageset = experiments.imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    cryst = XCrystal("CRYST1", None)
    wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())
    samp = XSample("X1", cryst)
    directory, image = os.path.split(imageset.get_path(1))
    sweep = XSweep("SWEEP1", wav, samp, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)

    refiner = XDSRefiner()
    refiner.set_working_directory(tmp_dir)
    refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)
    # refiner.refine()

    integrater = XDSIntegrater()
    integrater.set_working_directory(tmp_dir)
    integrater.setup_from_image(imageset.get_path(1))
    integrater.set_integrater_refiner(refiner)
    integrater.set_integrater_sweep(sweep)
    integrater.integrate()

    integrater_intensities = integrater.get_integrater_intensities()
    assert os.path.exists(integrater_intensities)
    reader = any_reflection_file(integrater_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert mtz_object.n_reflections() == pytest.approx(50000, abs=400)
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
    assert ma.size() == pytest.approx(50000, abs=400)

    assert integrater.get_integrater_wedge() == (1, 45)
    assert integrater.get_integrater_cell() == pytest.approx(
        (78.066, 78.066, 78.066, 90, 90, 90), abs=1
    )
    assert integrater.get_integrater_mosaic_min_mean_max() == pytest.approx(
        (0.180, 0.180, 0.180), abs=1e-1
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
    assert mtz_object.n_reflections() == pytest.approx(50000, abs=400)

    integrater2.set_integrater_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert mtz_object.n_reflections() == pytest.approx(50000, abs=450)

    integrater2.set_integrater_prepare_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert mtz_object.n_reflections() == pytest.approx(50100, abs=400)


def test_xds_integrater_serial(regression_test, ccp4, xds, dials_data, run_in_tmpdir):
    with mock.patch.object(sys, "argv", []):
        exercise_xds_integrater(dials_data, run_in_tmpdir.strpath, nproc=1)
