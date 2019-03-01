#!/usr/bin/env python
# RefineBravaisSettings.py
#
#   Copyright (C) 2014 Diamond Light Source, Richard Gildea, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Refine result of P1 DIALS indexing in all possible settings; publish results.

from __future__ import absolute_import, division, print_function

from xia2.Handlers.Phil import PhilIndex


def RefineBravaisSettings(DriverType=None):
    """A factory for RefineBravaisSettingsWrapper classes."""

    from xia2.Driver.DriverFactory import DriverFactory

    DriverInstance = DriverFactory.Driver(DriverType)

    class RefineBravaisSettingsWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("dials.refine_bravais_settings")

            self._experiments_filename = None
            self._indexed_filename = None
            self._detector_fix = None
            self._beam_fix = None
            self._close_to_spindle_cutoff = None

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def set_indexed_filename(self, indexed_filename):
            self._indexed_filename = indexed_filename

        def set_detector_fix(self, detector_fix):
            self._detector_fix = detector_fix

        def set_beam_fix(self, beam_fix):
            self._beam_fix = beam_fix

        def set_close_to_spindle_cutoff(self, close_to_spindle_cutoff):
            self._close_to_spindle_cutoff = close_to_spindle_cutoff

        def get_bravais_summary(self):
            import copy, os

            bravais_summary = {}
            for k in self._bravais_summary:
                bravais_summary[int(k)] = copy.deepcopy(self._bravais_summary[k])
                bravais_summary[int(k)]["experiments_file"] = os.path.join(
                    self.get_working_directory(), "bravais_setting_%d.json" % int(k)
                )
            return bravais_summary

        def run(self):
            from xia2.Handlers.Streams import Debug

            Debug.write("Running dials.refine_bravais_settings")

            self.clear_command_line()
            self.add_command_line(self._experiments_filename)
            self.add_command_line(self._indexed_filename)

            nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
            self.set_cpu_threads(nproc)
            self.add_command_line("nproc=%i" % nproc)
            # self.add_command_line('reflections_per_degree=10')
            if self._detector_fix:
                self.add_command_line("detector.fix=%s" % self._detector_fix)
            if self._beam_fix:
                self.add_command_line("beam.fix=%s" % self._beam_fix)
            # self.add_command_line('engine=GaussNewton')
            if self._close_to_spindle_cutoff is not None:
                self.add_command_line(
                    "close_to_spindle_cutoff=%f" % self._close_to_spindle_cutoff
                )

            self.start()
            self.close_wait()
            self.check_for_errors()

            from json import loads
            import os

            self._bravais_summary = loads(
                open(
                    os.path.join(self.get_working_directory(), "bravais_summary.json"),
                    "r",
                ).read()
            )

    return RefineBravaisSettingsWrapper()
