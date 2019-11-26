# coding: utf-8

from __future__ import absolute_import, division, print_function

import logging
import math

import iotbx.phil
from cctbx.array_family import flex
from iotbx.merging_statistics import dataset_statistics
from libtbx.utils import frange

from dials.util import tabulate

logger = logging.getLogger(__name__)

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
        self._cc_one_half_method = cc_one_half_method
        self._n_bins = n_bins

        unmerged_intensities = None
        for ma in intensities:
            if unmerged_intensities is None:
                unmerged_intensities = ma
            else:
                unmerged_intensities = unmerged_intensities.concatenate(
                    ma
                ).set_observation_type(unmerged_intensities.observation_type())

        self.binner = unmerged_intensities.eliminate_sys_absent().setup_binner_counting_sorted(
            n_bins=self._n_bins
        )
        self.merging_statistics = dataset_statistics(
            unmerged_intensities,
            n_bins=n_bins,
            cc_one_half_significance_level=0.01,
            binning_method="counting_sorted",
            anomalous=True,
            use_internal_variance=False,
            eliminate_sys_absent=False,
            cc_one_half_method=self._cc_one_half_method,
            assert_is_not_unique_set_under_symmetry=False,
        )
        if self._cc_one_half_method == "sigma_tau":
            self.cc_overall = self.merging_statistics.cc_one_half_sigma_tau_overall
        else:
            self.cc_overall = self.merging_statistics.cc_one_half_overall

        self.delta_cc = self._compute_delta_ccs()

    def _compute_delta_ccs(self):
        delta_cc = flex.double()
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

            unmerged_i = self.intensities[0].customized_copy(
                indices=indices_i, data=data_i, sigmas=sigmas_i
            )

            delta_cc.append(self._compute_delta_cc_for_dataset(unmerged_i))
        return delta_cc

    def _compute_delta_cc_for_dataset(self, intensities):
        intensities.use_binning(self.binner)
        if self._cc_one_half_method == "sigma_tau":
            cc_bins = intensities.cc_one_half_sigma_tau(
                use_binning=True, return_n_refl=True
            )
        else:
            cc_bins = intensities.cc_one_half(use_binning=True, return_n_refl=True)
        cc_i = flex.mean_weighted(
            flex.double(b[0] for b in cc_bins.data[1:-1]),
            flex.double(b[1] for b in cc_bins.data[1:-1]),
        )
        return self.cc_overall - cc_i

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

    def histogram(self):
        normalised_score = self._normalised_delta_cc_i()
        return {
            "delta_cc_half_histogram": {
                "data": [
                    {
                        "x": list(normalised_score),
                        "xbins": {
                            "start": math.floor(flex.min(normalised_score)),
                            "end": math.ceil(flex.max(normalised_score)) + 1,
                            "size": 0.1,
                        },
                        "type": "histogram",
                        "name": u"Delta CC<sub>½</sub>",
                    }
                ],
                "layout": {
                    "title": u"Histogram of Delta CC<sub>½</sub>",
                    "xaxis": {"title": u"σ"},
                    "yaxis": {"title": "Frequency"},
                },
            }
        }

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

    def normalised_scores(self):
        return {
            "delta_cc_half_normalised_score": {
                "data": [
                    {
                        "y": list(self._normalised_delta_cc_i()),
                        "type": "scatter",
                        "mode": "lines",
                        "name": "delta_cc_half_normalised_score",
                    }
                ],
                "layout": {
                    "title": u"Normalised Delta CC<sub>½</sub>",
                    "xaxis": {"title": "Group"},
                    "yaxis": {"title": u"σ"},
                },
            }
        }

    def plot_normalised_scores(self, filename):
        from matplotlib import pyplot as plt

        normalised_score = self._normalised_delta_cc_i()
        plt.figure()
        plt.plot(normalised_score)
        plt.xlabel("Group")
        plt.ylabel(r"$\sigma$")
        plt.savefig(filename)


class DeltaCcHalfImageGroups(DeltaCcHalf):
    def __init__(
        self,
        intensities,
        batches,
        n_bins=20,
        d_min=None,
        cc_one_half_method="sigma_tau",
        group_size=10,
    ):
        self._group_size = group_size
        super(DeltaCcHalfImageGroups, self).__init__(
            intensities,
            batches,
            n_bins,
            d_min=d_min,
            cc_one_half_method=cc_one_half_method,
        )

    def _compute_delta_ccs(self):
        self._group_to_batches = []
        self._group_to_dataset_id = flex.int()
        delta_cc = flex.double()
        for test_k in range(len(self.intensities)):
            batches = self.batches[test_k].data()
            b_min = flex.min(batches)
            b_max = flex.max(batches)
            n_batches = b_max - b_min + 1
            n_groups = int(math.ceil(n_batches / self._group_size))
            for k_group in range(n_groups):
                group_start = b_min + k_group * self._group_size
                group_end = min(b_max, group_start + self._group_size)
                group_sel = (batches >= group_start) & (batches < group_end)
                self._group_to_batches.append((group_start, group_end))
                self._group_to_dataset_id.append(test_k)
                indices_i = flex.miller_index()
                data_i = flex.double()
                sigmas_i = flex.double()
                for k, unmerged in enumerate(self.intensities):
                    if k == test_k:
                        unmerged = unmerged.select(~group_sel)
                    indices_i.extend(unmerged.indices())
                    data_i.extend(unmerged.data())
                    sigmas_i.extend(unmerged.sigmas())

                unmerged_i = self.intensities[0].customized_copy(
                    indices=indices_i, data=data_i, sigmas=sigmas_i
                )

                delta_cc.append(self._compute_delta_cc_for_dataset(unmerged_i))
                logger.info(
                    "Delta CC1/2 excluding batches %i-%i: %.3f",
                    group_start,
                    group_end,
                    delta_cc[-1],
                )
        return delta_cc

    def get_table(self):
        rows = [["dataset", "batches", "delta_cc_i", "sigma"]]
        normalised_score = self._normalised_delta_cc_i()
        perm = flex.sort_permutation(self.delta_cc)
        for i in perm:
            bmin, bmax = self._group_to_batches[i]
            rows.append(
                [
                    str(self._group_to_dataset_id[i]),
                    "%i to %i" % (bmin, bmax),
                    "% .3f" % self.delta_cc[i],
                    "% .2f" % normalised_score[i],
                ]
            )
        return tabulate(rows, headers="firstrow")
