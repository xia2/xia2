from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
from typing import List

import pytest

from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dxtbx.serialize import load
from iotbx import mtz


def check_output(main_dir, find_spots=False, index=False, integrate=False):

    assert find_spots is (main_dir / "batch_1" / "strong.refl").is_file()
    assert index is (main_dir / "batch_1" / "indexed.expt").is_file()
    assert index is (main_dir / "batch_1" / "indexed.refl").is_file()
    assert integrate is (main_dir / "batch_1" / "integrated_1.expt").is_file()
    assert integrate is (main_dir / "batch_1" / "integrated_1.refl").is_file()
    assert (main_dir / "xia2.ssx.log").is_file()
    assert integrate is (main_dir / "DataFiles" / "integrated_1_batch_1.expt").is_file()
    assert integrate is (main_dir / "DataFiles" / "integrated_1_batch_1.expt").is_file()


@pytest.mark.parametrize(
    "option,expected_success",
    [
        ("assess_crystals.images_to_use=3:5", [True, False, True]),
        ("batch_size=2", [False, False, True, False, True]),
        ("assess_crystals.n_crystals=2", [False, False, True, False, True]),
    ],
)
def test_assess_crystals(dials_data, tmp_path, option, expected_success):
    """
    Test a basic run. Expect to import and then do crystal assessment,
    and nothing more (for now).

    The options test the two modes of operation - either assess a specific
    image range or process cumulatively in batches until a given number of
    crystals are indexed, or all images are used.
    """

    ssx = dials_data("cunir_serial", pathlib=True)
    # Set the max cell to avoid issue of a suitable max cell not being found
    # due to very thin batch size.
    with (tmp_path / "index.phil").open(mode="w") as f:
        f.write("indexing.max_cell=150")
    args = ["xia2.ssx", option, "indexing.phil=index.phil"]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # want to test
    assert (tmp_path / "import").is_dir()
    assert (tmp_path / "import" / "file_input.json").is_file()

    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] is None
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]

    assert (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "assess_crystals" / "assess_crystals.json").is_file()
    assert (tmp_path / "assess_crystals" / "dials.cell_clusters.html").is_file()

    with open(tmp_path / "assess_crystals" / "assess_crystals.json", "r") as f:
        data = json.load(f)
    assert data["success_per_image"] == expected_success


def test_import_phil_handling(dials_data, tmp_path):
    """Just run geometry refinement. This will do the refinement then reimport
    using the refined as reference."""
    ssx = dials_data("cunir_serial", pathlib=True)
    with (tmp_path / "import.phil").open(mode="w") as f:
        f.write("geometry.beam.wavelength=1.36\ngeometry.detector.distance=247.6")
    with (tmp_path / "index.phil").open(mode="w") as f:
        f.write("indexing.max_cell=150")
    args = [
        "xia2.ssx",
        "steps=None",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "indexing.phil=index.phil",
        "dials_import.phil=import.phil",
        "max_lattices=1",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    imported_with_ref = load.experiment_list(tmp_path / "import" / "imported.expt")
    assert (
        imported_with_ref.beams()[0].get_wavelength() == 1.36
    )  # would be 1.37611 without import.phil
    assert (
        imported_with_ref.detectors()[0].to_dict()["panels"][0]["origin"][2] != -247.6
    )
    imported_without_ref = load.experiment_list(
        tmp_path / "geometry_refinement" / "imported.expt"
    )
    assert (
        imported_without_ref.beams()[0].get_wavelength() == 1.36
    )  # would be 1.37611 without import.phil
    assert (
        imported_without_ref.detectors()[0].to_dict()["panels"][0]["origin"][2]
        == -247.6
    )


@pytest.mark.parametrize(
    "option,expected_success",
    [
        ("geometry_refinement.images_to_use=3:5", [True, True, True]),
        ("batch_size=2", [False, True, True, True, True]),
        ("geometry_refinement.n_crystals=2", [False, True, True, True, True]),
    ],
)
def test_geometry_refinement(dials_data, tmp_path, option, expected_success):
    ssx = dials_data("cunir_serial", pathlib=True)
    # Set the max cell to avoid issue of a suitable max cell not being found
    # due to very thin batch size.
    with (tmp_path / "index.phil").open(mode="w") as f:
        f.write("indexing.max_cell=150")
    args = [
        "xia2.ssx",
        "steps=None",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        option,
        "indexing.phil=index.phil",
        "max_lattices=1",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Check that the processing went straight to geometry refinement and then
    # stopped before processing the batches
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()
    assert not (tmp_path / "batch_1").is_dir()

    # Test the data was reimported correctly ready for next run
    assert (tmp_path / "import").is_dir()
    assert (tmp_path / "import" / "file_input.json").is_file()
    assert (tmp_path / "import" / "imported.expt").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]

    # Inspect the output to check which images were used in refinement.
    assert (tmp_path / "geometry_refinement" / "geometry_refinement.json").is_file()
    assert (tmp_path / "geometry_refinement" / "dials.cell_clusters.html").is_file()
    with open(tmp_path / "geometry_refinement" / "geometry_refinement.json", "r") as f:
        data = json.load(f)
    assert data["success_per_image"] == expected_success
    refined_expts = load.experiment_list(reference, check_format=False)
    assert len(refined_expts) == sum(expected_success)
    assert len(refined_expts.detectors()) == 1

    assert (tmp_path / "DataFiles" / "refined.expt").is_file()
    assert (tmp_path / "LogFiles" / "dials.refine.log").is_file()


@pytest.fixture
def refined_expt(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "steps=None",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()
    refined_expts = load.experiment_list(reference, check_format=False)

    shutil.rmtree(tmp_path / "DataFiles")
    shutil.rmtree(tmp_path / "LogFiles")
    return refined_expts


@pytest.mark.parametrize(
    "starting",
    [True, False],
)
def test_run_with_reference(dials_data, tmp_path, refined_expt, starting):
    """
    Test running with a supplied reference geometry from a refined.expt.
    """
    refined_expt.as_file(tmp_path / "refined.expt")

    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        "steps=find_spots+index+integrate",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))
    if starting:
        args.append(f"starting_geometry={os.fspath(tmp_path / 'refined.expt')}")
    else:
        args.append(f"reference_geometry={os.fspath(tmp_path / 'refined.expt')}")

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=True)
    if starting:
        assert (tmp_path / "DataFiles" / "refined.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.refine.log").is_file()
    else:
        assert not (tmp_path / "DataFiles" / "refined.expt").is_file()
        assert not (tmp_path / "LogFiles" / "dials.refine.log").is_file()
    assert (tmp_path / "geometry_refinement" / "detector_models.pdf").is_file()


def test_slice_cbfs(dials_data, tmp_path, refined_expt):
    """
    Test slicing an image range from the cbf template
    """
    refined_expt.as_file(tmp_path / "refined.expt")

    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        f"reference_geometry={os.fspath(tmp_path / 'refined.expt')}",
        "steps=find_spots+index",
        "max_lattices=1",
    ]
    args.append(
        "template=" + os.fspath(ssx / "merlin0047_17###.cbf:2:4")
    )  # i.e. 17002,17003,17004

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=False)

    indexed = load.experiment_list(tmp_path / "batch_1" / "indexed.expt")
    images = []
    iset = indexed.imagesets()[0]
    for i, expt in enumerate(indexed):
        images.append(iset.get_image_identifier(i).split("_")[-1].rstrip(".cbf"))

    assert images == ["17002", "17003", "17004"]
    # Also check the correct images were reported in the indexing report.
    images = []
    with open(tmp_path / "batch_1" / "dials.ssx_index.log", "r") as f:
        lines = f.readlines()
        for l in lines:
            if "merlin" in l:
                for p in l.split():
                    if "merlin" in p:
                        images.append(p.split("_")[-1].rstrip(".cbf"))
    assert images == ["17002", "17003", "17004"]


def test_full_run_without_reference(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        "d_min=2.0",
        "enable_live_reporting=True",
        "max_lattices=1",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Now check that the processing went straight to geometry refinement
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()
    assert (tmp_path / "DataFiles" / "refined.expt").is_file()
    assert (tmp_path / "LogFiles" / "dials.refine.log").is_file()

    # Now check that the data was reimported with this reference
    assert (tmp_path / "import" / "file_input.json").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Check that the data were integrated with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    assert (tmp_path / "batch_1/nuggets").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers
    check_output(tmp_path, find_spots=True, index=True, integrate=True)
    assert len(list((tmp_path / "batch_1/nuggets").glob("nugget_index*"))) == 5
    assert len(list((tmp_path / "batch_1/nuggets").glob("nugget_integrate*"))) == 5

    # Check that data reduction completed.
    check_data_reduction_files(tmp_path)


def test_stepwise_run_without_reference(dials_data, tmp_path):
    ssx = dials_data("cunir_serial", pathlib=True)

    args = [
        "xia2.ssx",
        "unit_cell=96.4,96.4,96.4,90,90,90",
        "space_group=P213",
        "integration.algorithm=stills",
        "d_min=2.0",
        "steps=find_spots+index+integrate",
    ]
    args.append("image=" + os.fspath(ssx / "merlin0047_1700*.cbf"))
    args.append("steps=find_spots")

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    # Now check that the processing went straight to geometry refinement
    assert not (tmp_path / "assess_crystals").is_dir()
    assert (tmp_path / "geometry_refinement").is_dir()
    reference = tmp_path / "geometry_refinement" / "refined.expt"
    assert reference.is_file()

    # Now check that the data was reimported with this reference
    assert (tmp_path / "import" / "file_input.json").is_file()
    with (tmp_path / "import" / "file_input.json").open(mode="r") as f:
        file_input = json.load(f)
        assert file_input["reference_geometry"] == os.fspath(reference)
        assert file_input["images"] == [os.fspath(ssx / "merlin0047_1700*.cbf")]
    expts = tmp_path / "import" / "imported.expt"
    assert expts.is_file()
    with_reference_identifiers = load.experiment_list(
        expts, check_format=False
    ).identifiers()

    # Check that find_spots was run with this new reference geometry
    assert (tmp_path / "batch_1").is_dir()
    sliced_expts = tmp_path / "batch_1" / "imported.expt"
    assert sliced_expts.is_file()
    sliced_identifiers = load.experiment_list(
        sliced_expts, check_format=False
    ).identifiers()
    assert with_reference_identifiers == sliced_identifiers
    check_output(tmp_path, find_spots=True)

    # Now rerun, check nothing further done if forgetting to specify geometry
    args[-1] = "steps=index"
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True)

    # Now specify geometry
    args.append("reference_geometry=geometry_refinement/refined.expt")
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True)

    # Now specify geometry
    args[-2] = "steps=integrate"
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=True)


def check_data_reduction_files(tmp_path, reindex=True, reference=False):
    assert (tmp_path / "data_reduction").is_dir()
    assert reindex is (tmp_path / "data_reduction" / "reindex").is_dir()
    assert reindex is (tmp_path / "LogFiles" / "dials.cosym.0.log").is_file()
    assert reindex is (tmp_path / "LogFiles" / "dials.cosym.0.html").is_file()
    assert (tmp_path / "data_reduction" / "scale").is_dir()
    assert (tmp_path / "data_reduction" / "merge" / "all" / "merged.mtz").is_file()
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.html").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.log").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.json").is_file()
    if reference:
        assert (tmp_path / "DataFiles" / "scaled_batch1.refl").is_file()
        assert (tmp_path / "DataFiles" / "scaled_batch1.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.scale.scaled_batch1.log").is_file()
    else:
        assert (tmp_path / "DataFiles" / "scaled.refl").is_file()
        assert (tmp_path / "DataFiles" / "scaled.expt").is_file()
        assert (tmp_path / "LogFiles" / "dials.scale.log").is_file()


def check_data_reduction_files_on_scaled_only(tmp_path, reference=False):
    assert (tmp_path / "data_reduction").is_dir()
    assert not (tmp_path / "data_reduction" / "reindex").is_dir()
    assert not (tmp_path / "LogFiles" / "dials.cosym.0.log").is_file()
    assert not (tmp_path / "LogFiles" / "dials.cosym.0.html").is_file()
    assert (tmp_path / "data_reduction" / "merge").is_dir()
    assert (tmp_path / "data_reduction" / "merge" / "all" / "merged.mtz").is_file()
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.html").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.log").is_file()
    assert (tmp_path / "LogFiles" / "dials.merge.json").is_file()


# For testing data reduction, there are a few different paths.
# Processing can be done on integrated data, only on previously scaled data,
# or on a mix of new data and previously scaled.
# Processing can be done with or without a reference pdb model
# There can be an indexing ambiguity or not

# With a reference - reindexing is done against this if idx ambiguity. New data is
# scaled. Any previously scaled data is merged in at the end.
# Without a reference - if idx ambiguity, unscaled input data is reindexed in
# batches, then all data (scaled plus unscaled) must be reindexed together in
# batch mode. Then all data is scaled together


@pytest.mark.parametrize(
    "pdb_model,idx_ambiguity",
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_ssx_reduce(dials_data, tmp_path, pdb_model, idx_ambiguity):
    """Test ssx_reduce in the case of an indexing ambiguity or not.

    Test with and without a reference model, plus processing integrated,
    scaled, and integrated+scaled data.
    """
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    if not idx_ambiguity:
        # Reindex to P432, which doesn't have an indexing ambiguity.
        result = subprocess.run(
            [
                "dials.reindex",
                f"{ssx / 'integrated.refl'}",
                f"{ssx / 'integrated.expt'}",
                "space_group=P432",
            ],
            cwd=tmp_path,
            capture_output=True,
        )
        assert not result.returncode
        assert not result.stderr.decode()
        expts = tmp_path / "reindexed.expt"
        refls = tmp_path / "reindexed.refl"
        args = [
            "xia2.ssx_reduce",
            f"{refls}",
            f"{expts}",
        ]  # note - pass as files rather than directory to test that input option
        cosym_phil = "d_min=1.8"
    else:
        args = ["xia2.ssx_reduce", f"directory={ssx}", "batch_size=2"]
        cosym_phil = "d_min=1.8\ncc_weights=None\nweights=None"
        # forcing a stupidly small batch size can cause cosym failures, so change some options
    extra_args = []
    if pdb_model:
        model = dials_data("cunir_serial", pathlib=True) / "2BW4.pdb"
        extra_args.append(f"model={str(model)}")
    # also test using scaling and cosym phil files
    scaling_phil = "reflection_selection.Isigma_range=3.0,0.0"
    with open(tmp_path / "scaling.phil", "w") as f:
        f.write(scaling_phil)
    with open(tmp_path / "cosym.phil", "w") as f:
        f.write(cosym_phil)
    extra_args.append(f"symmetry.phil={tmp_path / 'cosym.phil'}")
    extra_args.append(f"scaling.phil={tmp_path / 'scaling.phil'}")

    result = subprocess.run(args + extra_args, cwd=tmp_path, capture_output=True)
    assert not result.returncode
    assert not result.stderr.decode()
    check_data_reduction_files(tmp_path, reference=pdb_model, reindex=idx_ambiguity)

    # now run again only on previously scaled data
    pathlib.Path.mkdir(tmp_path / "reduce")
    args = (
        [
            "xia2.ssx_reduce",
            "steps=merge",
        ]
        + list((tmp_path / "DataFiles").glob("scale*"))
        + extra_args
    )
    result = subprocess.run(args, cwd=tmp_path / "reduce", capture_output=True)
    assert not result.returncode
    assert not result.stderr.decode()
    check_data_reduction_files_on_scaled_only(tmp_path / "reduce", reference=pdb_model)


def test_reduce_h5(dials_data, tmp_path):
    """Test the data reduction on data from h5 format. Use as an opportunity to test
    groupings too for h5 data."""
    ssx = dials_data("dtpb_serial_processed", pathlib=True)
    grouping_yml = """
metadata:
  well_id:
    "/dls/mx/data/nt30330/nt30330-15/VMXi-AB1698/well_39/images/image_58763.nxs" : 39
    "/dls/mx/data/nt30330/nt30330-15/VMXi-AB1698/well_42/images/image_58766.nxs" : 42
grouping:
  merge_by:
    values:
      - well_id
"""
    files = [
        ssx / "well39_batch12_integrated.expt",
        ssx / "well39_batch12_integrated.refl",
        ssx / "well42_batch6_integrated.expt",
        ssx / "well42_batch6_integrated.refl",
    ]
    with open(tmp_path / "example.yaml", "w") as f:
        f.write(grouping_yml)

    args = ["xia2.ssx_reduce", "grouping=example.yaml"] + files
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode
    assert not result.stderr.decode()
    output_names = [f"group_{i}" for i in [1, 2]]
    for n in output_names:
        assert (tmp_path / "DataFiles" / f"{n}.mtz").is_file()
        assert (tmp_path / "LogFiles" / f"dials.merge.{n}.html").is_file()

    g1_mtz = mtz.object(
        file_name=os.fspath(tmp_path / "DataFiles" / f"{output_names[0]}.mtz")
    )
    assert abs(g1_mtz.n_reflections() - 6791) < 10
    g2_mtz = mtz.object(
        file_name=os.fspath(tmp_path / "DataFiles" / f"{output_names[1]}.mtz")
    )
    assert abs(g2_mtz.n_reflections() - 10276) < 10


@pytest.mark.parametrize(
    "use_grouping",
    [True, False],
)
def test_reduce_with_grouping(dials_data, tmp_path, use_grouping):
    """Test the feature of specifying a grouping yaml file
    to define merge groups.
    """
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    ssx_data = dials_data("cunir_serial", pathlib=True)
    args = ["xia2.ssx_reduce", f"directory={ssx}"]
    extra_args = []
    model = dials_data("cunir_serial", pathlib=True) / "2BW4.pdb"
    extra_args.append(f"model={str(model)}")
    # also test using scaling and cosym phil files
    cosym_phil = "d_min=1.8"
    scaling_phil = "reflection_selection.Isigma_range=3.0,0.0"
    with open(tmp_path / "scaling.phil", "w") as f:
        f.write(scaling_phil)
    with open(tmp_path / "cosym.phil", "w") as f:
        f.write(cosym_phil)
    extra_args.append("symmetry.phil=cosym.phil")
    extra_args.append("scaling.phil=scaling.phil")

    # pretend that this is some dose series data
    if use_grouping:
        grouping = f"""
metadata:
    dose_point:
        {os.fspath(ssx_data / 'merlin0047_#####.cbf')} : "repeat=2"
grouping:
    merge_by:
        values:
            - dose_point
        """
        with open(tmp_path / "example.yaml", "w") as f:
            f.write(grouping)
        extra_args.append("grouping=example.yaml")
    else:
        extra_args.append("dose_series_repeat=2")

    result = subprocess.run(args + extra_args, cwd=tmp_path, capture_output=True)
    assert not result.returncode
    assert not result.stderr.decode()
    output_names = [f"group_{i}" if use_grouping else f"dose_{i}" for i in [1, 2]]
    for n in output_names:
        assert (tmp_path / "DataFiles" / f"{n}.mtz").is_file()
        assert (tmp_path / "LogFiles" / f"dials.merge.{n}.html").is_file()

    g1_mtz = mtz.object(
        file_name=os.fspath(tmp_path / "DataFiles" / f"{output_names[0]}.mtz")
    )
    assert abs(g1_mtz.n_reflections() - 1464) < 10
    g2_mtz = mtz.object(
        file_name=os.fspath(tmp_path / "DataFiles" / f"{output_names[1]}.mtz")
    )
    assert abs(g2_mtz.n_reflections() - 566) < 10
    assert not (tmp_path / "DataFiles" / "merged.mtz").is_file()

    # now rerun with a res limit on one group. Should be able to just process straight from
    # the group files for fast merging.
    args = ["xia2.ssx_reduce", "d_min=3.0", "steps=merge"]
    if use_grouping:
        args += list(
            (tmp_path / "data_reduction" / "merge" / "group_1").glob("group*.expt")
        )
        args += list(
            (tmp_path / "data_reduction" / "merge" / "group_1").glob("group*.refl")
        )
    else:
        args += list(
            (tmp_path / "data_reduction" / "merge" / "dose_1").glob("group*.expt")
        )
        args += list(
            (tmp_path / "data_reduction" / "merge" / "dose_1").glob("group*.refl")
        )

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode
    assert not result.stderr.decode()
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()
    merged_mtz = mtz.object(file_name=os.fspath(tmp_path / "DataFiles" / "merged.mtz"))
    assert abs(merged_mtz.n_reflections() - 372) < 10  # expect 298 from d_min=3.0


@pytest.mark.parametrize(
    ("cluster_args", "expected_results"),
    [
        (
            ["clustering.threshold=1"],
            {
                "best_unit_cell": [96.411, 96.411, 96.411, 90.0, 90.0, 90.0],
                "n_cryst": 3,
            },
        ),
        (
            [
                "central_unit_cell=96.4,96.4,96.4,90,90,90",
                "absolute_length_tolerance=0.015",
            ],
            {
                "best_unit_cell": [96.4107, 96.4107, 96.4107, 90.0, 90.0, 90.0],
                "n_cryst": 4,
            },
        ),
        (
            ["absolute_length_tolerance=0.001"],
            {
                "best_unit_cell": [96.4107, 96.4107, 96.4107, 90.0, 90.0, 90.0],
                "n_cryst": 2,
            },
        ),
    ],
)
def test_ssx_reduce_filter_options(
    dials_data, tmp_path, cluster_args: List[str], expected_results: dict
):
    ssx = dials_data("cunir_serial_processed", pathlib=True)
    args = ["xia2.ssx_reduce", f"directory={ssx}"] + cluster_args
    cosym_phil = "d_min=1.8\ncc_weights=None\nweights=None"
    with open(tmp_path / "cosym.phil", "w") as f:
        f.write(cosym_phil)
    args.append(f"symmetry.phil={tmp_path / 'cosym.phil'}")

    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_data_reduction_files(tmp_path)

    expts = load.experiment_list(tmp_path / "DataFiles" / "scaled.expt")
    assert len(expts) == expected_results["n_cryst"]

    assert list(determine_best_unit_cell(expts).parameters()) == pytest.approx(
        expected_results["best_unit_cell"]
    )


def test_on_sacla_data(dials_data, tmp_path):

    sacla_path = dials_data("image_examples", pathlib=True)
    image = sacla_path / "SACLA-MPCCD-run266702-0-subset.h5"
    # NB need to set gain, as using reference from detector overwrites gain to 1
    # error with reference geom file? Alt is to manually set detector distance in
    # import.
    find_spots_phil = """spotfinder.threshold.dispersion.gain=10"""
    fp = tmp_path / "sf.phil"
    with open(fp, "w") as f:
        f.write(find_spots_phil)
    geometry = (
        sacla_path / "SACLA-MPCCD-run266702-0-subset-refined_experiments_level1.json"
    )
    args = [
        "xia2.ssx",
        f"image={image}",
        f"reference_geometry={geometry}",
        "space_group = P43212",
        "unit_cell=78.9,78.9,38.1,90,90,90",
        "min_spot_size=2",
        "integration.algorithm=stills",
        f"spotfinding.phil={fp}",
    ]
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr
    check_output(tmp_path, find_spots=True, index=True, integrate=True)

    imported = load.experiment_list(
        tmp_path / "import" / "imported.expt", check_format=False
    )
    assert len(imported) == 4
    assert len(imported.imagesets()) == 1
    assert (tmp_path / "DataFiles" / "merged.mtz").is_file()


def test_on_sacla_data_slice(dials_data, tmp_path):
    "Just import to check the slicing functionality"
    sacla_path = dials_data("image_examples", pathlib=True)
    image = sacla_path / "SACLA-MPCCD-run266702-0-subset.h5:3:4"
    geometry = (
        sacla_path / "SACLA-MPCCD-run266702-0-subset-refined_experiments_level1.json"
    )
    find_spots_phil = """spotfinder.threshold.dispersion.gain=10"""
    fp = tmp_path / "sf.phil"
    with open(fp, "w") as f:
        f.write(find_spots_phil)
    args = [
        "xia2.ssx",
        f"image={image}",
        f"reference_geometry={geometry}",
        "space_group = P43212",
        "unit_cell=78.9,78.9,38.1,90,90,90",
        "min_spot_size=2",
        "steps=find_spots+index",
        f"spotfinding.phil={fp}",
        "max_lattices=1",
    ]
    result = subprocess.run(args, cwd=tmp_path, capture_output=True)
    assert not result.returncode and not result.stderr

    imported = load.experiment_list(
        tmp_path / "import" / "imported.expt", check_format=False
    )
    assert len(imported) == 2
    assert len(imported.imagesets()) == 1

    indexed = load.experiment_list(
        tmp_path / "batch_1" / "indexed.expt", check_format=False
    )

    assert indexed[0].scan.get_image_range() == (3, 3)  # i.e. the third image
