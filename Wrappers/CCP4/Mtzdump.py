#!/usr/bin/env python

from __future__ import absolute_import, division, print_function


def Mtzdump(DriverType=None):
    """A factory for MtzdumpWrapper classes."""

    from xia2.Modules.Mtzdump import Mtzdump as _Mtzdump

    return _Mtzdump()
