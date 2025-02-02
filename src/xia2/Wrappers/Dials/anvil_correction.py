"""
Provide a wrapper for dials.anvil_correction.

When performing a high-pressure data collection using a diamond anvil pressure cell,
the incident and diffracted beams are attenuated in passing through the anvils,
adversely affecting the scaling statistics. dials.anvil_correction provides a
correction to the integrated intensities before symmetry determination and scaling.

This wrapper is intended for use in the _integrate_finish step of the DialsIntegrater.
"""

from __future__ import annotations

import os
from typing import SupportsFloat

from xia2.Driver.DriverFactory import DriverFactory


def anvil_correction(driver_type=None):
    """A factory for AnvilCorrectionWrapper classes."""

    driver_instance = DriverFactory.Driver(driver_type)

    class AnvilCorrectionWrapper(driver_instance.__class__):
        """Wrap dials.anvil_correction."""

        def __init__(self):
            super().__init__()

            self.set_executable("dials.anvil_correction")

            # Input and output files.
            # None is a valid value only for the output experiment list filename.
            self.experiments_filenames: list[str] = []
            self.reflections_filenames: list[str] = []
            self.output_experiments_filename: str | None = None
            self.output_reflections_filename: str | None = None

            # Parameters to pass to dials.anvil_correction
            self.density: SupportsFloat | None = None
            self.thickness: SupportsFloat | None = None
            self.normal: tuple[3 * (SupportsFloat,)] | None = None

        def run(self):
            """Run dials.anvil_correction if the parameters are valid."""
            # We should only start if the properties have been set.
            assert self.experiments_filenames
            assert self.reflections_filenames
            # None is a valid value for the output experiment list filename.
            assert self.output_reflections_filename
            assert self.density
            assert self.thickness
            assert self.normal

            self.clear_command_line()

            self.add_command_line(self.experiments_filenames)
            self.add_command_line(self.reflections_filenames)
            if self.output_experiments_filename:
                self.add_command_line(
                    "output.experiments=%s" % self.output_experiments_filename
                )
            self.add_command_line(
                "output.reflections=%s" % self.output_reflections_filename
            )
            self.add_command_line("anvil.density=%s" % self.density)
            self.add_command_line("anvil.thickness=%s" % self.thickness)
            self.add_command_line("anvil.normal={},{},{}".format(*tuple(self.normal)))

            self.start()
            self.close_wait()
            self.check_for_errors()

            assert os.path.exists(self.output_reflections_filename)

    return AnvilCorrectionWrapper()
