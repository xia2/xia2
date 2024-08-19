from __future__ import annotations

import math
from typing import Dict, List

import numpy as np
from dials.algorithms.clustering.unit_cell import Cluster
from dials.algorithms.scaling.scaling_library import (
    DialsMergingStatisticsError,
    merging_stats_from_scaled_array,
    scaled_data_as_miller_array,
)
from dials.report.analysis import format_statistics, table_1_stats
from dials.util.resolution_analysis import resolution_cc_half


def condensed_unit_cell_info(clusters: List[Cluster]) -> str:
    out_str = "Unit cell clustering for largest clusters (median & stdev)"
    al, be, ga = "med_" + "\u03b1", "med_" + "\u03b2", "med_" + "\u03b3"
    out_str += f"\n{'n_xtals'} {'s.g.':>7} {'med_a':>7} {'med_b':>7} {'med_c':>7} {al:>6} {be:>6} {ga:>6}"

    for cluster in clusters:
        sorted_pg_comp = sorted(
            cluster.pg_composition.items(),
            key=lambda x: -1 * x[1],
        )
        pg_str = ",".join([str(pg[0]) for pg in sorted_pg_comp])
        p = [f"{i:.2f}" for i in cluster.median_cell]
        sds = [f"{i:.2f}" for i in cluster.cell_std]
        out_str += f"\n{len(cluster):>7} {pg_str:>7} {p[0]:>7} {p[1]:>7} {p[2]:>7} {p[3]:>6} {p[4]:>6} {p[5]:>6}"
        out_str += f"\n{'':>7} {'':>7} {sds[0]:>7} {sds[1]:>7} {sds[2]:>7} {sds[3]:>6} {sds[4]:>6} {sds[5]:>6}"
    return out_str


def condensed_metric_unit_cell_info(clusters: List[Cluster]) -> str:
    from xia2.Modules.SSX.data_integration_programs import best_cell_from_cluster

    out_str = "Highest possible symmetries and metric unit cells for clusters"
    al, be, ga = "med_" + "\u03b1", "med_" + "\u03b2", "med_" + "\u03b3"
    out_str += f"\n{'n_xtals'} {'sym.':>10} {'med_a':>7} {'med_b':>7} {'med_c':>7} {al:>6} {be:>6} {ga:>6}"
    for c in clusters:
        sg, uc = best_cell_from_cluster(c)
        p = [f"{i:.2f}" for i in uc]
        out_str += f"\n{len(c):>7} {sg:>10} {p[0]:>7} {p[1]:>7} {p[2]:>7} {p[3]:>6} {p[4]:>6} {p[5]:>6}"
    return out_str


def indexing_summary_output(summary_data: Dict, summary_plots: Dict) -> str:
    success = [
        str(len(v)) if len(v) > 1 else "\u2713" if v[0]["n_indexed"] else "."
        for v in summary_data.values()
    ]
    output_ = ""
    block_width = 50
    for i in range(0, math.ceil(len(success) / block_width)):
        row_ = success[i * block_width : (i + 1) * block_width]
        output_ += "".join(row_) + "\n"
    if not summary_plots:
        return output_

    # Now determine the IQR for the rmsds
    output_ += "Indexing summary statistics (median and IQR):\n"
    output_ += f"{'Quantity':<28} {'Q1':>6} Median {'Q3':>6}"

    rmsdx = [i["y"] for i in summary_plots["rmsds"]["data"][::2]]
    rmsdy = [i["y"] for i in summary_plots["rmsds"]["data"][1::2]]
    rmsdz = (
        [i["y"] for i in summary_plots["rmsdz"]["data"]]
        if summary_plots["rmsdz"]
        else [[0.0] * len(rmsdy[0])]
    )
    for name, vals in zip(
        ["RMSD_X", "RMSD_Y", "RMSD_dPsi (deg)"], [rmsdx, rmsdy, rmsdz]
    ):
        x = np.concatenate([np.array(i) for i in vals])
        n = x.size
        sorted_x = np.sort(x)
        Q1 = f"{sorted_x[n // 4]:.4f}"
        Q2 = f"{sorted_x[n // 2]:.4f}"
        Q3 = f"{sorted_x[3 * n // 4]:.4f}"
        output_ += f"\n{name:<28} {Q1:>6} {Q2:>6} {Q3:>6}"
    percent_idx = np.array(summary_plots["percent_indexed"]["data"][0]["y"])
    name = f"{'%'} spots indexed per image"
    percent_idx = percent_idx[percent_idx > 0]
    n = percent_idx.size
    sorted_x = np.sort(percent_idx)
    Q1 = f"{sorted_x[n // 4]:3.2f}"
    Q2 = f"{sorted_x[n // 2]:3.2f}"
    Q3 = f"{sorted_x[3 * n // 4]:3.2f}"
    output_ += f"\n{name:<28} {Q1:>6} {Q2:>6} {Q3:>6}"
    return output_


def statistics_output_and_resolution_from_scaler(scaler):
    stats = scaler.merging_statistics_result
    anom_stats = None
    if not scaler.scaled_miller_array.space_group().is_centric():
        anom_stats = scaler.anom_merging_statistics_result

    t1_stats = ""
    d_min_fit = None

    if scaler.params.cut_data.d_min is not None:
        t1_stats = format_statistics(table_1_stats(stats, anom_stats))
    elif stats:
        t1_stats, d_min_fit = _fit_stats(
            stats,
            anom_stats,
            scaler.scaled_miller_array,
            scaler.params.output.merging.nbins,
            scaler.params.output.use_internal_variance,
        )
    return (t1_stats, d_min_fit)


def statistics_output_from_scaled_files(
    experiments, reflection_table, best_unit_cell, d_min=None
):
    scaled_array = scaled_data_as_miller_array(
        [reflection_table], experiments, best_unit_cell
    )
    t1_stats = ""
    d_min_fit = None

    if d_min:
        scaled_array = scaled_array.select(scaled_array.d_spacings().data() >= d_min)
        try:
            stats, anom_stats = merging_stats_from_scaled_array(
                scaled_array, additional_stats=True
            )
        except DialsMergingStatisticsError:
            pass
        else:
            if scaled_array.space_group().is_centric():
                anom_stats = None
            if stats:
                t1_stats = format_statistics(table_1_stats(stats, anom_stats))

    else:  # estimate resolution limit
        try:
            stats, anom_stats = merging_stats_from_scaled_array(
                scaled_array, additional_stats=True
            )
        except DialsMergingStatisticsError:
            pass
        else:
            if scaled_array.space_group().is_centric():
                anom_stats = None
            if stats:
                t1_stats, d_min_fit = _fit_stats(stats, anom_stats, scaled_array)

    return (t1_stats, d_min_fit)


def _fit_stats(stats, anom_stats, scaled_array, n_bins=20, use_internal_variance=False):
    fit_msg = ""
    d_min_fit = None
    cut_stats, cut_anom_stats = (None, None)
    try:
        d_min_fit = resolution_cc_half(stats, limit=0.3).d_min
    except RuntimeError:
        pass
    else:
        max_current_res = stats.bins[-1].d_min
        if d_min_fit and d_min_fit - max_current_res > 0.005:
            fit_msg = (
                "Approximate resolution limit suggested from CC"
                + "\u00bd"
                + " fit (limit CC"
                + "\u00bd"
                + f"=0.3): {d_min_fit:.2f}"
                + "\n"
            )
            try:
                cut_stats, cut_anom_stats = merging_stats_from_scaled_array(
                    scaled_array.resolution_filter(d_min=d_min_fit),
                    n_bins=n_bins,
                    use_internal_variance=use_internal_variance,
                    additional_stats=True,
                )
            except DialsMergingStatisticsError:
                pass
            else:
                if scaled_array.space_group().is_centric():
                    cut_anom_stats = None
    if not d_min_fit:
        fit_msg = (
            "Unable to estimate resolution limit from CC" + "\u00bd" + " fit" + "\n"
        )
    t1_stats = format_statistics(
        table_1_stats(stats, anom_stats, cut_stats, cut_anom_stats)
    )
    return (fit_msg + t1_stats, d_min_fit)
