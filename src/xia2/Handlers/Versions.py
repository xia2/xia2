import re
from collections.abc import Mapping

import procrunner

import xia2.XIA2Version
import dials.util.version


class _Versions(Mapping):

    """Mapping of program names and functions to determine their versions."""

    def __init__(self, *args, **kw):
        self._raw_dict = dict(*args, **kw)

    def __getitem__(self, key):
        func = self._raw_dict[key]
        return func()

    def __iter__(self):
        return iter(self._raw_dict)

    def __len__(self):
        return len(self._raw_dict)

    def __eq__(self, other):
        if isinstance(other, _Versions):
            return all(x == y for x, y in zip(self, other))
        return super().__eq__(other)

    def __ne__(self, other):
        return not (self == other)


def get_xia2_version():
    return xia2.XIA2Version.Version


def get_xds_version():
    try:
        result = procrunner.run(["xds"], print_stdout=False, print_stderr=False)
    except OSError:
        pass
    version = re.search(br"BUILT=([0-9]+)\)", result.stdout)
    if version:
        return int(version.groups()[0])
    return None


def get_aimless_version():
    result = procrunner.run(
        ["aimless", "--no-input"], print_stdout=False, print_stderr=False
    )
    version = re.search(br"version\s\d+\.\d+\.\d+", result.stdout)
    if version:
        return version.group().decode("utf-8").split(" ")[1]
    return None


def get_pointless_version():
    result = procrunner.run(
        ["pointless", "--no-input"], print_stdout=False, print_stderr=False
    )
    version = re.search(br"version\s\d+\.\d+\.\d+", result.stdout)
    if version:
        return version.group().decode("utf-8").split(" ")[1]
    return None


versions = _Versions(
    {
        "xia2": get_xia2_version,
        "dials": dials.util.version.dials_version,
        "xds": get_xds_version,
        "aimless": get_aimless_version,
        "pointless": get_pointless_version,
    }
)
