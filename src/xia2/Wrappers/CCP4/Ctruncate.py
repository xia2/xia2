import logging
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Citations import Citations
from xia2.lib.bits import transpose_loggraph

logger = logging.getLogger("xia2.Wrappers.CCP4.Ctruncate")


def Ctruncate(DriverType=None):
    """A factory for CtruncateWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class CtruncateWrapper(DriverInstance.__class__):
        """A wrapper for Ctruncate, using the regular Driver."""

        def __init__(self):
            # generic things
            DriverInstance.__class__.__init__(self)
            Citations.cite("ccp4")

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "ctruncate"))

            self._anomalous = False
            self._nres = 0

            self._b_factor = 0.0
            self._moments = None

            # numbers of reflections in and out, and number of absences
            # counted

            self._nref_in = 0
            self._nref_out = 0
            self._nabsent = 0

            self._xmlout = None

        def set_hklin(self, hklin):
            self._hklin = hklin

        def set_hklout(self, hklout):
            self._hklout = hklout

        def set_nres(self, nres):
            self._nres = nres

        def set_anomalous(self, anomalous):
            self._anomalous = anomalous

        def get_xmlout(self):
            return self._xmlout

        def truncate(self):
            """Actually perform the truncation procedure."""

            if not self._hklin:
                raise RuntimeError("hklin not defined")
            if not self._hklout:
                raise RuntimeError("hklout not defined")

            self.add_command_line("-hklin")
            self.add_command_line(self._hklin)
            self.add_command_line("-hklout")
            self.add_command_line(self._hklout)

            if self._nres:
                self.add_command_line("-nres")
                self.add_command_line("%d" % self._nres)

            if self._anomalous:
                self.add_command_line("-colano")
                self.add_command_line("/*/*/[I(+),SIGI(+),I(-),SIGI(-)]")

            self.add_command_line("-colin")
            self.add_command_line("/*/*/[IMEAN,SIGIMEAN]")

            self._xmlout = os.path.join(
                self.get_working_directory(), "%d_truncate.xml" % self.get_xpid()
            )
            self.add_command_line("-xmlout")
            self.add_command_line(self._xmlout)

            self.start()
            self.close_wait()

            try:
                self.check_for_errors()

            except RuntimeError as e:
                try:
                    os.remove(self._hklout)
                except Exception:
                    pass

                logger.debug(str(e))
                raise RuntimeError("ctruncate failure")

            nref = 0

            for record in self.get_all_output():
                if "Number of reflections:" in record:
                    nref = int(record.split()[-1])

                if "Estimate of Wilson B factor:" in record:
                    self._b_factor = float(record.split(":")[1].split()[0])

            self._nref_in, self._nref_out = nref, nref
            self._nabsent = 0

            moments = None

            results = self.parse_ccp4_loggraph()

            if "Acentric moments of E using Truncate method" in results:
                moments = transpose_loggraph(
                    results["Acentric moments of E using Truncate method"]
                )
            elif "Acentric moments of I" in results:
                moments = transpose_loggraph(results["Acentric moments of I"])
            elif "Acentric moments of E" in results:
                moments = transpose_loggraph(results["Acentric moments of E"])
            else:
                logger.debug("Acentric moments of E/I not found")

            self._moments = moments

        def get_b_factor(self):
            return self._b_factor

        def get_moments(self):
            return self._moments

        def get_nref_in(self):
            return self._nref_in

        def get_nref_out(self):
            return self._nref_out

        def get_nabsent(self):
            return self._nabsent

        def parse_ccp4_loggraph(self):
            """Look through the standard output of the program for
            CCP4 loggraph text. When this is found store it in a
            local dictionary to allow exploration."""

            # reset the loggraph store
            self._loggraph = {}

            output = self.get_all_output()

            for i in range(len(output)):
                line = output[i]
                if "$TABLE" in line:

                    n_dollar = line.count("$$")

                    current = line.split(":")[1].replace(">", "").strip()
                    self._loggraph[current] = {}
                    self._loggraph[current]["columns"] = []
                    self._loggraph[current]["data"] = []

                    loggraph_info = ""

                    while n_dollar < 4:
                        n_dollar += line.count("$$")
                        loggraph_info += line

                        if n_dollar == 4:
                            break

                        i += 1
                        line = output[i]

                    tokens = loggraph_info.split("$$")
                    self._loggraph[current]["columns"] = tokens[1].split()

                    if len(tokens) < 4:
                        raise RuntimeError('loggraph "%s" broken' % current)

                    data = tokens[3].split("\n")

                    columns = len(self._loggraph[current]["columns"])

                    for record in data:
                        record = record.split()
                        if len(record) == columns:
                            self._loggraph[current]["data"].append(record)

            return self._loggraph

    return CtruncateWrapper()
