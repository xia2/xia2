import os
import sys

from unittest import mock
import pathlib
import pytest


@pytest.mark.parametrize("nproc", [1])
def test_ccp4_scalerA(regression_test, ccp4, dials_data, run_in_tmpdir, nproc):
    if nproc is not None:
        from xia2.Handlers.Phil import PhilIndex

        PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

    template = dials_data("insulin").join("insulin_1_###.img").strpath

    tmpdir = run_in_tmpdir.strpath

    from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
    from xia2.Modules.Refiner.DialsRefiner import DialsRefiner
    from xia2.Modules.Integrater.DialsIntegrater import DialsIntegrater
    from xia2.Modules.Scaler.CCP4ScalerA import CCP4ScalerA

    indexer = DialsIndexer()
    indexer.set_working_directory(tmpdir)
    from dxtbx.model.experiment_list import ExperimentListTemplateImporter

    importer = ExperimentListTemplateImporter([template])
    experiments = importer.experiments
    imageset = experiments.imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    from xia2.Schema.XCrystal import XCrystal
    from xia2.Schema.XWavelength import XWavelength
    from xia2.Schema.XSweep import XSweep
    from xia2.Schema.XSample import XSample
    from xia2.Schema.XProject import XProject

    proj = XProject(name="AUTOMATIC")
    cryst = XCrystal("CRYST1", proj)
    wav = XWavelength("WAVE1", cryst, imageset.get_beam().get_wavelength())
    cryst.add_wavelength(wav)
    samp = XSample("X1", cryst)
    directory, image = os.path.split(imageset.get_path(1))
    with mock.patch.object(sys, "argv", []):
        sweep = XSweep("SWEEP1", wav, samp, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)

    refiner = DialsRefiner()
    refiner.set_working_directory(tmpdir)
    refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)

    integrater = DialsIntegrater()
    integrater.set_output_format("hkl")
    integrater.set_working_directory(tmpdir)
    integrater.setup_from_image(imageset.get_path(1))
    integrater.set_integrater_refiner(refiner)
    # integrater.set_integrater_indexer(indexer)
    integrater.set_integrater_sweep(sweep)
    integrater.set_integrater_sweep_name("SWEEP1")
    integrater.set_integrater_project_info("AUTOMATIC", "CRYST1", "WAVE1")

    scaler = CCP4ScalerA(base_path=pathlib.Path(tmpdir))
    scaler.add_scaler_integrater(integrater)
    scaler.set_scaler_xcrystal(cryst)
    scaler.set_scaler_project_info("AUTOMATIC", "CRYST1")

    check_scaler_files_exist(scaler)

    # test serialization of scaler
    json_str = scaler.as_json()
    # print json_str
    scaler2 = CCP4ScalerA.from_json(string=json_str)
    scaler2.set_scaler_xcrystal(cryst)

    check_scaler_files_exist(scaler2)

    scaler2.set_scaler_done(False)
    check_scaler_files_exist(scaler2)

    scaler2._scalr_integraters = {}  # XXX
    scaler2.add_scaler_integrater(integrater)
    scaler2.set_scaler_prepare_done(False)
    check_scaler_files_exist(scaler2)


def check_scaler_files_exist(scaler):
    merged = scaler.get_scaled_merged_reflections()
    for filetype in ("mtz", "sca", "sca_unmerged"):
        assert filetype in merged
        if isinstance(merged[filetype], str):
            files = [merged[filetype]]
        else:
            files = merged[filetype].values()
        for f in files:
            assert os.path.isfile(f)
