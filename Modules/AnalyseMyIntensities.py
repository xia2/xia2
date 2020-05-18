# A tool to use for the analysis and gathering of scaled intensity data
# from a single macromolecular crystal. This will be both a module (for
# use in xia2) and an application in it's own right, AMI.
#
# Example usage:
#
# ami hklin1 PEAK.HKL hklin2 INFL.HKL hklin3 LREM.HKL HKLOUT merged.mtz << eof
# drename file 1 pname demo xname only dname peak
# drename file 2 pname demo xname only dname infl
# drename file 3 pname demo xname only dname lrem
# solvent 0.53
# symm P43212
# reindex h,k,l
# cell 55.67 55.67 108.92 90.0 90.0 90.0
# anomalous on
# eof
#
# should also allow for a HKLREF.


import math
import os

from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory


class AnalyseMyIntensities:
    # FIXME retire this entire class...

    def __init__(self):
        self._working_directory = os.getcwd()
        self._factory = CCP4Factory()
        self._resolution = 0.0

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)

    def get_working_directory(self):
        return self._working_directory

    def compute_average_cell(self, hklin_list):
        if len(hklin_list) == 0:
            raise RuntimeError("no input reflection files to compute cell from")

        cell_a = 0.0
        cell_b = 0.0
        cell_c = 0.0
        cell_alpha = 0.0
        cell_beta = 0.0
        cell_gamma = 0.0
        n_input = 0
        sg = None

        for hklin in hklin_list:
            mtzdump = self._factory.Mtzdump()
            mtzdump.set_hklin(hklin)
            mtzdump.dump()

            resolution = min(mtzdump.get_resolution_range())
            if resolution < self._resolution or self._resolution == 0:
                self._resolution = resolution

            datasets = mtzdump.get_datasets()
            reflections = mtzdump.get_reflections()
            if len(datasets) > 1:
                raise RuntimeError("more than one dataset in %s" % hklin)
            info = mtzdump.get_dataset_info(datasets[0])

            if not sg:
                sg = info["spacegroup"]
            elif sg != info["spacegroup"]:
                raise RuntimeError("inconsistent spacegroup")

            # check that this u/c is in agreement with the others -
            # allow 10% grace (!)

            if n_input == 0:
                cell_a = info["cell"][0] * reflections
                cell_b = info["cell"][1] * reflections
                cell_c = info["cell"][2] * reflections
                cell_alpha = info["cell"][3] * reflections
                cell_beta = info["cell"][4] * reflections
                cell_gamma = info["cell"][5] * reflections
                n_input += reflections
            else:
                if math.fabs(n_input * info["cell"][0] - cell_a) / cell_a > 0.1:
                    raise RuntimeError("inconsistent unit cell")
                if math.fabs(n_input * info["cell"][1] - cell_b) / cell_b > 0.1:
                    raise RuntimeError("inconsistent unit cell")
                if math.fabs(n_input * info["cell"][2] - cell_c) / cell_c > 0.1:
                    raise RuntimeError("inconsistent unit cell")
                if math.fabs(n_input * info["cell"][3] - cell_alpha) / cell_alpha > 0.1:
                    raise RuntimeError("inconsistent unit cell")
                if math.fabs(n_input * info["cell"][4] - cell_beta) / cell_beta > 0.1:
                    raise RuntimeError("inconsistent unit cell")
                if math.fabs(n_input * info["cell"][5] - cell_gamma) / cell_gamma > 0.1:
                    raise RuntimeError("inconsistent unit cell")

                cell_a += info["cell"][0] * reflections
                cell_b += info["cell"][1] * reflections
                cell_c += info["cell"][2] * reflections
                cell_alpha += info["cell"][3] * reflections
                cell_beta += info["cell"][4] * reflections
                cell_gamma += info["cell"][5] * reflections
                n_input += reflections

        cell_a /= n_input
        cell_b /= n_input
        cell_c /= n_input
        cell_alpha /= n_input
        cell_beta /= n_input
        cell_gamma /= n_input

        average_cell = (cell_a, cell_b, cell_c, cell_alpha, cell_beta, cell_gamma)

        return average_cell, sg
