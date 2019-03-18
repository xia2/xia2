from __future__ import absolute_import, division, print_function

import os
import sys

import mock
import pytest
from libtbx.test_utils import approx_equal


def exercise_mosflm_integrater(dials_data, tmp_dir, nproc):
    from xia2.Handlers.Phil import PhilIndex

    PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

    template = dials_data("insulin").join("insulin_1_###.img").strpath

    # otherwise if this test is running multiple times simultaneously two mosflm
    # processes try to write to the same genfile
    os.environ["CCP4_SCR"] = tmp_dir

    from xia2.Modules.Indexer.MosflmIndexer import MosflmIndexer
    from xia2.Modules.Integrater.MosflmIntegrater import MosflmIntegrater
    from dxtbx.datablock import DataBlockTemplateImporter

    indexer = MosflmIndexer()
    indexer.set_working_directory(tmp_dir)
    importer = DataBlockTemplateImporter([template])
    datablocks = importer.datablocks
    imageset = datablocks[0].extract_imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    from xia2.Schema.XCrystal import XCrystal
    from xia2.Schema.XWavelength import XWavelength
    from xia2.Schema.XSweep import XSweep
    from xia2.Schema.XSample import XSample

    cryst = XCrystal("CRYST1", None)
    wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())
    samp = XSample("X1", cryst)
    directory, image = os.path.split(imageset.get_path(1))
    sweep = XSweep("SWEEP1", wav, samp, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)

    from xia2.Modules.Refiner.MosflmRefiner import MosflmRefiner

    refiner = MosflmRefiner()
    refiner.set_working_directory(tmp_dir)
    refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)

    nref_error = 500

    integrater = MosflmIntegrater()
    integrater.set_working_directory(tmp_dir)
    integrater.setup_from_image(imageset.get_path(1))
    integrater.set_integrater_refiner(refiner)
    # integrater.set_integrater_indexer(indexer)
    integrater.set_integrater_sweep(sweep)
    integrater.integrate()

    integrater_intensities = integrater.get_integrater_intensities()
    assert os.path.exists(integrater_intensities)
    from iotbx.reflection_file_reader import any_reflection_file

    reader = any_reflection_file(integrater_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert (
        abs(mtz_object.n_reflections() - 81116) < nref_error
    ), mtz_object.n_reflections()
    assert mtz_object.column_labels() == [
        "H",
        "K",
        "L",
        "M_ISYM",
        "BATCH",
        "I",
        "SIGI",
        "IPR",
        "SIGIPR",
        "FRACTIONCALC",
        "XDET",
        "YDET",
        "ROT",
        "WIDTH",
        "LP",
        "MPART",
        "FLAG",
        "BGPKRATIOS",
    ]

    assert integrater.get_integrater_wedge() == (1, 45)
    assert approx_equal(
        integrater.get_integrater_cell(),
        (78.014, 78.014, 78.014, 90.0, 90.0, 90.0),
        eps=1e-2,
    )

    # test serialization of integrater
    json_str = integrater.as_json()
    # print json_str
    integrater2 = MosflmIntegrater.from_json(string=json_str)
    integrater2.set_integrater_sweep(sweep, reset=False)
    integrater2_intensities = integrater.get_integrater_intensities()
    assert integrater2_intensities == integrater_intensities

    integrater2.set_integrater_finish_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert (
        abs(mtz_object.n_reflections() - 81116) < nref_error
    ), mtz_object.n_reflections()

    integrater2.set_integrater_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert (
        abs(mtz_object.n_reflections() - 81116) < nref_error
    ), mtz_object.n_reflections()

    integrater2.set_integrater_prepare_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert (
        abs(mtz_object.n_reflections() - 81116) < nref_error
    ), mtz_object.n_reflections()


def test_mosflm_integrater_serial(regression_test, ccp4, dials_data, run_in_tmpdir):
    with mock.patch.object(sys, "argv", []):
        exercise_mosflm_integrater(dials_data, run_in_tmpdir.strpath, nproc=1)


def test_mosflm_integrater_parallel(regression_test, ccp4, dials_data, run_in_tmpdir):
    with mock.patch.object(sys, "argv", []):
        exercise_mosflm_integrater(dials_data, run_in_tmpdir.strpath, nproc=2)
