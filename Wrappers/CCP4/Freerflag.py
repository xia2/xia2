import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Citations import Citations
from xia2.Modules.FindFreeFlag import FindFreeFlag


def Freerflag(DriverType=None):
    """A factory for FreerflagWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class FreerflagWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Freerflag, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)
            Citations.cite("ccp4")

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "freerflag"))

            self._free_fraction = 0.05

        def set_free_fraction(self, free_fraction):
            self._free_fraction = free_fraction

        def add_free_flag(self):
            self.check_hklin()
            self.check_hklout()

            self.start()
            self.input("freerfrac %.3f" % self._free_fraction)
            self.close_wait()
            self.check_for_errors()
            self.check_ccp4_errors()

        def complete_free_flag(self):
            self.check_hklin()
            self.check_hklout()
            free_column = FindFreeFlag(self.get_hklin())
            self.start()
            self.input("freerfrac %.3f" % self._free_fraction)
            self.input("complete FREE=%s" % free_column)
            self.close_wait()
            self.check_for_errors()
            self.check_ccp4_errors()

    return FreerflagWrapper()
