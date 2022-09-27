from __future__ import annotations

from xia2.Modules.SSX.yml_handling import full_parse

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
