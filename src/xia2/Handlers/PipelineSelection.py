#!/usr/bin/env python
# PipelineSelection.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A handler to manage the selection of pipelines through which to run xia2,
# for instance what indexer to use, what integrater and what scaler.
# This will look for a file preferences.xia in ~/.xia2 or equivalent,
# and the current working directory.


import os


def check(key, value):
    """Check that this thing is allowed to have this value."""

    # this should be current!

    allowed_indexers = ["xds", "xdsii", "dials"]
    allowed_integraters = ["xdsr", "xds", "dials"]
    allowed_refiners = ["xds", "dials"]
    allowed_scalers = ["ccp4a", "xdsa", "dials"]

    if key == "indexer":
        if value not in allowed_indexers:
            raise RuntimeError("indexer %s unknown" % value)
        return value

    if key == "refiner":
        if value not in allowed_refiners:
            raise RuntimeError("refiner %s unknown" % value)
        return value

    if key == "integrater":
        if value not in allowed_integraters:
            raise RuntimeError("integrater %s unknown" % value)
        if value == "xds":
            return "xdsr"
        return value

    if key == "scaler":
        if value not in allowed_scalers:
            raise RuntimeError("scaler %s unknown" % value)
        return value


preferences = {}


def get_preferences():
    global preferences

    if preferences == {}:
        _search_for_preferences()

    return preferences


def add_preference(key, value):
    """Add in run-time a preference."""

    global preferences

    value = check(key, value)

    if key in preferences:
        if preferences[key] != value:
            raise RuntimeError(
                "setting %s to %s: already %s" % (key, value, preferences[key])
            )

    preferences[key] = value


def _search_for_preferences():
    """Search for a preferences file, first in HOME then here."""

    global preferences

    if os.name == "nt":
        homedir = os.path.join(os.environ["HOMEDRIVE"], os.environ["HOMEPATH"])
        xia2dir = os.path.join(homedir, "xia2")
    else:
        homedir = os.environ["HOME"]
        xia2dir = os.path.join(homedir, ".xia2")

    if os.path.exists(os.path.join(xia2dir, "preferences.xia")):
        preferences = _parse_preferences(
            os.path.join(xia2dir, "preferences.xia"), preferences
        )

    # look also in current working directory

    if os.path.exists(os.path.join(os.getcwd(), "preferences.xia")):
        preferences = _parse_preferences(
            os.path.join(os.getcwd(), "preferences.xia"), preferences
        )

    return preferences


def _parse_preferences(filename, preferences):
    """Parse preferences to the dictionary."""

    with open(filename) as fh:
        for line in fh.readlines():

            # all lower case
            line = line.lower()

            # ignore comment lines
            if line[0] == "!" or line[0] == "#" or not line.split():
                continue

            key = line.split(":")[0].strip()
            value = line.split(":")[1].strip()

            value = check(key, value)

            add_preference(key, value)

    return preferences


if __name__ == "__main__":

    print(_search_for_preferences())
