import logging
import math

import iotbx.phil
from cctbx.array_family import flex
from libtbx.utils import frange

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


class DeltaCcHalf:
    def __init__(
        self,
        intensities,
        batches,
        n_bins=20,
        d_min=None,
        cc_one_half_method="sigma_tau",
        group_size=None,
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
                    ma, assert_is_similar_symmetry=False
                ).set_observation_type(unmerged_intensities.observation_type())

        self.binner = (
            unmerged_intensities.eliminate_sys_absent().setup_binner_counting_sorted(
                n_bins=self._n_bins
            )
        )
        self.cc_half_overall = self._compute_mean_weighted_cc_half(unmerged_intensities)

        self._group_size = group_size
        self._setup_processing_groups()
        self.cc_half = self._compute_ccs()
        self.delta_cc_half = self.cc_half_overall - self.cc_half
        self.normalised_delta_cc = self._compute_normalised_delta_ccs()

    def _setup_processing_groups(self):
        self._group_to_batches = []
        self._group_to_dataset_id = flex.int()
        for test_k in range(len(self.intensities)):
            batches = self.batches[test_k].data()
            b_min = flex.min(batches)
            b_max = flex.max(batches)
            n_batches = b_max - b_min + 1
            if self._group_size is not None:
                n_groups = int(math.ceil(n_batches / self._group_size))
                for k_group in range(n_groups):
                    group_start = b_min + k_group * self._group_size
                    group_end = min(b_max, group_start + self._group_size - 1)
                    self._group_to_batches.append((group_start, group_end))
                    self._group_to_dataset_id.append(test_k)
            else:
                self._group_to_batches.append((b_min, b_max))
                self._group_to_dataset_id.append(test_k)

    def _compute_ccs(self):
        ccs = flex.double()
        for (group_start, group_end), test_k in zip(
            self._group_to_batches, self._group_to_dataset_id
        ):
            batches = self.batches[test_k].data()
            group_sel = (batches >= group_start) & (batches <= group_end)
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

            ccs.append(self._compute_mean_weighted_cc_half(unmerged_i))
            logger.debug(
                "CC½ excluding batches %i-%i: %.3f",
                group_start,
                group_end,
                ccs[-1],
            )
        return ccs

    def _compute_mean_weighted_cc_half(self, intensities):
        intensities.use_binning(self.binner)
        if self._cc_one_half_method == "sigma_tau":
            cc_bins = intensities.cc_one_half_sigma_tau(
                use_binning=True, return_n_refl=True
            )
        else:
            cc_bins = intensities.cc_one_half(use_binning=True, return_n_refl=True)
        bin_data = [b for b in cc_bins.data if b is not None]
        return flex.mean_weighted(
            flex.double(b[0] for b in bin_data),
            flex.double(b[1] for b in bin_data),
        )

    def _compute_normalised_delta_ccs(self):
        mav = flex.mean_and_variance(self.delta_cc_half)
        return (
            self.delta_cc_half - mav.mean()
        ) / mav.unweighted_sample_standard_deviation()

    def get_table(self, html=False):
        if html:
            cc_half_header = "CC<sub>½</sub>"
        else:
            cc_half_header = "CC½"
        rows = [["Dataset", "Batches", cc_half_header, f"Δ{cc_half_header}", "σ"]]
        normalised_score = self.normalised_delta_cc
        perm = flex.sort_permutation(self.delta_cc_half)
        for i in perm:
            bmin, bmax = self._group_to_batches[i]
            rows.append(
                [
                    str(self._group_to_dataset_id[i]),
                    "%i to %i" % (bmin, bmax),
                    "% .3f" % self.cc_half[i],
                    "% .3f" % self.delta_cc_half[i],
                    "% .2f" % normalised_score[i],
                ]
            )
        return rows

    def histogram(self):
        normalised_score = self.normalised_delta_cc
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
                        "name": "ΔCC<sub>½</sub>",
                    }
                ],
                "layout": {
                    "title": "Histogram of ΔCC<sub>½</sub>",
                    "xaxis": {"title": "σ"},
                    "yaxis": {"title": "Frequency"},
                },
            }
        }

    def plot_histogram(self, filename):
        from matplotlib import pyplot as plt

        normalised_score = self.normalised_delta_cc
        plt.figure()
        bins = frange(
            math.floor(flex.min(normalised_score)),
            math.ceil(flex.max(normalised_score)) + 1,
            step=0.1,
        )
        plt.hist(normalised_score.as_numpy_array(), bins=bins, fill=False)
        plt.xlabel(r"$\sigma$")
        plt.ylabel("Frequency")
        plt.savefig(filename)

    def normalised_scores(self):
        return {
            "delta_cc_half_normalised_score": {
                "data": [
                    {
                        "y": list(self.normalised_delta_cc),
                        "type": "scatter",
                        "mode": "lines",
                        "name": "delta_cc_half_normalised_score",
                    }
                ],
                "layout": {
                    "title": "Normalised ΔCC<sub>½</sub>",
                    "xaxis": {"title": "Group"},
                    "yaxis": {"title": "σ"},
                },
            }
        }

    def plot_normalised_scores(self, filename):
        from matplotlib import pyplot as plt

        normalised_score = self.normalised_delta_cc
        plt.figure()
        plt.plot(normalised_score)
        plt.xlabel("Group")
        plt.ylabel(r"$\sigma$")
        plt.savefig(filename)
