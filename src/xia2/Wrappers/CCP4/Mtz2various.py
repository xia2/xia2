import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory


def Mtz2various(DriverType=None):
    """A factory for Mtz2variousWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class Mtz2variousWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Mtz2various, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "mtz2various"))

            # this will allow extraction of specific intensities
            # from a multi-set reflection file
            self._dataset_suffix = ""

        def set_suffix(self, suffix):
            if suffix:
                self._dataset_suffix = "_%s" % suffix
            else:
                self._dataset_suffix = suffix

        def convert(self):
            """Convert the input reflection file to .sca format."""

            self.check_hklin()
            self.check_hklout()

            self.start()

            labin = "I(+)=I(+){suffix} SIGI(+)=SIGI(+){suffix} ".format(
                suffix=self._dataset_suffix,
            )
            labin += "I(-)=I(-){suffix} SIGI(-)=SIGI(-){suffix}".format(
                suffix=self._dataset_suffix,
            )

            self.input("output scal")
            self.input("labin " + labin)

            self.close_wait()

            self.get_all_output()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError:
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass

        def convert_shelx(self, unmerged=False):
            """Convert the input reflection file to SHELX hklf4 format."""

            self.check_hklin()
            self.check_hklout()

            self.start()

            if self._dataset_suffix or unmerged:
                labin = "I=I{suffix} SIGI=SIGI{suffix}".format(
                    suffix=self._dataset_suffix,
                )

            else:
                labin = "I=IMEAN SIGI=SIGIMEAN"

            self.input("output shelx")
            self.input("labin " + labin)

            self.close_wait()

            self.get_all_output()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError:
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass

    return Mtz2variousWrapper()
