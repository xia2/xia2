import logging

from xia2.Driver.DriverFactory import DriverFactory

logger = logging.getLogger("xia2.Wrappers.Dials.ExportMMCIF")


def ExportMMCIF(DriverType=None):
    """A factory for ExportMMCIFWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class ExportMMCIFWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.export")

            self._experiments_filename = None
            self._reflections_filename = None
            self._filename = "scaled.mmcif"
            self._partiality_threshold = 0.4
            self._combine_partials = True
            self._intensity_choice = "scale"
            self._compress = None
            self._pdb_version = "v5_next"

        def set_intensity_choice(self, choice):
            self._intensity_choice = choice

        def set_partiality_threshold(self, partiality_threshold):
            self._partiality_threshold = partiality_threshold

        def set_compression(self, compression=None):
            "Set a compression type: gz bz2 xz or None(uncompressed)"
            self._compress = compression

        def set_pdb_version(self, version):
            self._pdb_version = version

        def set_combine_partials(self, combine_partials):
            self._combine_partials = combine_partials

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def get_experiments_filename(self):
            return self._experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def get_reflections_filename(self):
            return self._reflections_filename

        def set_filename(self, filename):
            self._filename = filename

        def get_filename(self):
            return self._filename

        def run(self):
            logger.debug("Running dials.export")

            self.clear_command_line()
            self.add_command_line("experiments=%s" % self._experiments_filename)
            self.add_command_line("reflections=%s" % self._reflections_filename)
            self.add_command_line("format=mmcif")
            self.add_command_line("mmcif.hklout=%s" % self._filename)
            if self._combine_partials:
                self.add_command_line("combine_partials=true")
            if self._compress:
                self.add_command_line("mmcif.compress=%s" % self._compress)
            self.add_command_line(
                "partiality_threshold=%s" % self._partiality_threshold
            )
            self.add_command_line("pdb_version=%s" % self._pdb_version)
            self.add_command_line("intensity=%s" % self._intensity_choice)
            self.start()
            self.close_wait()
            self.check_for_errors()

    return ExportMMCIFWrapper()
