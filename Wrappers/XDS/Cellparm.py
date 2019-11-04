from __future__ import absolute_import, division, print_function

import math
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex


def Cellparm(DriverType=None):
    DriverInstance = DriverFactory.Driver(DriverType)

    class CellparmWrapper(DriverInstance.__class__):
        """A wrapper for wrapping CELLPARM."""

        def __init__(self):

            # set up the object ancestors...

            DriverInstance.__class__.__init__(self)

            self.set_executable("cellparm")

            # input parameters
            self._cells = []
            self._n_refs = []

        def add_cell(self, cell, n_ref):
            """Add a unit cell which belongs to n_ref reflections."""

            self._cells.append(cell)
            self._n_refs.append(n_ref)

        def get_cell(self):
            """Compute an average cell."""

            if not self._cells:
                raise RuntimeError("no input unit cell parameters")

            # check that the input cells are reasonably uniform -
            # be really relaxed and allow 5% variation!

            average_cell = [self._cells[0][j] for j in range(6)]
            number_cells = 1

            for j in range(1, len(self._cells)):
                cell = self._cells[j]
                for k in range(6):
                    # FIXME should use xds_cell_deviation
                    average = average_cell[k] / number_cells
                    check = PhilIndex.params.xia2.settings.xds_check_cell_deviation
                    if math.fabs((cell[k] - average) / average) > 0.05 and check:
                        raise RuntimeError("incompatible unit cells")
                    average = average_cell[k] / number_cells
                    if math.fabs((cell[k] - average) / average) > 0.2:
                        raise RuntimeError("very incompatible unit cells")

                # it was ok to remember for later on..
                for k in range(6):
                    average_cell[k] += cell[k]
                number_cells += 1

            with open(
                os.path.join(self.get_working_directory(), "CELLPARM.INP"), "w"
            ) as fh:

                for j, cell in enumerate(self._cells):
                    n_ref = self._n_refs[j]
                    fh.write("UNIT_CELL_CONSTANTS=")
                    fh.write(
                        "%.3f %.3f %.3f %.3f %.3f %.3f WEIGHT=%d\n"
                        % (cell[0], cell[1], cell[2], cell[3], cell[4], cell[5], n_ref)
                    )

            self.start()

            self.close_wait()

            # FIXME need to look for errors in here

            with open(
                os.path.join(self.get_working_directory(), "CELLPARM.LP"), "r"
            ) as fh:
                data = fh.readlines()

            return map(float, data[-1].split()[:6])

    return CellparmWrapper()
