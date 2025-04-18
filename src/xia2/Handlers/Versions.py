from __future__ import annotations

import functools
import re
import subprocess
from collections.abc import Mapping

import dials.util.version

import xia2.XIA2Version


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


@functools.cache
def get_xia2_version():
    return xia2.XIA2Version.Version


@functools.cache
def get_xds_version():
    try:
        result = subprocess.run(
            ["xds"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
        )
    except OSError:
        pass
    version = re.search(rb"BUILT=([0-9]+)\)", result.stdout)
    if version:
        return int(version.groups()[0])
    return None


@functools.cache
def get_aimless_version():
    result = subprocess.run(
        ["aimless", "--no-input"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    version = re.search(rb"version\s\d+\.\d+\.\d+", result.stdout)
    if version:
        return version.group().decode("utf-8").split(" ")[1]
    return None


@functools.cache
def get_pointless_version():
    result = subprocess.run(
        ["pointless"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )
    version = re.search(rb"version\s\d+\.\d+\.\d+", result.stdout)
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
