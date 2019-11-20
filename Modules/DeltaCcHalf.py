from __future__ import absolute_import, division, print_function

import math

import iotbx.phil
from cctbx.array_family import flex
from iotbx.merging_statistics import dataset_statistics
from libtbx.utils import frange

from dials.util import tabulate

phil_scope = iotbx.phil.parse(
    """\
cc_one_half_method = half_dataset *sigma_tau
  .type = choice
unit_cell = None
  .type = unit_cell
n_bins = 20
  .type = int(value_min=1)
d_min = None
  .type = float(value_min=0)
""",
    process_includes=True,
)


class DeltaCcHalf(object):
    def __init__(
        self,
        intensities,
        batches,
        n_bins=20,
        d_min=None,
        cc_one_half_method="sigma_tau",
    ):
        self.intensities = intensities
        self.batches = batches

        unmerged_intensities = None
        for ma in intensities:
            if unmerged_intensities is None:
                unmerged_intensities = ma
            else:
                unmerged_intensities = unmerged_intensities.concatenate(
                    ma
                ).set_observation_type(unmerged_intensities.observation_type())

        self.merging_statistics = dataset_statistics(
            unmerged_intensities,
            n_bins=n_bins,
            cc_one_half_significance_level=0.01,
            binning_method="counting_sorted",
            anomalous=True,
            use_internal_variance=False,
            eliminate_sys_absent=False,
            cc_one_half_method=cc_one_half_method,
        )
        if cc_one_half_method == "sigma_tau":
            cc_overall = self.merging_statistics.cc_one_half_sigma_tau_overall
        else:
            cc_overall = self.merging_statistics.cc_one_half_overall

        self.delta_cc = flex.double()
        for test_k in range(len(self.intensities)):
            indices_i = flex.miller_index()
            data_i = flex.double()
            sigmas_i = flex.double()
            for k, unmerged in enumerate(self.intensities):
                if k == test_k:
                    continue
                indices_i.extend(unmerged.indices())
                data_i.extend(unmerged.data())
                sigmas_i.extend(unmerged.sigmas())

            unmerged_i = unmerged_intensities.customized_copy(
                indices=indices_i, data=data_i, sigmas=sigmas_i
            ).set_info(unmerged_intensities.info())

            unmerged_i.setup_binner_counting_sorted(n_bins=n_bins)
            if cc_one_half_method == "sigma_tau":
                cc_bins = unmerged_i.cc_one_half_sigma_tau(
                    use_binning=True, return_n_refl=True
                )
            else:
                cc_bins = unmerged_i.cc_one_half(use_binning=True, return_n_refl=True)
            cc_i = flex.mean_weighted(
                flex.double(b[0] for b in cc_bins.data[1:-1]),
                flex.double(b[1] for b in cc_bins.data[1:-1]),
            )

            delta_cc_i = cc_i - cc_overall
            self.delta_cc.append(delta_cc_i)

    def _normalised_delta_cc_i(self):
        mav = flex.mean_and_variance(self.delta_cc)
        return (self.delta_cc - mav.mean()) / mav.unweighted_sample_standard_deviation()

    def get_table(self):
        rows = [["dataset", "batches", "delta_cc_i", "sigma"]]
        normalised_score = self._normalised_delta_cc_i()
        perm = flex.sort_permutation(self.delta_cc)
        for i in perm:
            bmin = flex.min(self.batches[i].data())
            bmax = flex.max(self.batches[i].data())
            rows.append(
                [
                    str(i),
                    "%i to %i" % (bmin, bmax),
                    "% .3f" % self.delta_cc[i],
                    "% .2f" % normalised_score[i],
                ]
            )
        return tabulate(rows, headers="firstrow")

    def plot_histogram(self, filename):
        from matplotlib import pyplot as plt

        normalised_score = self._normalised_delta_cc_i()
        plt.figure()
        bins = frange(
            math.floor(flex.min(normalised_score)),
            math.ceil(flex.max(normalised_score)) + 1,
            step=0.1,
        )
        n, bins, patches = plt.hist(
            normalised_score.as_numpy_array(), bins=bins, fill=False
        )
        plt.xlabel(r"$\sigma$")
        plt.ylabel("Frequency")
        plt.savefig(filename)
