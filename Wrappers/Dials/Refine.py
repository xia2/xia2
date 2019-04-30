#!/usr/bin/env python
# Refine.py
#
#   Copyright (C) 2013 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Assign indices to reflection centroids given a crystal model

from __future__ import absolute_import, division, print_function

import os


def Refine(DriverType=None):
    """A factory for RefineWrapper classes."""

    from xia2.Driver.DriverFactory import DriverFactory

    DriverInstance = DriverFactory.Driver(DriverType)

    class RefineWrapper(DriverInstance.__class__):
        def __init__(self):
            DriverInstance.__class__.__init__(self)

            self._images = []
            self._spot_range = []

            self.set_executable("dials.refine")

            self._experiments_filename = None
            self._indexed_filename = None
            self._refined_experiments_filename = None
            self._refined_filename = None
            self._scan_varying = False
            self._detector_fix = None
            self._beam_fix = None
            self._reflections_per_degree = None
            self._interval_width_degrees = None
            self._phil_file = None
            self._outlier_algorithm = None
            self._close_to_spindle_cutoff = None

        def set_experiments_filename(self, experiments_filename):
            self._experiments_filename = experiments_filename

        def get_experiments_filename(self):
            return self._experiments_filename

        def set_indexed_filename(self, indexed_filename):
            self._indexed_filename = indexed_filename

        def get_refined_filename(self):
            return self._refined_filename

        def get_refined_experiments_filename(self):
            return self._refined_experiments_filename

        def set_scan_varying(self, scan_varying):
            self._scan_varying = scan_varying

        def get_scan_varying(self):
            return self._scan_varying

        def set_detector_fix(self, detector_fix):
            self._detector_fix = detector_fix

        def set_beam_fix(self, beam_fix):
            self._beam_fix = beam_fix

        def set_reflections_per_degree(self, reflections_per_degree):
            self._reflections_per_degree = int(reflections_per_degree)

        def set_interval_width_degrees(self, interval_width_degrees):
            self._interval_width_degrees = interval_width_degrees

        def set_phil_file(self, phil_file):
            self._phil_file = phil_file

        def set_outlier_algorithm(self, outlier_algorithm):
            self._outlier_algorithm = outlier_algorithm

        def set_close_to_spindle_cutoff(self, close_to_spindle_cutoff):
            self._close_to_spindle_cutoff = close_to_spindle_cutoff

        def run(self):
            from xia2.Handlers.Streams import Debug

            Debug.write("Running dials.refine")

            self.clear_command_line()
            self.add_command_line(self._experiments_filename)
            self.add_command_line(self._indexed_filename)
            self.add_command_line("scan_varying=%s" % self._scan_varying)
            if self._close_to_spindle_cutoff is not None:
                self.add_command_line(
                    "close_to_spindle_cutoff=%f" % self._close_to_spindle_cutoff
                )
            if self._outlier_algorithm:
                self.add_command_line("outlier.algorithm=%s" % self._outlier_algorithm)
            self._refined_experiments_filename = os.path.join(
                self.get_working_directory(),
                "%s_refined_experiments.json" % self.get_xpid(),
            )
            self.add_command_line(
                "output.experiments=%s" % self._refined_experiments_filename
            )
            self._refined_filename = os.path.join(
                self.get_working_directory(), "%s_refined.pickle" % self.get_xpid()
            )
            self.add_command_line("output.reflections=%s" % self._refined_filename)
            if self._reflections_per_degree is not None:
                self.add_command_line(
                    "reflections_per_degree=%i" % self._reflections_per_degree
                )
            if self._interval_width_degrees is not None:
                self.add_command_line(
                    "unit_cell.smoother.interval_width_degrees=%i"
                    % self._interval_width_degrees
                )
                self.add_command_line(
                    "orientation.smoother.interval_width_degrees=%i"
                    % self._interval_width_degrees
                )
            if self._detector_fix:
                self.add_command_line("detector.fix=%s" % self._detector_fix)
            if self._beam_fix:
                self.add_command_line("beam.fix=%s" % self._beam_fix)
            if self._phil_file is not None:
                self.add_command_line("%s" % self._phil_file)

            self.start()
            self.close_wait()

            if not os.path.isfile(self._refined_filename) or not os.path.isfile(
                self._refined_experiments_filename
            ):
                raise RuntimeError(
                    "DIALS did not refine the data, see log file for more details:  %s"
                    % self.get_log_file()
                )
            for record in self.get_all_output():
                if "Sorry: Too few reflections to" in record:
                    raise RuntimeError(record.strip())

            self.check_for_errors()

    return RefineWrapper()
