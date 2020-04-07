from __future__ import absolute_import, division, print_function

import os
import pytest

from dxtbx.model.experiment_list import ExperimentListTemplateImporter

from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XWavelength import XWavelength
from xia2.Schema.XSweep import XSweep
from xia2.Schema.XSample import XSample


def test_dials_indexer_serial(
    regression_test, ccp4, dials_data, run_in_tmpdir, monkeypatch
):
    monkeypatch.setattr(PhilIndex.params.xia2.settings.multiprocessing, "nproc", 1)

    template = dials_data("insulin").join("insulin_1_###.img").strpath

    indexer = DialsIndexer()
    indexer.set_working_directory(run_in_tmpdir.strpath)

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

    indexer.index()

    assert indexer.get_indexer_cell() == pytest.approx(
        (78.14, 78.14, 78.14, 90, 90, 90), rel=1e-3
    )
    solution = indexer.get_solution()
    assert solution["rmsd"] == pytest.approx(0.03545, abs=1e-3)
    assert solution["metric"] == pytest.approx(0.02517, abs=1e-3)
    assert solution["number"] == 22
    assert solution["lattice"] == "cI"

    beam_centre = indexer.get_indexer_beam_centre()
    assert beam_centre == pytest.approx(
        (94.41567208118963, 94.51337522659865), abs=1e-3
    )
    print(indexer.get_indexer_experiment_list()[0].crystal)
    print(indexer.get_indexer_experiment_list()[0].detector)

    # test serialization of indexer
    json_str = indexer.as_json()
    indexer2 = DialsIndexer.from_json(string=json_str)
    indexer2.index()

    assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell())
    assert indexer.get_indexer_beam_centre() == pytest.approx(
        indexer2.get_indexer_beam_centre()
    )

    indexer.eliminate()
    indexer2.eliminate()

    assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell())
    assert indexer.get_indexer_lattice() == "hR"
    assert indexer2.get_indexer_lattice() == "hR"
