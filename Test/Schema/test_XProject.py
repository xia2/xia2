from __future__ import absolute_import, division, print_function

import json
import os
import sys

import mock
import pathlib2


def exercise_serialization(dials_data, tmp_dir):
    base_path = pathlib2.Path(tmp_dir)
    template = dials_data("insulin").join("insulin_1_###.img").strpath

    from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
    from xia2.Modules.Refiner.DialsRefiner import DialsRefiner
    from xia2.Modules.Integrater.DialsIntegrater import DialsIntegrater
    from xia2.Modules.Scaler.CCP4ScalerA import CCP4ScalerA

    from dxtbx.model.experiment_list import ExperimentListTemplateImporter

    importer = ExperimentListTemplateImporter([template])
    experiments = importer.experiments
    imageset = experiments.imagesets()[0]

    from xia2.Schema.XProject import XProject
    from xia2.Schema.XCrystal import XCrystal
    from xia2.Schema.XWavelength import XWavelength
    from xia2.Schema.XSweep import XSweep
    from xia2.Schema.XSample import XSample

    proj = XProject(base_path=base_path)
    proj._name = "PROJ1"
    cryst = XCrystal("CRYST1", proj)
    wav = XWavelength("WAVE1", cryst, wavelength=0.98)
    samp = XSample("X1", cryst)
    cryst.add_wavelength(wav)
    cryst.set_ha_info({"atom": "S"})
    cryst.add_sample(samp)
    directory, image = os.path.split(imageset.get_path(1))
    sweep = wav.add_sweep(name="SWEEP1", sample=samp, directory=directory, image=image)
    samp.add_sweep(sweep)

    from dxtbx.serialize.load import _decode_dict

    indexer = DialsIndexer()
    indexer.set_working_directory(tmp_dir)
    indexer.add_indexer_imageset(imageset)
    indexer.set_indexer_sweep(sweep)
    sweep._indexer = indexer

    refiner = DialsRefiner()
    refiner.set_working_directory(tmp_dir)
    refiner.add_refiner_indexer(sweep.get_epoch(1), indexer)
    refiner.add_refiner_sweep(sweep)
    sweep._refiner = refiner

    integrater = DialsIntegrater()
    integrater.set_output_format("hkl")
    integrater.set_working_directory(tmp_dir)
    integrater.setup_from_image(imageset.get_path(1))
    integrater.set_integrater_refiner(refiner)
    # integrater.set_integrater_indexer(indexer)
    integrater.set_integrater_sweep(sweep)
    integrater.set_integrater_epoch(sweep.get_epoch(1))
    integrater.set_integrater_sweep_name(sweep.get_name())
    integrater.set_integrater_project_info(
        cryst.get_name(), wav.get_name(), sweep.get_name()
    )
    sweep._integrater = integrater

    scaler = CCP4ScalerA(base_path=base_path)
    scaler.add_scaler_integrater(integrater)
    scaler.set_scaler_xcrystal(cryst)
    scaler.set_scaler_project_info(cryst.get_name(), wav.get_name())
    scaler._scalr_xcrystal = cryst
    cryst._scaler = scaler

    proj.add_crystal(cryst)

    s_dict = sweep.to_dict()
    s_str = json.dumps(s_dict, ensure_ascii=True)
    s_dict = json.loads(s_str, object_hook=_decode_dict)
    xsweep = XSweep.from_dict(s_dict)
    assert xsweep

    w_dict = wav.to_dict()
    w_str = json.dumps(w_dict, ensure_ascii=True)
    w_dict = json.loads(w_str, object_hook=_decode_dict)
    xwav = XWavelength.from_dict(w_dict)
    assert xwav.get_sweeps()[0].get_wavelength() is xwav

    c_dict = cryst.to_dict()
    c_str = json.dumps(c_dict, ensure_ascii=True)
    c_dict = json.loads(c_str, object_hook=_decode_dict)
    xcryst = XCrystal.from_dict(c_dict)
    assert (
        xcryst.get_xwavelength(xcryst.get_wavelength_names()[0]).get_crystal() is xcryst
    )

    p_dict = proj.to_dict()
    p_str = json.dumps(p_dict, ensure_ascii=True)
    p_dict = json.loads(p_str, object_hook=_decode_dict)
    xproj = XProject.from_dict(p_dict)
    assert xproj.path == base_path
    assert list(xproj.get_crystals().values())[0].get_project() is xproj
    assert list(xproj.get_crystals().values())[0]._scaler._base_path == base_path

    json_str = proj.as_json()
    xproj = XProject.from_json(string=json_str)
    assert xproj.path == base_path
    assert list(xproj.get_crystals().values())[0].get_project() is xproj
    print(xproj.get_output())
    print("\n".join(xproj.summarise()))
    json_str = xproj.as_json()
    xproj = XProject.from_json(string=json_str)
    assert xproj.path == base_path
    # Test that we can serialize to json and back again
    xproj = XProject.from_json(string=xproj.as_json())
    assert xproj.path == base_path
    xcryst = list(xproj.get_crystals().values())[0]
    assert xcryst.get_project() is xproj
    intgr = xcryst._get_integraters()[0]
    assert intgr.get_integrater_finish_done()
    assert (
        xcryst._get_scaler()
        ._sweep_handler.get_sweep_information(intgr.get_integrater_epoch())
        .get_integrater()
        is intgr
    )

    print(xproj.get_output())
    print("\n".join(xproj.summarise()))


def test_serialization(regression_test, ccp4, dials_data, run_in_tmpdir):
    with mock.patch.object(sys, "argv", []):
        exercise_serialization(dials_data, run_in_tmpdir.strpath)
