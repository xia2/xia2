#!/usr/bin/env python

from __future__ import absolute_import, division, print_function


def ExportBest(DriverType=None):
    """A factory for ExportMtzWrapper classes."""

    from xia2.Driver.DriverFactory import DriverFactory

    DriverInstance = DriverFactory.Driver(DriverType)

    class ExportBestWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.export_best")

            self._experiments_filename = None
            self._reflections_filename = None
            self._prefix = "best"

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def get_experiments_filename(self):
            return self._experiments_filename

        def set_reflections_filename(self, reflections_filename):
            self._reflections_filename = reflections_filename

        def get_reflections_filename(self):
            return self._reflections_filename

        def set_prefix(self, prefix):
            self._prefix = prefix

        def get_prefix(self):
            return self._prefix

        def run(self):
            from xia2.Handlers.Streams import Debug

            Debug.write("Running dials.export_best")

            self.clear_command_line()
            self.add_command_line("experiments=%s" % self._experiments_filename)
            self.add_command_line("reflections=%s" % self._reflections_filename)
            self.add_command_line("output.prefix=%s" % self._prefix)
            self.start()
            self.close_wait()
            self.check_for_errors()

    return ExportBestWrapper()
