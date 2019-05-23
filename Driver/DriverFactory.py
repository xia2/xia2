# DriverFactory.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 24th May 2006
#
# A factory for Driver implementations.
#
# At the moment this will instantiate
#
# SimpleDriver, ScriptDriver, QSubDriver, InteractiveDriver
#
# instances only.
#

from __future__ import absolute_import, division, print_function

import os

# another factory to delegate to
from xia2.Driver.ClusterDriverFactory import ClusterDriverFactory
from xia2.Driver.InteractiveDriver import InteractiveDriver
from xia2.Driver.QSubDriver import QSubDriver
from xia2.Driver.ScriptDriver import ScriptDriver
from xia2.Driver.SimpleDriver import SimpleDriver


class _DriverFactory(object):
    def __init__(self):
        self._driver_type = "simple"

        self._implemented_types = [
            "simple",
            "script",
            "interactive",
            "qsub",
            "cluster.sge",
        ]

        # should probably write a message or something explaining
        # that the following Driver implementation is being used

        if "XIA2CORE_DRIVERTYPE" in os.environ:
            self.set_driver_type(os.environ["XIA2CORE_DRIVERTYPE"])

    def set_driver_type(self, driver_type):
        """Set the kind of driver this factory should produce."""
        if driver_type not in self._implemented_types:
            raise RuntimeError("unimplemented driver class: %s" % driver_type)

        self._driver_type = driver_type

    def get_driver_type(self):
        return self._driver_type

    def Driver(self, driver_type=None):
        """Create a new Driver instance, optionally providing the
        type of Driver we want."""

        if not driver_type:
            driver_type = self._driver_type

        if "cluster" in driver_type:
            return ClusterDriverFactory.Driver(driver_type)

        driver_class = {
            "simple": SimpleDriver,
            "script": ScriptDriver,
            "interactive": InteractiveDriver,
            "qsub": QSubDriver,
        }.get(driver_type)
        if driver_class:
            return driver_class()

        raise RuntimeError('Driver class "%s" unknown' % driver_type)


DriverFactory = _DriverFactory()
