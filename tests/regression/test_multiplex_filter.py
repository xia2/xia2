from __future__ import annotations

import json
import os
import pathlib

import pytest

from xia2.cli.multiplex import run as run_multiplex
from xia2.cli.multiplex_filtering import multiplex_filter_error_message
from xia2.cli.multiplex_filtering import run as run_mplx_filter

expected_data_files = [
    "filtered.expt",
    "filtered.refl",
    "filtered.mtz",
    "filtered_unmerged.mtz",
    "filtered_unmerged.mmcif",
    "filtered.sca",
    "filtered_unmerged.sca",
    "xia2.multiplex_filtering.html",
    "xia2.multiplex_filtering.json",
]


@pytest.fixture()
def proteinase_k(dials_data):
    data_dir = dials_data("multi_crystal_proteinase_k", pathlib=True)
    expts = sorted(os.fspath(f) for f in data_dir.glob("experiments*.json"))
    refls = sorted(os.fspath(f) for f in data_dir.glob("reflections*.pickle"))
    yield expts, refls


@pytest.mark.parametrize("filtering", [("deltacchalf"), (None)])
def test_multiplex_filtering_program(proteinase_k, filtering, run_in_tmp_path):
    """
    Run xia2.multiplex_filtering to check it runs.
    Run once setting the desired filtering method.
    Run once to check the program will default to filtering even if not specified.
    """
    expts, refls = proteinase_k
    command_line_args = expts + refls + []
    run_multiplex(command_line_args)
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    os.chdir(filtering_dir)
    if filtering:
        filter_args = [mplx_dir.as_posix(), f"filtering.method={filtering}"]
    else:
        filter_args = [mplx_dir.as_posix()]
    run_mplx_filter(filter_args)
    for f in expected_data_files:
        assert os.path.isfile(f), "expected file %s missing" % f


def test_consistency(proteinase_k, run_in_tmp_path):
    """
    Checks that the filtering results produced by xia2.multiplex match xia2.multiplex_filtering when run with the same parameters.
    """
    expts, refls = proteinase_k
    command_line_args = expts + refls + ["filtering.method=deltacchalf"]
    run_multiplex(command_line_args)
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    os.chdir(filtering_dir)
    filter_args = [mplx_dir.as_posix(), "filtering.method=deltacchalf"]
    run_mplx_filter(filter_args)
    for f in expected_data_files:
        assert os.path.isfile(f), "expected file %s missing" % f

    with open(mplx_dir / "xia2.multiplex.json") as fh:
        d_mplx = json.load(fh)

    with open("xia2.multiplex_filtering.json") as fh:
        d_filtered = json.load(fh)

    for i in d_filtered["datasets"]["Filtered"]["merging_stats"]:
        assert (
            d_filtered["datasets"]["Filtered"]["merging_stats"][i]
            == d_mplx["datasets"]["Filtered"]["merging_stats"][i]
        )


def test_exit_for_invalid_multiplex_dir(run_in_tmp_path):
    """
    Check xia2.multiplex_filtering exits gracefully if multiplex directory doesn't contain a multiplex job.
    """
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filter_args = [mplx_dir.as_posix(), "filtering.method=deltacchalf"]
    with pytest.raises(SystemExit) as e:
        run_mplx_filter(filter_args)
    assert str(e.value) == multiplex_filter_error_message


@pytest.mark.parametrize("directory", [("fake_directory"), (None)])
def test_exit_for_no_multiplex_dir(directory, run_in_tmp_path):
    """
    Check xia2.multiplex_filtering exits gracefully if multiplex directory is not provided or doesn't exist.
    """
    if directory:
        filter_args = [pathlib.Path(directory).as_posix()]
    else:
        filter_args = []
    with pytest.raises(SystemExit) as e:
        run_mplx_filter(filter_args)
    assert (
        str(e.value)
        == "Please provide a path to a directory containing a completed multiplex job."
    )


def test_exit_partial_multiplex_dir(proteinase_k, run_in_tmp_path):
    """
    Run multiplex, then remove a key file used by the filtering module.
    Check that xia2.multiplex_filtering exists gracefully.
    This simulates running on an incomplete multiplex directory.
    """
    expts, refls = proteinase_k
    command_line_args = expts + refls + []
    run_multiplex(command_line_args)
    mplx_dir = pathlib.Path(run_in_tmp_path)
    os.remove("xia2.multiplex.json")
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    os.chdir(filtering_dir)
    filter_args = [mplx_dir.as_posix(), "filtering.method=deltacchalf"]
    with pytest.raises(SystemExit) as e:
        run_mplx_filter(filter_args)
    assert str(e.value) == multiplex_filter_error_message


def test_overwrite_multiplex_filtering_params(proteinase_k, run_in_tmp_path):
    """
    Run multiplex with dataset deltacchalf filtering.
    Run mutliplex_filtering with image mode deltacchalf filtering.
    Checks that user parameters overwrites original multiplex parameters.
    """
    expts, refls = proteinase_k
    command_line_args = (
        expts
        + refls
        + ["filtering.method=deltacchalf", "filtering.deltacchalf.mode=dataset"]
    )
    run_multiplex(command_line_args)
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    os.chdir(filtering_dir)
    filter_args = [
        mplx_dir.as_posix(),
        "filtering.deltacchalf.mode=image_group",
        "filtering.deltacchalf.group_size=12",
    ]
    run_mplx_filter(filter_args)
    for f in expected_data_files:
        assert os.path.isfile(f), "expected file %s missing" % f
    with open(mplx_dir / "dials.scale.log", "r") as f:
        data_mplx = f.readlines()
    with open(filtering_dir / "dials.scale.log", "r") as f:
        data_filtering = f.readlines()

    mplx_groups = None
    filtering_groups = None

    for i in data_mplx:
        if "# Groups:" in i:
            mplx_groups = i
    for j in data_filtering:
        if "# Groups:" in j:
            filtering_groups = j

    # If image mode has successfully run, the number of groups increases compared to dataset mode
    assert mplx_groups != filtering_groups
