from __future__ import annotations

import iotbx.phil
import pytest

from xia2.Modules.SSX.data_reduction_definitions import ReductionParams
from xia2.Modules.SSX.xia2_ssx_reduce import full_phil_str

phil_scope = iotbx.phil.parse(full_phil_str)


def _reduction_params(phil_str):
    params = phil_scope.fetch(iotbx.phil.parse(phil_str)).extract()
    return ReductionParams.from_phil(params)


@pytest.mark.parametrize(
    "phil_str",
    ["series_repeat=first,second,last", "series_repeat='first second last'"],
)
def test_series_repeat(phil_str):
    """Test that the names can be given as a comma or space separated list,
    and that the repeat is deduced from the number of names."""
    reduction_params = _reduction_params(phil_str)
    assert reduction_params.series_repeat_names == ["first", "second", "last"]
    assert reduction_params.dose_series_repeat == 3


def test_dose_series_repeat():
    reduction_params = _reduction_params("dose_series_repeat=3")
    assert reduction_params.series_repeat_names is None
    assert reduction_params.dose_series_repeat == 3


@pytest.mark.parametrize(
    ("phil_str", "expected_names"),
    [
        ("series_repeat=dose,dose,apo", ["dose_1", "dose_2", "apo"]),
        ("series_repeat=apo,dose,dose", ["apo", "dose_1", "dose_2"]),
        (
            "series_repeat=" + ",".join(["dose"] * 12),
            [f"dose_{i:02d}" for i in range(1, 13)],
        ),
    ],
)
def test_repeated_series_repeat_names(phil_str, expected_names):
    """Repeated names are numbered in order, padded to the number of digits
    needed for that name."""
    reduction_params = _reduction_params(phil_str)
    assert reduction_params.series_repeat_names == expected_names
    assert reduction_params.dose_series_repeat == len(expected_names)


@pytest.mark.parametrize(
    "phil_str",
    [
        "series_repeat=first",  # need at least two names
        "series_repeat=first,'second/last'",  # no path separators allowed
        "series_repeat=dose,dose,dose_1",  # numbering gives a duplicate name
        "series_repeat=first,second\ndose_series_repeat=2",  # mutually exclusive
    ],
)
def test_invalid_series_repeat(phil_str):
    with pytest.raises(ValueError):
        _reduction_params(phil_str)
