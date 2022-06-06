from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

from dxtbx.model import ExperimentList

from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.Indexer.DialsIndexer import DialsIndexer
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XSample import XSample
from xia2.Schema.XSweep import XSweep
from xia2.Schema.XWavelength import XWavelength


def _exercise_dials_indexer(dials_data, tmp_path):
    PhilIndex.params.xia2.settings.multiprocessing.nproc = 1

    template = dials_data("centroid_test_data", pathlib=True) / "centroid_####.cbf"

    indexer = DialsIndexer()
    indexer.set_working_directory(os.fspath(tmp_path))

    experiments = ExperimentList.from_templates([template])
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
        (42.20, 42.20, 39.68, 90, 90, 90), rel=1e-3
    )
    solution = indexer.get_solution()
    assert solution["rmsd"] == pytest.approx(0.09241, abs=1e-3)
    assert solution["metric"] == pytest.approx(0.34599, abs=5e-3)
    assert solution["number"] == 9
    assert solution["lattice"] == "tP"

    beam_centre = indexer.get_indexer_beam_centre()
    assert beam_centre == pytest.approx((219.8758, 212.6103), abs=1e-3)
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
    assert indexer.get_indexer_lattice() == "oC"
    assert indexer2.get_indexer_lattice() == "oC"


def test_dials_indexer_serial(ccp4, dials_data, run_in_tmp_path):
    with mock.patch.object(sys, "argv", []):
        _exercise_dials_indexer(dials_data, run_in_tmp_path)
