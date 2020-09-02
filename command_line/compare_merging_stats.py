import concurrent.futures
import functools
import math
import os
import sys

import iotbx.merging_statistics
import iotbx.phil
import libtbx
from libtbx.introspection import number_of_processors
from cctbx import uctbx
from cycler import cycler
from dials.util.options import OptionParser

help_message = """
"""

phil_scope = iotbx.phil.parse(
    """
nproc = Auto
  .type = int(value_min=1)
n_bins = 20
  .type = int(value_min=1)
anomalous = False
  .type = bool
use_internal_variance = False
  .type = bool
eliminate_sys_absent = False
  .type = bool
plot_labels = None
  .type = strings
data_labels = None
  .type = str
size_inches = None
  .type = floats(size=2, value_min=0)
image_dir = None
  .type = path
format = *png pdf
  .type = choice
style = *ggplot
  .type = choice
space_group = None
  .type = space_group
d_min = None
  .type = float
d_max = None
  .type = float
small_multiples = False
  .type = bool
alpha = 0.3
  .type = float(value_min=0, value_max=1)
  .help = "The alpha value for the background line plots in conjunction with"
          "small_multiples=True."
""",
    process_includes=True,
)


def run(args):
    usage = "xia2.compare_merging_stats [options] unmerged1.mtz unmerged2.mtz (..)"

    parser = OptionParser(
        usage=usage, phil=phil_scope, check_format=False, epilog=help_message
    )

    params, options, args = parser.parse_args(
        args, show_diff_phil=True, return_unhandled=True
    )

    if params.nproc is libtbx.Auto:
        params.nproc = number_of_processors()

    results = []
    mtz_files = [arg for arg in args if os.path.isfile(arg)]

    get_merging_stats_partial = functools.partial(
        get_merging_stats,
        anomalous=params.anomalous,
        n_bins=params.n_bins,
        use_internal_variance=params.use_internal_variance,
        eliminate_sys_absent=params.eliminate_sys_absent,
        data_labels=params.data_labels,
        space_group_info=params.space_group,
        d_min=params.d_min,
        d_max=params.d_max,
    )
    with concurrent.futures.ProcessPoolExecutor(max_workers=params.nproc) as pool:
        results = pool.map(get_merging_stats_partial, mtz_files)

    plot_merging_stats(
        list(results),
        labels=params.plot_labels,
        size_inches=params.size_inches,
        image_dir=params.image_dir,
        format=params.format,
        style=params.style,
        small_multiples=params.small_multiples,
        alpha=params.alpha,
    )
    return results


def get_merging_stats(
    scaled_unmerged_mtz,
    anomalous=False,
    n_bins=20,
    use_internal_variance=False,
    eliminate_sys_absent=False,
    data_labels=None,
    space_group_info=None,
    d_min=None,
    d_max=None,
):
    print(scaled_unmerged_mtz)
    i_obs = iotbx.merging_statistics.select_data(
        scaled_unmerged_mtz, data_labels=data_labels
    )
    i_obs = i_obs.customized_copy(anomalous_flag=False, info=i_obs.info())
    if space_group_info is not None:
        i_obs = i_obs.customized_copy(
            space_group_info=space_group_info, info=i_obs.info()
        )
    result = iotbx.merging_statistics.dataset_statistics(
        i_obs=i_obs,
        n_bins=n_bins,
        anomalous=anomalous,
        use_internal_variance=use_internal_variance,
        eliminate_sys_absent=eliminate_sys_absent,
        d_min=d_min,
        d_max=d_max,
    )
    return result


def plot_merging_stats(
    results,
    labels=None,
    plots=None,
    size_inches=None,
    image_dir=None,
    format="png",
    style="ggplot",
    small_multiples=False,
    global_labels=None,
    alpha=0.3,
):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    if style is not None:
        plt.style.use(style)

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    plt.rcParams["axes.titlesize"] = "medium"
    linestyles = []
    for style in ("-", "--", ":", "-."):
        linestyles.extend([style] * len(colors))
    colors = colors * len(set(linestyles))
    plt.rc("axes", prop_cycle=(cycler("c", colors) + cycler("ls", linestyles)))

    plots_ = {
        "r_merge": "$R_{merge}$",
        "r_meas": "$R_{meas}$",
        "r_pim": "$R_{pim}$",
        "cc_one_half": r"$CC_{\frac{1}{2}}$",
        "cc_one_half_sigma_tau": r"$CC_{\frac{1}{2}}$",
        "cc_anom": "$CC_{anom}$",
        "i_over_sigma_mean": r"$< I / \sigma(I) >$",
        "completeness": "Completeness",
        "mean_redundancy": "Multiplicity",
    }

    if plots is None:
        plots = plots_
    else:
        plots = {k: plots_[k] for k in plots}
    if labels is not None:
        assert len(results) == len(labels)
    if image_dir is None:
        image_dir = "."
    elif not os.path.exists(image_dir):
        os.makedirs(image_dir)

    n_rows = 1
    n_cols = 1
    if small_multiples:
        n_rows = int(math.floor(math.sqrt(len(results))))
        n_cols = n_rows
        while n_cols * n_rows < len(results):
            n_cols += 1
        assert n_cols * n_rows >= len(results), (n_cols, n_rows, len(results))

    for k in plots:

        plot_data(
            results,
            k,
            plots.get(k, k),
            labels,
            n_rows=n_rows,
            n_cols=n_cols,
            global_labels=global_labels,
            alpha=alpha,
        )

        if size_inches is not None:
            fig = plt.gcf()
            fig.set_size_inches(size_inches)
        if n_cols == 1 and labels is not None:
            if k.startswith("cc"):
                plt.legend(loc="lower left")
            elif k.startswith("r_"):
                plt.legend(loc="upper left")
            elif k.startswith("i_"):
                plt.legend(loc="upper right")
            else:
                plt.legend(loc="best")
        if global_labels is not None:
            ax = plt.gca()
            handles, lab = ax.get_legend_handles_labels()
            plt.figlegend(handles, lab, loc="lower right")

        plt.tight_layout()
        plt.savefig(os.path.join(image_dir, k + ".%s" % format))
        plt.clf()


def plot_data(
    results,
    k,
    ylabel,
    labels,
    linestyle=None,
    n_rows=None,
    n_cols=None,
    global_labels=None,
    alpha=0.3,
):
    from matplotlib import pyplot as plt

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    ref_ax = None
    for i, result in enumerate(results):
        if not isinstance(result, (list, tuple)):
            result = (result,)
        if labels is not None:
            label = labels[i].replace("\\$", "$")
        else:
            label = None
        if n_cols > 1:
            ax = plt.subplot(n_rows, n_cols, i + 1, sharex=ref_ax, sharey=ref_ax)
            if label:
                ax.set_title(label, loc="left")
            if ref_ax is None:
                ref_ax = ax
            for other in results:
                if isinstance(other, iotbx.merging_statistics.dataset_statistics):
                    other = (other,)
                for res in other:
                    if res is not None:
                        x = [
                            0.5
                            * (
                                uctbx.d_as_d_star_sq(b.d_max)
                                + uctbx.d_as_d_star_sq(b.d_min)
                            )
                            for b in res.bins
                        ]
                        y = [getattr(b, k) for b in res.bins]
                        ax.plot(
                            x,
                            y,
                            linestyle="-",
                            color="grey",
                            linewidth=1,
                            alpha=alpha,
                        )
        else:
            ax = plt.gca()

        for i_res, res in enumerate(result):
            if res is not None:
                if global_labels is not None:
                    l = global_labels[i_res]
                else:
                    l = label
                x = [
                    0.5
                    * (uctbx.d_as_d_star_sq(b.d_max) + uctbx.d_as_d_star_sq(b.d_min))
                    for b in res.bins
                ]
                y = [getattr(b, k) for b in res.bins]
                color = colors[i_res] if n_cols > 1 else colors[i]
                ax.plot(x, y, label=l, linestyle=linestyle, color=color)

        ax.set_xlabel(r"Resolution ($\AA$)")
        ax.set_ylabel(ylabel)
        ax.label_outer()
        if k in ("cc_one_half", "cc_one_half_sigma_tau", "completeness"):
            ax.set_ylim(0, 1.05)
        elif k in ("cc_anom",):
            ax.set_ylim(min(0, ax.get_ylim()[0]), 1.05)
        elif k in ("r_merge",):
            ax.set_ylim(0, min(4, ax.get_ylim()[1]))
        elif k in ("r_meas", "r_pim"):
            ax.set_ylim(0, min(2, ax.get_ylim()[1]))
        else:
            ax.set_ylim(0, ax.get_ylim()[1])
        xticks = ax.get_xticks()
        xticks_d = [
            "%.2f" % uctbx.d_star_sq_as_d(ds2) if ds2 > 0 else 0 for ds2 in xticks
        ]
        ax.set_xticklabels(xticks_d)


if __name__ == "__main__":
    run(sys.argv[1:])
