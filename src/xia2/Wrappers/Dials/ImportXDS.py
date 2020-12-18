import os

from xia2.Driver.DriverFactory import DriverFactory


def ImportXDS(DriverType=None):
    """A factory for ImportXDSWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class ImportXDSWrapper(DriverInstance.__class__):
        def __init__(self):
            super().__init__()

            self.set_executable("dials.import_xds")

            self._spot_xds = None
            self._integrate_hkl = None
            self._xparm_xds = None
            self._experiments_json = None
            self._reflection_filename = None

        def set_spot_xds(self, spot_xds):
            self._spot_xds = spot_xds

        def set_integrate_hkl(self, integrate_hkl):
            self._integrate_hkl = integrate_hkl

        def set_xparm_xds(self, xparm_xds):
            self._xparm_xds = xparm_xds

        def set_experiments_json(self, experiments_json):
            self._experiments_json = experiments_json

        def get_reflection_filename(self):
            return self._reflection_filename

        def get_experiments_json(self):
            return self._experiments_json

        def run(self):

            self.clear_command_line()

            if self._spot_xds is not None:
                self._reflection_filename = os.path.join(
                    self.get_working_directory(), "%s_spot_xds.refl" % self.get_xpid()
                )
                self.add_command_line(self._spot_xds)
                self.add_command_line("output.filename=%s" % self._reflection_filename)
                self.add_command_line("method=reflections")

            elif self._integrate_hkl is not None:
                self._reflection_filename = os.path.join(
                    self.get_working_directory(),
                    "%s_integrate_hkl.refl" % self.get_xpid(),
                )
                assert self._experiments_json is not None
                self.add_command_line(self._integrate_hkl)
                self.add_command_line(self._experiments_json)
                self.add_command_line("output.filename=%s" % self._reflection_filename)
                self.add_command_line("method=reflections")

            elif self._xparm_xds is not None:
                if self._experiments_json is None:
                    self._experiments_json = os.path.join(
                        self.get_working_directory(),
                        "%s_xparm_xds.expt" % self.get_xpid(),
                    )
                directory, xparm = os.path.split(self._xparm_xds)
                self.add_command_line(directory)
                self.add_command_line("xds_file=%s" % xparm)
                self.add_command_line("output.filename=%s" % self._experiments_json)

            self.start()
            self.close_wait()
            self.check_for_errors()

            if self._reflection_filename is not None:
                assert os.path.exists(
                    self._reflection_filename
                ), self._reflection_filename
            else:
                assert os.path.exists(self._experiments_json), self._experiments_json

    return ImportXDSWrapper()
