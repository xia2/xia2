from __future__ import annotations

from xia2.Modules.SSX.yml_handling import (
    determine_groups,
    files_to_groups,
    full_parse,
    yml_to_filesdict,
)

tst_yml = """
---
images:
  - "master1.h5"
  - "master2.h5"
metadata:
  timepoint:
    master1.h5 : "meta.h5:/timepoint"
    master2.h5 : "meta2.h5:/timepoint"
  wavelength:
    master1.h5 : 0.5
    master2.h5 : 0.7
structure: # this informs the structure of the data processing.
  merge_by:
    values:
      - timepoint
      - wavelength
    tolerances:
      - 0.1
      - 0.001
  resolve_by:
    values:
      - timepoint
    tolerances:
      - 0.2
"""

tst_yml_2 = """
---
images:
  - "master1.h5"
metadata:
  timepoint:
    master1.h5 : 1
structure:
  merge_by:
    values:
      - timepoint
    tolerances:
      - 0.1
"""


def test_yml_parsing():
    parsed = full_parse(tst_yml)
    assert list(parsed.groupings.keys()) == ["merge_by", "resolve_by"]
    assert parsed.groupings["merge_by"].tolerances == {
        "timepoint": 0.1,
        "wavelength": 0.001,
    }
    assert parsed.groupings["merge_by"].metadata_names == {"timepoint", "wavelength"}
    assert parsed.groupings["resolve_by"].tolerances == {"timepoint": 0.2}
    assert parsed.groupings["resolve_by"].metadata_names == {"timepoint"}


import mock


def mock_expt(index=0):
    expt = mock.Mock()
    expt.identifier = str(index)
    expt.imageset.paths.return_value = ["master1.h5"]
    expt.imageset.indices.return_value = [index]


def test_yml_to_filesdict():

    from pathlib import Path

    cwd = Path.cwd()
    import numpy as np

    vals = np.array([0, 1, 2, 3, 4, 5, 6, 7])
    import h5py

    hf = h5py.File("meta.h5", "w")
    hf.create_dataset("timepoint", data=vals)
    hf.close()

    from dials.array_family import flex
    from dxtbx.model import Experiment, ExperimentList

    from xia2.Modules.SSX.data_reduction_definitions import FilePair

    elist = ExperimentList([Experiment(identifier=f"{i}") for i in range(0, 8)])
    elist.as_file(cwd / "test.expt")
    refls = flex.reflection_table()
    refls["id"] = flex.int(list(range(0, 8)))
    for i in range(0, 8):
        refls.experiment_identifiers()[i] = str(i)
    refls.as_file(cwd / "test.refl")
    data = [FilePair(cwd / "test.expt", cwd / "test.refl")]
    parsed = full_parse(tst_yml_2)
    yml_to_filesdict(cwd, parsed, data, grouping="merge_by")


import numpy as np


def test_assign_groups():
    metadata = {
        "img1": {
            "tp": 1.0,
            "wl": 0.5,
        },
        "img2": {
            "tp": np.array([1, 2, 3, 4]),
            "wl": 0.6,
        },
    }
    tolerances = {"tp": 0.1, "wl": 0.01}
    groups = determine_groups(metadata, ["tp", "wl"], tolerances)

    assert len(groups) == 5
    assert groups[0] == {
        "tp": {"min": 1.0, "max": 1.1},
        "wl": {"min": 0.5, "max": 0.51},
    }
    assert groups[1] == {
        "tp": {"min": 1.0, "max": 1.1},
        "wl": {"min": 0.6, "max": 0.61},
    }
    assert groups[2] == {
        "tp": {"min": 2.0, "max": 2.1},
        "wl": {"min": 0.6, "max": 0.61},
    }
    assert groups[3] == {
        "tp": {"min": 3.0, "max": 3.1},
        "wl": {"min": 0.6, "max": 0.61},
    }
    assert groups[4] == {
        "tp": {"min": 4.0, "max": 4.1},
        "wl": {"min": 0.6, "max": 0.61},
    }

    img_file_to_groups = files_to_groups(metadata, groups)
    assert img_file_to_groups["img1"]["groups"] == [0]
    assert img_file_to_groups["img2"]["groups"] == [1, 2, 3, 4]

    metadata = {
        "img1": {
            "tp": np.array([1, 1, 2, 2]),
            "wl": 0.5,
        },
        "img2": {
            "tp": np.array([4, 4, 5, 5]),
            "wl": 0.6,
        },
    }
    tolerances = {"tp": 1.5, "wl": 0.01}
    groups = determine_groups(metadata, ["tp", "wl"], tolerances)

    assert len(groups) == 2
    assert groups[0] == {
        "tp": {"min": 1.0, "max": 2.5},
        "wl": {"min": 0.5, "max": 0.51},
    }
    assert groups[1] == {
        "tp": {"min": 4.0, "max": 5.5},
        "wl": {"min": 0.6, "max": 0.61},
    }
    img_file_to_groups = files_to_groups(metadata, groups)
    assert img_file_to_groups["img1"]["groups"] == [0]
    assert img_file_to_groups["img2"]["groups"] == [1]
