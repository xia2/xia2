#!/usr/bin/env python


from __future__ import absolute_import, division, print_function

from xia2.Driver.DriverFactory import DriverFactory


def Xtriage(DriverType=None):
    """A factory for the Xtriage wrappers."""

    DriverInstance = DriverFactory.Driver("simple")

    class XtriageWrapper(DriverInstance.__class__):
        """A wrapper class for phenix.xtriage."""

        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("mmtbx.xtriage")

            self._mtz = None

            return

        def set_mtz(self, mtz):
            self._mtz = mtz
            return

        def run(self):
            import os

            assert self._mtz is not None
            assert os.path.isfile(self._mtz)

            self.add_command_line(self._mtz)

            self.start()
            self.close_wait()
            self.check_for_errors()

    return XtriageWrapper()
