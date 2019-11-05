#!/usr/bin/env python
# XDS_ASCII.py
# Maintained by G.Winter
#
#   Copyright (C) 2008 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 22nd February 2008
#
# Code for manipulating XDS_ASCII files from XDS CORRECT.
#

from __future__ import absolute_import, division, print_function

import os


def remove_misfits(xdsin, xdsout):
    """Read through the XDS_ASCII input file and remove the misfit
    reflections (SD < 0.0) - write out the remains to xdsout."""

    if xdsin == xdsout:
        raise RuntimeError("xdsin and xdsout same file")

    if not os.path.exists(xdsin):
        raise RuntimeError("xdsin does not exist")

    ignored = 0

    with open(xdsin, "r") as fin, open(xdsout, "w") as fout:
        for record in fin.readlines():
            if not record.strip():
                continue
            if record[0] == "!":
                fout.write(record)
                continue
            values = list(map(float, record.split()))
            if values[4] > 0.0:
                fout.write(record)
                continue
            else:
                ignored += 1

    return ignored
