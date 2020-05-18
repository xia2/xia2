import xia2.Modules.CctbxFrenchWilson
from xia2.Driver.DefaultDriver import DefaultDriver


def FrenchWilson(DriverType=None):
    """A factory for FrenchWilsonWrapper classes."""

    class FrenchWilsonWrapper(DefaultDriver):
        """A wrapper for cctbx French and Wilson analysis."""

        def __init__(self):
            super().__init__()

            self._executable = "cctbx_FrenchWilson"
            self._outbuffer = []

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

        def set_hklin(self, hklin):
            self._hklin = hklin

        def get_hklin(self):
            return self._hklin

        def set_hklout(self, hklout):
            self._hklout = hklout

        def get_hklout(self):
            return self._hklout

        def check_hklout(self):
            return self.checkHklout()

        def get_xmlout(self):
            return self._xmlout

        def truncate(self):
            """Actually perform the truncation procedure."""

            self.add_command_line(self._hklin)
            self.add_command_line("hklout=%s" % self._hklout)
            if self._anomalous:
                self.add_command_line("anomalous=true")
            else:
                self.add_command_line("anomalous=false")

            output = xia2.Modules.CctbxFrenchWilson.do_french_wilson(
                self._hklin, self._hklout, self._anomalous
            )
            self._outbuffer = output.splitlines(True)

            self.close_wait()

            lines = self.get_all_output()
            for i, line in enumerate(lines):
                if "ML estimate of overall B value:" in line:
                    self._b_factor = float(lines[i + 1].strip().split()[0])

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

        def start(self):
            pass

        def close(self):
            pass

        def _output(self):
            try:
                return self._outbuffer.pop(0)
            except IndexError:
                return ""

    return FrenchWilsonWrapper()
