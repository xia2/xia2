#!/usr/bin/env python
# GenerateMask.py
#
#   Copyright (C) 2017 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Generate an image mask for DIALS

from __future__ import absolute_import, division, print_function

from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor


def GenerateMask(DriverType=None):
    """A factory for GenerateMaskWrapper classes."""

    from xia2.Driver.DriverFactory import DriverFactory

    DriverInstance = DriverFactory.Driver(DriverType)

    class GenerateMaskWrapper(DriverInstance.__class__, FrameProcessor):
        def __init__(self):
            super(GenerateMaskWrapper, self).__init__()

            self.set_executable("dials.generate_mask")

            self._input_experiments_filename = None
            self._output_experiments_filename = None
            self._output_mask_filename = None
            self._params = None

        def set_input_experiments(self, experiments_filename):
            self._input_experiments_filename = experiments_filename

        def set_output_experiments(self, experiments_filename):
            self._output_experiments_filename = experiments_filename

        def set_output_mask_filename(self, mask_filename):
            self._output_mask_filename = mask_filename

        def set_params(self, params):
            self._params = params

        def run(self):
            import os
            from xia2.Handlers.Streams import Debug

            Debug.write("Running dials.generate_mask")

            self.clear_command_line()

            assert self._params is not None
            from dials.util.masking import phil_scope

            working_phil = phil_scope.format(self._params)
            diff_phil = phil_scope.fetch_diff(source=working_phil)
            phil_filename = os.path.join(
                self.get_working_directory(), "%s_mask.phil" % self.get_xpid()
            )
            with open(phil_filename, "wb") as f:
                f.write(diff_phil.as_str())
                f.write(
                    os.linesep
                )  # temporarily required for https://github.com/dials/dials/issues/522

            self.add_command_line(
                'input.experiments="%s"' % self._input_experiments_filename
            )
            if self._output_mask_filename is None:
                self._output_mask_filename = os.path.join(
                    self.get_working_directory(), "%s_mask.pickle" % self.get_xpid()
                )
            if self._output_experiments_filename is None:
                self._output_experiments_filename = os.path.join(
                    self.get_working_directory(),
                    "%s_experiments.mpack" % self.get_xpid(),
                )
            self.add_command_line('output.mask="%s"' % self._output_mask_filename)
            self.add_command_line(
                'output.experiments="%s"' % self._output_experiments_filename
            )
            self.add_command_line(phil_filename)
            self.start()
            self.close_wait()
            self.check_for_errors()
            assert os.path.exists(
                self._output_mask_filename
            ), self._output_mask_filename
            assert os.path.exists(
                self._output_experiments_filename
            ), self._output_experiments_filename
            return self._output_experiments_filename, self._output_mask_filename

    return GenerateMaskWrapper()
