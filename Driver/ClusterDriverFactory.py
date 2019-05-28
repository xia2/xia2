#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 19th June 2006
#
# A DriverFactory for cluster-specific driver instances.
# At the moment this supports the following machines:
#
# Linux/Sun Grid Engine
#
#

from __future__ import absolute_import, division, print_function

import os

from xia2.Driver.SunGridEngineClusterDriver import SunGridEngineClusterDriver


class _ClusterDriverFactory(object):
    def __init__(self):
        self._driver_type = "cluster.sge"

        self._implemented_types = ["cluster.sge"]

        # should probably write a message or something explaining
        # that the following Driver implementation is being used

        if "XIA2CORE_DRIVERTYPE" in os.environ:
            if "cluster" in os.environ["XIA2CORE_DRIVERTYPE"]:
                self.setDriver_type(os.environ["XIA2CORE_DRIVERTYPE"])

    def set_driver_type(self, driver_type):
        return self.setDriver_type(driver_type)

    def setDriver_type(self, driver_type):
        """Set the kind of driver this factory should produce."""

        if driver_type not in self._implemented_types:
            raise RuntimeError("unimplemented driver class: %s" % driver_type)

        self._driver_type = driver_type

    def Driver(self, driver_type=None):
        """Create a new Driver instance, optionally providing the
        type of Driver we want."""

        if not driver_type:
            driver_type = self._driver_type

        if driver_type == "cluster.sge":
            return SunGridEngineClusterDriver()

        raise RuntimeError('Driver class "%s" unknown' % driver_type)


ClusterDriverFactory = _ClusterDriverFactory()
