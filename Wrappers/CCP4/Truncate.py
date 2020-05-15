import logging
import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import transpose_loggraph
from xia2.Wrappers.CCP4.Ctruncate import Ctruncate
from xia2.Wrappers.XIA.FrenchWilson import FrenchWilson

logger = logging.getLogger("xia2.Wrappers.CCP4.Truncate")


def Truncate(DriverType=None):
    """A factory for TruncateWrapper classes."""

    if PhilIndex.params.ccp4.truncate.program == "ctruncate":
        return Ctruncate(DriverType)
    elif PhilIndex.params.ccp4.truncate.program == "cctbx":
        return FrenchWilson(DriverType)

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class TruncateWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Truncate, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "truncate"))

            self._anomalous = False
            self._nres = 0

            # should we do wilson scaling?
            self._wilson = True

            self._b_factor = 0.0
            self._moments = None

            self._wilson_fit_grad = 0.0
            self._wilson_fit_grad_sd = 0.0
            self._wilson_fit_m = 0.0
            self._wilson_fit_m_sd = 0.0
            self._wilson_fit_range = None

            # numbers of reflections in and out, and number of absences
            # counted

            self._nref_in = 0
            self._nref_out = 0
            self._nabsent = 0

            self._xmlout = None

        def set_anomalous(self, anomalous):
            self._anomalous = anomalous

        def set_wilson(self, wilson):
            """Set the use of Wilson scaling - if you set this to False
            Wilson scaling will be switched off..."""
            self._wilson = wilson

        def get_xmlout(self):
            return self._xmlout

        def truncate(self):
            """Actually perform the truncation procedure."""

            self.check_hklin()
            self.check_hklout()

            self.start()

            if self._anomalous:
                self.input("anomalous yes")
            else:
                self.input("anomalous no")

            if self._nres:
                self.input("nres %d" % self._nres)

            if not self._wilson:
                self.input("scale 1")

            self.close_wait()

            try:
                self.check_for_errors()
                self.check_ccp4_errors()

            except RuntimeError:
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass

                raise RuntimeError("truncate failure")

            # parse the output for interesting things, including the
            # numbers of reflections in and out (isn't that a standard CCP4
            # report?) and the number of absent reflections.

            self._nref_in, self._nref_out = self.read_nref_hklin_hklout(
                self.get_all_output()
            )

            # FIXME guess I should be reading this properly...
            self._nabsent = self._nref_in - self._nref_out

            for line in self.get_all_output():
                if "Least squares straight line gives" in line:
                    list = line.replace("=", " ").split()
                    if "***" not in list[6]:
                        self._b_factor = float(list[6])
                    else:
                        logger.debug("no B factor available")

                if "LSQ Line Gradient" in line:
                    self._wilson_fit_grad = float(line.split()[-1])
                    if self._wilson_fit_grad > 0:
                        logger.debug("Positive gradient but not much wilson plot")

                if "Uncertainty in Gradient" in line:
                    self._wilson_fit_grad_sd = float(line.split()[-1])
                if "X Intercept" in line:
                    self._wilson_fit_m = float(line.split()[-1])
                if "Uncertainty in Intercept" in line:
                    self._wilson_fit_m_sd = float(line.split()[-1])
                if "Resolution range" in line:
                    self._wilson_fit_range = list(map(float, line.split()[-2:]))

            results = self.parse_ccp4_loggraph()
            moments = transpose_loggraph(
                results["Acentric Moments of E for k = 1,3,4,6,8"]
            )

            # keys we want in this are "Resln_Range" "1/resol^2" and
            # MomentZ2. The last of these should be around two, but is
            # likely to be a little different to this.
            self._moments = moments

        def get_b_factor(self):
            return self._b_factor

        def get_wilson_fit(self):
            return (
                self._wilson_fit_grad,
                self._wilson_fit_grad_sd,
                self._wilson_fit_m,
                self._wilson_fit_m_sd,
            )

        def get_wilson_fit_range(self):
            return self._wilson_fit_range

        def get_moments(self):
            return self._moments

        def get_nref_in(self):
            return self._nref_in

        def get_nref_out(self):
            return self._nref_out

        def get_nabsent(self):
            return self._nabsent

        def read_nref_hklin_hklout(self, records):
            """Look to see how many reflections came in through HKLIN, and
            how many went out again in HKLOUT."""

            nref_in = 0
            nref_out = 0

            current_logical = None

            for record in records:
                if "Logical Name" in record:
                    current_logical = record.split()[2]
                    assert current_logical in ["HKLIN", "HKLOUT", "SYMINFO"]

                if "Number of Reflections" in record:
                    if current_logical == "HKLIN":
                        nref_in = int(record.split()[-1])
                    elif current_logical == "HKLOUT":
                        nref_out = int(record.split()[-1])

            return nref_in, nref_out

    return TruncateWrapper()
