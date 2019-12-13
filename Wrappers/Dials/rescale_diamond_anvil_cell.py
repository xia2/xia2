"""
Provide a wrapper for dials.rescale_diamond_anvil_cell.

When performing a high-pressure data collection using a diamond anvil pressure cell,
the incident and diffracted beams are attenuated in passing through the anvils,
adversely affecting the scaling statistics.  dials.rescale_diamond_anvil_cell
provides a correction to the integrated intensities before symmetry determination and
scaling.

This wrapper is intended for use in the _integrate_finish step of the DialsIntegrater.
"""

from __future__ import absolute_import, division, print_function

from xia2.Driver.DriverFactory import DriverFactory

import os


def rescale_dac(driver_type=None):
    """A factory for RescaleDACWrapper classes."""

    driver_instance = DriverFactory.Driver(driver_type)

    class RescaleDACWrapper(driver_instance.__class__):
        """Wrap dials.rescale_diamond_anvil_cell."""

        def __init__(self):
            super(RescaleDACWrapper, self).__init__()

            self.set_executable("dials.rescale_diamond_anvil_cell")

            # Input and output files.  None is a valid value for the output experiments.
            self._experiments_filename = None
            self._reflections_filename = None
            self._output_experiments_filename = None
            self._output_reflections_filename = None

            # Parameters to pass to dials.rescale_diamond_anvil_cell
            self._density = None
            self._thickness = None
            self._normal = None

        @property
        def experiments_filename(self):
            return self._experiments_filename

        @experiments_filename.setter
        def experiments_filename(self, filename):
            self.add_command_line("%s" % filename)
            self._experiments_filename = filename

        @property
        def reflections_filename(self):
            return self._reflections_filename

        @reflections_filename.setter
        def reflections_filename(self, filename):
            self.add_command_line("%s" % filename)
            self._experiments_filename = filename

        @property
        def output_experiments_filename(self):
            return self._output_experiments_filename

        @output_experiments_filename.setter
        def output_experiments_filename(self, filename):
            self.add_command_line("output.experiments=%s" % filename)
            self._output_experiments_filename = filename

        @property
        def output_reflections_filename(self):
            return self._output_reflections_filename

        @output_reflections_filename.setter
        def output_reflections_filename(self, filename):
            self.add_command_line("output.reflections=%s" % filename)
            self._output_reflections_filename = filename

        @property
        def density(self):
            return self._density

        @density.setter
        def density(self, density):
            self.add_command_line("anvil.density=%s" % density)
            self._density = density

        @property
        def thickness(self):
            return self._thickness

        @thickness.setter
        def thickness(self, thickness):
            self.add_command_line("anvil.thickness=" % thickness)
            self._thickness = thickness

        @property
        def normal(self):
            return self._normal

        @normal.setter
        def normal(self, normal):
            self.add_command_line("anvil.normal=%s" % normal)
            self._normal = normal

        def __call__(self):
            """Run dials.rescale_diamond_anvil_cell if the parameters are valid."""
            self.clear_command_line()

            # We should only start if the properties have been set.
            assert self.experiments_filename
            assert self.reflections_filename
            # None is a valid value for the output experiment list filename.
            assert self.output_reflections_filename
            assert self.density
            assert self.thickness
            assert self.normal

            self.start()
            self.close_wait()
            self.check_for_errors()

            assert os.path.exists(self._output_reflections_filename)

    return RescaleDACWrapper()
