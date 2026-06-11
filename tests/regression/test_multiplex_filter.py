from __future__ import annotations

import json
import math
import os
import pathlib
import shutil
import subprocess

import pytest

from xia2.cli.multiplex_filtering import multiplex_filter_error_message

expected_data_files = [
    pathlib.Path("Processing") / "filtered.expt",
    pathlib.Path("Processing") / "filtered.refl",
    pathlib.Path("DataFiles") / "filtered.mtz",
    pathlib.Path("DataFiles") / "filtered_unmerged.mtz",
    pathlib.Path("DataFiles") / "filtered_unmerged.mmcif",
    pathlib.Path("DataFiles") / "filtered.sca",
    pathlib.Path("DataFiles") / "filtered_unmerged.sca",
    pathlib.Path("xia2.multiplex_filtering.html"),
    pathlib.Path("Processing") / "xia2.multiplex_filtering.json",
]


@pytest.fixture()
def proteinase_k(dials_data):
    data_dir = dials_data("multi_crystal_proteinase_k")
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
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    if filtering:
        filter_args = [mplx_dir.as_posix(), f"filtering.method={filtering}"]
    else:
        filter_args = [mplx_dir.as_posix()]
    result = subprocess.run(
        [shutil.which("xia2.multiplex_filtering")] + filter_args,
        cwd=run_in_tmp_path / filtering_dir,
        capture_output=True,
    )
    assert not result.returncode
    for f in expected_data_files:
        assert (filtering_dir / f).is_file(), "expected file %s missing" % f


def test_consistency(proteinase_k, run_in_tmp_path):
    """
    Checks that the filtering results produced by xia2.multiplex match xia2.multiplex_filtering when run with the same parameters.
    """
    expts, refls = proteinase_k
    command_line_args = expts + refls + ["filtering.method=deltacchalf"]
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    filter_args = [mplx_dir.as_posix(), "filtering.method=deltacchalf"]
    result = subprocess.run(
        [shutil.which("xia2.multiplex_filtering")] + filter_args,
        cwd=run_in_tmp_path / filtering_dir,
        capture_output=True,
    )
    assert not result.returncode
    for f in expected_data_files:
        assert (filtering_dir / f).is_file(), "expected file %s missing" % f

    with open(mplx_dir / "Processing" / "xia2.multiplex.json") as fh:
        d_mplx = json.load(fh)

    with open(filtering_dir / "Processing" / "xia2.multiplex_filtering.json") as fh:
        d_filtered = json.load(fh)

    for x, y in zip(
        d_mplx["datasets"]["Filtered"]["merging_stats"]["cc_one_half"],
        d_filtered["datasets"]["Filtered"]["merging_stats"]["cc_one_half"],
    ):
        assert math.isclose(x, y, abs_tol=1e-10)


def test_exit_for_invalid_multiplex_dir(run_in_tmp_path):
    """
    Check xia2.multiplex_filtering exits gracefully if multiplex directory doesn't contain a multiplex job.
    """
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filter_args = [mplx_dir.as_posix(), "filtering.method=deltacchalf"]
    result = subprocess.run(
        [shutil.which("xia2.multiplex_filtering")] + filter_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert result.returncode
    assert multiplex_filter_error_message in str(result.stderr)


@pytest.mark.parametrize("directory", [("fake_directory"), (None)])
def test_exit_for_no_multiplex_dir(directory, run_in_tmp_path):
    """
    Check xia2.multiplex_filtering exits gracefully if multiplex directory is not provided or doesn't exist.
    """
    if directory:
        filter_args = [pathlib.Path(directory).as_posix()]
    else:
        filter_args = []
    result = subprocess.run(
        [shutil.which("xia2.multiplex_filtering")] + filter_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert result.returncode
    assert (
        "Please provide a path to a directory containing a completed multiplex job."
        in str(result.stderr)
    )


def test_exit_partial_multiplex_dir(proteinase_k, run_in_tmp_path):
    """
    Run multiplex, then remove a key file used by the filtering module.
    Check that xia2.multiplex_filtering exists gracefully.
    This simulates running on an incomplete multiplex directory.
    """
    expts, refls = proteinase_k
    command_line_args = expts + refls + []
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode
    mplx_dir = pathlib.Path(run_in_tmp_path)
    json = run_in_tmp_path / "Processing" / "xia2.multiplex.json"
    json.unlink()
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    filter_args = [mplx_dir.as_posix(), "filtering.method=deltacchalf"]
    result = subprocess.run(
        [shutil.which("xia2.multiplex_filtering")] + filter_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert result.returncode
    assert multiplex_filter_error_message in str(result.stderr)


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
    result = subprocess.run(
        [shutil.which("xia2.multiplex")] + command_line_args,
        cwd=run_in_tmp_path,
        capture_output=True,
    )
    assert not result.returncode
    mplx_dir = pathlib.Path(run_in_tmp_path)
    filtering_dir = mplx_dir / "filtering"
    filtering_dir.mkdir()
    filter_args = [
        mplx_dir.as_posix(),
        "filtering.deltacchalf.mode=image_group",
        "filtering.deltacchalf.group_size=12",
    ]
    result = subprocess.run(
        [shutil.which("xia2.multiplex_filtering")] + filter_args,
        cwd=run_in_tmp_path / filtering_dir,
        capture_output=True,
    )
    assert not result.returncode
    for f in expected_data_files:
        assert (filtering_dir / f).is_file(), "expected file %s missing" % f

    mplx_scale_logs = list((run_in_tmp_path / "LogFiles").glob("*_dials.scale.log"))

    assert len(mplx_scale_logs) == 2

    filter_scale_logs = list(
        (run_in_tmp_path / "filtering" / "LogFiles").glob("*_dials.scale.log")
    )

    assert len(filter_scale_logs) == 1

    mplx_scale_log = mplx_scale_logs[1]
    filter_scale_log = filter_scale_logs[0]

    with open(mplx_scale_log, "r", encoding="utf-8") as f:
        data_mplx = f.readlines()
    with open(filter_scale_log, "r", encoding="utf-8") as f:
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
