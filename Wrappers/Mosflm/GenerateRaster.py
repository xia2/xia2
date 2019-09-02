#!/usr/bin/env python

from __future__ import absolute_import, division, print_function


def GenerateRaster(DriverType=None):
    """A factory for GenerateRasterWrapper(ipmosflm) classes."""

    from xia2.Driver.DriverFactory import DriverFactory

    DriverInstance = DriverFactory.Driver(DriverType)

    class GenerateRasterWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)

            import os

            self.set_executable(os.path.join(os.environ["CCP4"], "bin", "ipmosflm"))

        def __call__(self, indxr, images):
            from xia2.Handlers.Streams import Debug

            Debug.write("Running mosflm to generate RASTER, SEPARATION")

            self.start()
            self.input('template "%s"' % indxr.get_template())
            self.input('directory "%s"' % indxr.get_directory())
            self.input("beam %f %f" % indxr.get_indexer_beam_centre())
            self.input("distance %f" % indxr.get_indexer_distance())
            self.input("wavelength %f" % indxr.get_wavelength())
            self.input("findspots file spots.dat")
            for i in images:
                self.input("findspots find %d" % i)
            self.input("go")

            self.close_wait()

            p = {}

            # scrape from the output the values we want...

            for o in self.get_all_output():
                if "parameters have been set to" in o:
                    p["raster"] = map(int, o.split()[-5:])
                if "(currently SEPARATION" in o:
                    p["separation"] = map(float, o.replace(")", "").split()[-2:])

            return p

    return GenerateRasterWrapper()
