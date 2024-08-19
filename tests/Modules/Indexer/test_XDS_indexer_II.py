from __future__ import annotations

import os
import sys
from unittest import mock

import pytest
from dxtbx.model import ExperimentList

from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.Indexer.XDSIndexerII import XDSIndexerII
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XSample import XSample
from xia2.Schema.XSweep import XSweep
from xia2.Schema.XWavelength import XWavelength


def exercise_xds_indexer(dials_data, tmp_path, nproc=None):
    if nproc is not None:
        PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

    template = dials_data("insulin", pathlib=True) / "insulin_1_###.img"

    indexer = XDSIndexerII()
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
        (78.054, 78.054, 78.054, 90, 90, 90), abs=1
    )
    experiment = indexer.get_indexer_experiment_list()[0]
    sgi = experiment.crystal.get_space_group().info()
    assert sgi.type().number() == 197

    beam_centre = indexer.get_indexer_beam_centre()
    assert beam_centre == pytest.approx((94.4239, 94.5110), abs=1e-1)
    assert indexer.get_indexer_images() == [(1, 45)]
    print(indexer.get_indexer_experiment_list()[0].crystal)
    print(indexer.get_indexer_experiment_list()[0].detector)

    # test serialization of indexer
    json_str = indexer.as_json()
    print(json_str)
    indexer2 = XDSIndexerII.from_json(string=json_str)
    indexer2.index()

    assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell())
    assert indexer.get_indexer_beam_centre() == pytest.approx(
        indexer2.get_indexer_beam_centre()
    )
    assert list(indexer.get_indexer_images()[0]) == list(
        indexer2.get_indexer_images()[0]
    )

    indexer.eliminate()
    indexer2.eliminate()

    assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell())
    assert indexer.get_indexer_lattice() == "hR"
    assert indexer2.get_indexer_lattice() == "hR"


def test_xds_indexer_serial(regression_test, ccp4, xds, dials_data, run_in_tmp_path):
    with mock.patch.object(sys, "argv", []):
        exercise_xds_indexer(dials_data, run_in_tmp_path, nproc=1)
