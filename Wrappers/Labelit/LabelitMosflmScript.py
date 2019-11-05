from __future__ import absolute_import, division, print_function

import os

from xia2.Driver.DriverFactory import DriverFactory


def LabelitMosflmScript(DriverType=None):
    """Factory for LabelitMosflmScript wrapper classes, with the specified
    Driver type."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class LabelitMosflmScriptWrapper(DriverInstance.__class__):
        """A wrapper for the program labelit.mosflm_script - which will
        calculate the matrix for mosflm integration."""

        def __init__(self):
            DriverInstance.__class__.__init__(self)
            self.set_executable("labelit.mosflm_script")

            self._solution = None
            self._mosflm_beam = None

        def set_solution(self, solution):
            self._solution = solution

        def calculate(self):
            """Compute matrix for solution #."""

            if self._solution is None:
                raise RuntimeError("solution not selected")

            self.add_command_line("%d" % self._solution)

            self.start()
            self.close_wait()

            output = open(
                os.path.join(
                    self.get_working_directory(), "integration%02d.csh" % self._solution
                )
            ).readlines()
            matrix = output[2:11]

            # also check for the beam centre in mosflm land! - ignoring
            # SWUNG OUT though I should probably check the two-theta
            # value too...

            for o in output:
                if "BEAM" in o[:4]:
                    self._mosflm_beam = list(map(float, o.split()[-2:]))

            return matrix

        def get_mosflm_beam(self):
            return self._mosflm_beam

    return LabelitMosflmScriptWrapper()
