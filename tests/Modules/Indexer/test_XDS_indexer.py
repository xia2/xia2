from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

from dxtbx.model import ExperimentList

from xia2.Handlers.Phil import PhilIndex
from xia2.Modules.Indexer.XDSIndexer import XDSIndexer
from xia2.Schema.XCrystal import XCrystal
from xia2.Schema.XSample import XSample
from xia2.Schema.XSweep import XSweep
from xia2.Schema.XWavelength import XWavelength


def exercise_xds_indexer(dials_data, tmp_dir, nproc=None):
    if nproc is not None:
        PhilIndex.params.xia2.settings.multiprocessing.nproc = nproc

    template = dials_data("insulin").join("insulin_1_###.img").strpath

    indexer = XDSIndexer()
    indexer.set_working_directory(tmp_dir)

    experiments = ExperimentList.from_templates([template])
    imageset = experiments.imagesets()[0]
    indexer.add_indexer_imageset(imageset)

    cryst = XCrystal("CRYST1", None)
    wav = XWavelength("WAVE1", cryst, indexer.get_wavelength())
    samp = XSample("X1", cryst)
    directory, image = os.path.split(imageset.get_path(1))
    sweep = XSweep("SWEEP1", wav, samp, directory=directory, image=image)
    indexer.set_indexer_sweep(sweep)

    indexer.index()

    assert indexer.get_indexer_cell() == pytest.approx(
        (78.076, 78.076, 78.076, 90, 90, 90), abs=1
    ), indexer.get_indexer_cell()
    experiment = indexer.get_indexer_experiment_list()[0]
    sgi = experiment.crystal.get_space_group().info()
    assert sgi.type().number() == 197

    beam_centre = indexer.get_indexer_beam_centre()
    assert beam_centre == pytest.approx((94.4221, 94.5096), abs=1e-1)
    assert indexer.get_indexer_images() == [(1, 5), (20, 24), (41, 45)]
    print(indexer.get_indexer_experiment_list()[0].crystal)
    print(indexer.get_indexer_experiment_list()[0].detector)

    # test serialization of indexer
    json_str = indexer.as_json()
    print(json_str)
    indexer2 = XDSIndexer.from_json(string=json_str)
    indexer2.index()

    assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell())
    assert indexer.get_indexer_beam_centre() == pytest.approx(
        indexer2.get_indexer_beam_centre()
    )
    assert indexer.get_indexer_images() == [
        tuple(i) for i in indexer2.get_indexer_images()
    ]

    indexer.eliminate()
    indexer2.eliminate()

    assert indexer.get_indexer_cell() == pytest.approx(indexer2.get_indexer_cell())
    assert indexer.get_indexer_lattice() == "hR"
    assert indexer2.get_indexer_lattice() == "hR"


def test_xds_indexer_serial(regression_test, ccp4, xds, dials_data, run_in_tmpdir):
    with mock.patch.object(sys, "argv", []):
        exercise_xds_indexer(dials_data, run_in_tmpdir.strpath, nproc=1)
