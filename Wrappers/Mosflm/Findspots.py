#!/usr/bin/env python

from __future__ import absolute_import, division, print_function


def Findspots(DriverType=None):
    """A factory for FindspotsWrapper(ipmosflm) classes."""

    from xia2.Driver.DriverFactory import DriverFactory

    DriverInstance = DriverFactory.Driver(DriverType)

    class FindspotsWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)

            import os

            self.set_executable(os.path.join(os.environ["CCP4"], "bin", "ipmosflm"))

        def __call__(self, fp, images):
            from xia2.Handlers.Streams import Debug

            Debug.write("Running mosflm to find spots")

            self.start()
            self.input('template "%s"' % fp.get_template())
            self.input('directory "%s"' % fp.get_directory())
            self.input("beam %f %f" % fp.get_beam_centre())
            self.input("distance %f" % fp.get_distance())
            self.input("wavelength %f" % fp.get_wavelength())
            self.input("findspots file spots.dat")
            for i in images:
                self.input("findspots find %d" % i)
            self.input("go")
            self.close_wait()

            # FIXME I should really gather some interesting information about
            # the spot finding in here...

            import os

            return os.path.join(self.get_working_directory(), "spots.dat")

    return FindspotsWrapper()
