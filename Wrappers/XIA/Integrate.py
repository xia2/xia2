import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.XIA.Integrate")


def Integrate(DriverType=None):
    """A factory for IntegrateWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class IntegrateWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("xia2.integrate")
            self._argv = []
            self._nproc = None
            self._njob = None
            self._mp_mode = None
            self._phil_file = None

        def add_command_line_args(self, args):
            self._argv.extend(args)

        def set_nproc(self, nproc):
            self._nproc = nproc

        def set_njob(self, njob):
            self._njob = njob

        def set_mp_mode(self, mp_mode):
            self._mp_mode = mp_mode

        def set_phil_file(self, phil_file):
            self._phil_file = phil_file

        def run(self):
            logger.debug("Running xia2.integrate")

            self.clear_command_line()

            if self._phil_file is not None:
                self.add_command_line(self._phil_file)

            for arg in self._argv:
                self.add_command_line(arg)
            if self._nproc is not None:
                self.set_cpu_threads(self._nproc)
                self.add_command_line("nproc=%i" % self._nproc)

            if self._njob is not None:
                self.add_command_line("njob=%i" % self._njob)

            if self._mp_mode is not None:
                self.add_command_line("multiprocessing.mode=%s" % self._mp_mode)

            self.add_command_line("failover=False")

            self.start()
            self.close_wait()
            self.check_for_errors()
            for line in self.get_all_output():
                if "Status: error" in line:
                    raise RuntimeError(line.split("error")[-1].strip())

    return IntegrateWrapper()
