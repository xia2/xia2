from __future__ import absolute_import, division, print_function

import os
import sys

import mock
import pytest
from libtbx.test_utils import approx_equal
from xia2.DriverExceptions import NotAvailableError


def exercise_xds_indexer(dials_data, tmp_dir, nproc=None):
    if nproc is not None:
        from xia2.Handlers.Phil import PhilIndex

        PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

    template = dials_data("insulin").join("insulin_1_###.img").strpath

    from xia2.Modules.Indexer.XDSIndexerII import XDSIndexerII

    try:
        indexer = XDSIndexerII()
    except NotAvailableError:
        pytest.skip("XDS not found")

    indexer.set_working_directory(tmp_dir)

    from dxtbx.model.experiment_list import ExperimentListTemplateImporter

    importer = ExperimentListTemplateImporter([template])
    experiments = importer.experiments
    imageset = experiments.imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    from xia2.Schema.XCrystal import XCrystal
    from xia2.Schema.XWavelength import XWavelength
    from xia2.Schema.XSweep import XSweep
    from xia2.Schema.XSample import XSample

    cryst = XCrystal("CRYST1", None)
    wav = XWavelength("WAVE1", cryst, imageset.get_beam().get_wavelength())
    samp = XSample("X1", cryst)
    directory, image = os.path.split(imageset.get_path(1))
    sweep = XSweep("SWEEP1", wav, samp, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)

    indexer.index()

    assert approx_equal(
        indexer.get_indexer_cell(), (78.054, 78.054, 78.054, 90, 90, 90), eps=1
    ), indexer.get_indexer_cell()
    experiment = indexer.get_indexer_experiment_list()[0]
    sgi = experiment.crystal.get_space_group().info()
    assert sgi.type().number() == 197

    beam_centre = indexer.get_indexer_beam_centre()
    assert approx_equal(beam_centre, (94.4239, 94.5110), eps=1e-1)
    assert indexer.get_indexer_images() == [(1, 45)]
    print(indexer.get_indexer_experiment_list()[0].crystal)
    print(indexer.get_indexer_experiment_list()[0].detector)

    # test serialization of indexer
    json_str = indexer.as_json()
    print(json_str)
    indexer2 = XDSIndexerII.from_json(string=json_str)
    indexer2.index()

    assert approx_equal(indexer.get_indexer_cell(), indexer2.get_indexer_cell())
    assert approx_equal(
        indexer.get_indexer_beam_centre(), indexer2.get_indexer_beam_centre()
    )
    assert approx_equal(indexer.get_indexer_images(), indexer2.get_indexer_images())

    indexer.eliminate()
    indexer2.eliminate()

    assert approx_equal(indexer.get_indexer_cell(), indexer2.get_indexer_cell())
    assert indexer.get_indexer_lattice() == "hR"
    assert indexer2.get_indexer_lattice() == "hR"


def test_xds_indexer_serial(regression_test, ccp4, dials_data, run_in_tmpdir):
    with mock.patch.object(sys, "argv", []):
        exercise_xds_indexer(dials_data, run_in_tmpdir.strpath, nproc=1)
