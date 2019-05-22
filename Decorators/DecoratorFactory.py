#!/usr/bin/env python
# DecoratorFactory.py
#
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 31st May 2006
#
# A factory to provide access to the decorator classes. So far this is
#
# "ccp4" -> A CCP4 Decorator
#

from __future__ import absolute_import, division, print_function

from xia2.Decorators.CCP4Decorator import CCP4DecoratorFactory


class _DecoratorFactory(object):
    """A factory singleton to dress Driver instances with decoration
    for specific program suites, for instance CCP4."""

    def __init__(self):
        self._type = "ccp4"

    def Decorate(self, DriverInstance, typ=None):
        """Decorate DriverInstance as type or self._type if not specified."""

        if typ is None:
            typ = self._type

        if typ == "ccp4":
            return CCP4DecoratorFactory(DriverInstance)

        raise RuntimeError('unknown decorator class "%s"' % typ)


DecoratorFactory = _DecoratorFactory()

if __name__ == "__main__":
    # run some kind of test here
    raise RuntimeError("no test available")
