from unittest import mock
import os
import pytest
import sys

from iotbx.reflection_file_reader import any_reflection_file
from dials.array_family import flex
from dxtbx.model.experiment_list import ExperimentListTemplateImporter

from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
from xia2.Modules.Integrater.DialsIntegrater import DialsIntegrater
from xia2.Modules.Refiner.DialsRefiner import DialsRefiner
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XWavelength import XWavelength
from xia2.Schema.XSweep import XSweep
from xia2.Schema.XSample import XSample


def exercise_dials_integrater(dials_data, tmp_dir, nproc=None):
    if nproc:
        PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

    template = dials_data("insulin").join("insulin_1_###.img").strpath

    indexer = DialsIndexer()
    indexer.set_working_directory(tmp_dir)
    importer = ExperimentListTemplateImporter([template])
    experiments = importer.experiments
    imageset = experiments.imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    cryst = XCrystal("CRYST1", None)
    wav = XWavelength("WAVE1", cryst, imageset.get_beam().get_wavelength())
    samp = XSample("X1", cryst)
    directory, image = os.path.split(imageset.get_path(1))
    sweep = XSweep("SWEEP1", wav, samp, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)

    refiner = DialsRefiner()
    refiner.set_working_directory(tmp_dir)
    refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)
    # refiner.refine()

    integrater = DialsIntegrater()
    integrater.set_output_format("hkl")
    integrater.set_working_directory(tmp_dir)
    integrater.setup_from_image(imageset.get_path(1))
    integrater.set_integrater_refiner(refiner)
    # integrater.set_integrater_indexer(indexer)
    integrater.set_integrater_sweep(sweep)
    integrater.integrate()

    integrater_intensities = integrater.get_integrater_intensities()
    assert os.path.exists(integrater_intensities)

    reader = any_reflection_file(integrater_intensities)
    assert reader.file_type() == "ccp4_mtz", repr(integrater_intensities)
    mtz_object = reader.file_content()
    expected_reflections = 47623
    assert (
        abs(mtz_object.n_reflections() - expected_reflections) < 300
    ), mtz_object.n_reflections()

    assert mtz_object.column_labels() == [
        "H",
        "K",
        "L",
        "M_ISYM",
        "BATCH",
        "IPR",
        "SIGIPR",
        "I",
        "SIGI",
        "BG",
        "SIGBG",
        "FRACTIONCALC",
        "XDET",
        "YDET",
        "ROT",
        "LP",
        "QE",
    ]

    assert integrater.get_integrater_wedge() == (1, 45)
    assert integrater.get_integrater_cell() == pytest.approx(
        (78.14, 78.14, 78.14, 90, 90, 90), abs=1e-1
    )

    # test serialization of integrater
    json_str = integrater.as_json()
    # print(json_str)
    integrater2 = DialsIntegrater.from_json(string=json_str)
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
        abs(mtz_object.n_reflections() - expected_reflections) < 300
    ), mtz_object.n_reflections()

    integrater2.set_integrater_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert (
        abs(mtz_object.n_reflections() - expected_reflections) < 300
    ), mtz_object.n_reflections()

    integrater2.set_integrater_prepare_done(False)
    integrater2_intensities = integrater2.get_integrater_intensities()
    assert os.path.exists(integrater2_intensities)
    reader = any_reflection_file(integrater2_intensities)
    assert reader.file_type() == "ccp4_mtz"
    mtz_object = reader.file_content()
    assert (
        abs(mtz_object.n_reflections() - expected_reflections) < 300
    ), mtz_object.n_reflections()

    # Test that diamond anvil cell attenuation correction does something.
    # That it does the right thing is left as a matter for the DIALS tests.
    integrater3 = DialsIntegrater.from_json(string=json_str)
    integrater3.set_integrater_sweep(sweep, reset=False)
    integrater3.set_integrater_done(False)
    integrater3.high_pressure = True
    # Don't get .hkl output because we're applying the attenuation correction to data
    # that weren't actually collected with a diamond anvil cell and some integrated
    # intensities will be rather nonsensical, which causes an error
    # 'cctbx Error: Inconsistent observation/sigma pair in columns: IPR, SIGIPR',
    # when some internal .hkl consistency checks are run, which is not meaningful here.
    integrater3.set_output_format("pickle")
    # Compare the first ten profile-fitted integrated intensities without correction.
    control_reflections = flex.reflection_table.from_file(
        integrater2.get_integrated_reflections()
    )
    valid = control_reflections.get_flags(control_reflections.flags.integrated_prf)
    valid = valid.iselection()[:10]
    control_reflections = control_reflections.select(valid)
    # Get the first ten profile-fitted integrated intensities with DAC correction.
    corrected_reflections = flex.reflection_table.from_file(
        integrater3.get_integrated_reflections()
    )
    valid = corrected_reflections.get_flags(corrected_reflections.flags.integrated_prf)
    valid = valid.iselection()[:10]
    corrected_reflections = corrected_reflections.select(valid)
    # Check that we're comparing equivalent reflections.
    assert control_reflections["miller_index"] == corrected_reflections["miller_index"]
    control_intensities = control_reflections["intensity.prf.value"]
    corrected_intensities = corrected_reflections["intensity.prf.value"]
    # Check that the reflection intensities are not the same.
    assert pytest.approx(control_intensities) != corrected_intensities


def test_dials_integrater_serial(regression_test, ccp4, dials_data, run_in_tmpdir):
    with mock.patch.object(sys, "argv", []):
        exercise_dials_integrater(dials_data, run_in_tmpdir.strpath, nproc=1)


def test_dials_integrater_high_pressure_set(monkeypatch):
    """Check that the appropriate PHIL parameter triggers high-pressure mode."""
    # Without the relevant PHIL parameter set, check everything is normal.
    integrater = DialsIntegrater()
    assert not integrater.high_pressure
    # Check we can trigger high-pressure mode with the relevant PHIL parameter.
    monkeypatch.setattr(PhilIndex.params.dials.high_pressure, "correction", True)
    integrater = DialsIntegrater()
    assert integrater.high_pressure
