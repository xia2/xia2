import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.StereographicProjection")


def StereographicProjection(DriverType=None):
    """A factory for StereographicProjectionWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class StereographicProjectionWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self.set_executable("dials.stereographic_projection")

            self._experiments_filenames = []
            self._hkl = None
            self._labels = None
            self._plot_filename = None
            self._json_filename = None

        def add_experiments(self, experiments_filename):
            self._experiments_filenames.append(experiments_filename)

        def set_hkl(self, hkl):
            assert len(hkl) == 3
            self._hkl = hkl

        def set_labels(self, labels):
            self._labels = labels

        def get_json_filename(self):
            return self._json_filename

        def run(self):
            logger.debug("Running dials.stereographic_projection")

            assert len(self._experiments_filenames) > 0
            assert self._hkl is not None

            self.clear_command_line()
            for expt in self._experiments_filenames:
                self.add_command_line(expt)
            self.add_command_line("frame=laboratory")
            self.add_command_line("hkl=%i,%i,%i" % self._hkl)
            if self._labels:
                self.add_command_line(
                    "plot.labels=%s" % " ".join([str(l) for l in self._labels])
                )
            if self.get_xpid():
                prefix = "%i_" % self.get_xpid()
            else:
                prefix = ""
            self._plot_filename = "%sstereographic_projection_%i%i%i.png" % (
                prefix,
                self._hkl[0],
                self._hkl[1],
                self._hkl[2],
            )
            self._json_filename = "%sstereographic_projection_%i%i%i.json" % (
                prefix,
                self._hkl[0],
                self._hkl[1],
                self._hkl[2],
            )
            self.add_command_line("plot.filename=%s" % self._plot_filename)
            self.add_command_line("json.filename=%s" % self._json_filename)

            self.start()
            self.close_wait()
            self.check_for_errors()

    return StereographicProjectionWrapper()
