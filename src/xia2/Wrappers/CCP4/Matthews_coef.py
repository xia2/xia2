import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory


def Matthews_coef(DriverType=None):
    """A factory for Matthews_coefWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class Matthews_coefWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Matthews_coef, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(
                os.path.join(os.environ.get("CBIN", ""), "matthews_coef")
            )

            self._nmol = 1
            self._nres = 0
            self._cell = None
            self._spacegroup = None

            # results

            self._solvent = 0.0

            return

        # setters follow

        def set_nmol(self, nmol):
            self._nmol = nmol
            return

        def set_nres(self, nres):
            self._nres = nres
            return

        def set_cell(self, cell):
            self._cell = cell
            return

        def set_spacegroup(self, spacegroup):
            self._spacegroup = spacegroup
            return

        def compute_solvent(self):

            self.start()

            self.input("cell %f %f %f %f %f %f" % tuple(self._cell))

            # cannot cope with spaces in the spacegroup!

            self.input("symmetry %s" % self._spacegroup.replace(" ", ""))
            self.input("nres %d" % self._nres)
            self.input("nmol %d" % self._nmol)

            self.close_wait()

            self.check_for_errors()
            self.check_ccp4_errors()

            # get the useful information out from here...

            for line in self.get_all_output():
                if "Assuming protein density" in line:
                    self._solvent = 0.01 * float(line.split()[-1])

            return

        def get_solvent(self):
            return self._solvent

    return Matthews_coefWrapper()
