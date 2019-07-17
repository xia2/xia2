from __future__ import absolute_import, division, print_function

import sys

import iotbx.phil
from cctbx import crystal
from cctbx.array_family import flex
from libtbx.phil import command_line
from xia2.Modules.Analysis import separate_unmerged

master_phil_scope = iotbx.phil.parse(
    """\
cc_one_half_method = half_dataset *sigma_tau
  .type = choice
unit_cell = None
  .type = unit_cell
n_bins = 20
  .type = int(value_min=1)
d_min = None
  .type = float(value_min=0)
batch
  .multiple = True
{
  id = None
    .type = str
  range = None
    .type = ints(size=2, value_min=0)
}
include scope xia2.Modules.MultiCrystalAnalysis.batch_phil_scope
""",
    process_includes=True,
)


class delta_cc_half(object):
    def __init__(
        self,
        unmerged_intensities,
        batches_all,
        n_bins=20,
        d_min=None,
        cc_one_half_method="sigma_tau",
        id_to_batches=None,
    ):

        sel = unmerged_intensities.sigmas() > 0
        unmerged_intensities = unmerged_intensities.select(sel).set_info(
            unmerged_intensities.info()
        )
        batches_all = batches_all.select(sel)

        unmerged_intensities.setup_binner(n_bins=n_bins)
        self.unmerged_intensities = unmerged_intensities
        self.merged_intensities = unmerged_intensities.merge_equivalents().array()

        separate = separate_unmerged(
            unmerged_intensities, batches_all, id_to_batches=id_to_batches
        )
        self.intensities = separate.intensities
        self.batches = separate.batches
        self.run_id_to_batch_id = separate.run_id_to_batch_id

        from iotbx.merging_statistics import dataset_statistics

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
        self.merging_statistics.show()

        self.delta_cc = flex.double()
        for test_k in self.intensities.keys():
            # print test_k
            indices_i = flex.miller_index()
            data_i = flex.double()
            sigmas_i = flex.double()
            for k, unmerged in self.intensities.iteritems():
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

    def _labels(self):
        if self.run_id_to_batch_id is not None:
            labels = self.run_id_to_batch_id.values()
        else:
            labels = ["%i" % (j + 1) for j in range(len(self.delta_cc))]
        return labels

    def _normalised_delta_cc_i(self):
        mav = flex.mean_and_variance(self.delta_cc)
        return (self.delta_cc - mav.mean()) / mav.unweighted_sample_standard_deviation()

    def get_table(self):
        from libtbx import table_utils

        rows = [["dataset", "batches", "delta_cc_i", "sigma"]]
        labels = self._labels()
        normalised_score = self._normalised_delta_cc_i()
        perm = flex.sort_permutation(self.delta_cc)
        for i in perm:
            bmin = flex.min(self.batches[i].data())
            bmax = flex.max(self.batches[i].data())
            rows.append(
                [
                    str(labels[i]),
                    "%i to %i" % (bmin, bmax),
                    "% .3f" % self.delta_cc[i],
                    "% .2f" % normalised_score[i],
                ]
            )
        return table_utils.format(rows, has_header=True, prefix="|", postfix="|")

    def plot_histogram(self, filename):
        import math
        from matplotlib import pyplot

        normalised_score = self._normalised_delta_cc_i()
        pyplot.figure()
        # bins = range(
        # int(math.floor(flex.min(normalised_score))), int(math.ceil(flex.max(normalised_score)))+1)
        from libtbx.utils import frange

        bins = frange(
            math.floor(flex.min(normalised_score)),
            math.ceil(flex.max(normalised_score)) + 1,
            step=0.1,
        )
        n, bins, patches = pyplot.hist(
            normalised_score.as_numpy_array(), bins=bins, fill=False
        )
        pyplot.xlabel(r"$\sigma$")
        pyplot.ylabel("Frequency")
        pyplot.savefig(filename)


def run(args):

    cmd_line = command_line.argument_interpreter(master_params=master_phil_scope)
    working_phil, args = cmd_line.process_and_fetch(
        args=args, custom_processor="collect_remaining"
    )
    working_phil.show()
    params = working_phil.extract()

    if params.unit_cell is not None:
        unit_cell = params.unit_cell
        crystal_symmetry = crystal.symmetry(unit_cell=unit_cell)
    else:
        crystal_symmetry = None

    from iotbx.reflection_file_reader import any_reflection_file

    result = any_reflection_file(args[0])
    unmerged_intensities = None
    batches_all = None

    for ma in result.as_miller_arrays(
        merge_equivalents=False, crystal_symmetry=crystal_symmetry
    ):
        # print ma.info().labels
        if ma.info().labels == ["I(+)", "SIGI(+)", "I(-)", "SIGI(-)"]:
            assert ma.anomalous_flag()
            unmerged_intensities = ma
        elif ma.info().labels == ["I", "SIGI"]:
            assert not ma.anomalous_flag()
            unmerged_intensities = ma
        elif ma.info().labels == ["BATCH"]:
            batches_all = ma

    assert batches_all is not None
    assert unmerged_intensities is not None

    id_to_batches = None

    if len(params.batch) > 0:
        id_to_batches = {}
        for b in params.batch:
            assert b.id is not None
            assert b.range is not None
            assert b.id not in id_to_batches, "Duplicate batch id: %s" % b.id
            id_to_batches[b.id] = b.range

    result = delta_cc_half(
        unmerged_intensities,
        batches_all,
        n_bins=params.n_bins,
        d_min=params.d_min,
        cc_one_half_method=params.cc_one_half_method,
        id_to_batches=id_to_batches,
    )
    hist_filename = "delta_cc_hist.png"
    print("Saving histogram to %s" % hist_filename)
    result.plot_histogram(hist_filename)
    print(result.get_table())
    from xia2.Handlers.Citations import Citations

    Citations.cite("delta_cc_half")
    for citation in Citations.get_citations_acta():
        print(citation)


if __name__ == "__main__":
    run(sys.argv[1:])
