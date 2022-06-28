from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np

from dials.algorithms.clustering.unit_cell import Cluster
from dials.report.analysis import format_statistics, table_1_stats
from dials.util import tabulate


def condensed_unit_cell_info(clusters: List[Cluster]) -> str:
    out_str = "Unit cell clustering for largest clusters (median & stdev)"
    al, be, ga = "med_" + "\u03B1", "med_" + "\u03B2", "med_" + "\u03B3"
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


def generate_refinement_step_table(refiner: Any) -> str:

    rmsd_multipliers = []
    header = ["Step", "Nref"]
    for (name, units) in zip(refiner._target.rmsd_names, refiner._target.rmsd_units):
        if units == "mm":
            header.append(name + "\n(mm)")
            rmsd_multipliers.append(1.0)
        elif units == "rad":  # convert radians to degrees for reporting
            header.append(name + "\n(deg)")
            rmsd_multipliers.append(180 / math.pi)
        else:  # leave unknown units alone
            header.append(name + "\n(" + units + ")")

    rows = []
    for i in range(refiner._refinery.history.get_nrows()):
        rmsds = [
            r * m
            for (r, m) in zip(refiner._refinery.history["rmsd"][i], rmsd_multipliers)
        ]
        rows.append(
            [str(i), str(refiner._refinery.history["num_reflections"][i])]
            + [f"{r:.5g}" for r in rmsds]
        )
    return tabulate(rows, header)


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
    rmsdz = [i["y"] for i in summary_plots["rmsdz"]["data"]]
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


def statistics_output_from_scaler(scaler: Any) -> str:
    stats = format_statistics(
        table_1_stats(
            scaler.merging_statistics_result,
            scaler.anom_merging_statistics_result,
        )
    )
    return stats


def statistics_output_from_scaled_files(
    experiments, reflection_table, best_unit_cell, d_min=None
):
    from dials.algorithms.scaling.scaling_library import (
        merging_stats_from_scaled_array,
        scaled_data_as_miller_array,
    )

    scaled_array = scaled_data_as_miller_array(
        [reflection_table], experiments, best_unit_cell
    )
    if d_min:
        scaled_array = scaled_array.select(scaled_array.d_spacings().data() >= d_min)
    stats, anom_stats = merging_stats_from_scaled_array(scaled_array)

    stats = format_statistics(table_1_stats(stats, anom_stats))
    return stats
