# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import json
import os
from collections import OrderedDict

import iotbx.phil
from xia2.Modules.Report import Report
from dials.util.options import OptionParser


phil_scope = iotbx.phil.parse(
    """\
title = 'xia2 report'
  .type = str
prefix = 'xia2'
  .type = str
log_include = None
  .type = path
include scope xia2.Modules.Analysis.phil_scope
json {
  indent = None
    .type = int(value_min=0)
}
""",
    process_includes=True,
)

help_message = """
"""


def run(args):
    from xia2.XIA2Version import Version

    usage = "xia2.report [options] scaled_unmerged.mtz"

    parser = OptionParser(
        usage=usage, phil=phil_scope, check_format=False, epilog=help_message
    )

    params, options, args = parser.parse_args(
        show_diff_phil=True, return_unhandled=True
    )
    if len(args) == 0:
        parser.print_help()
        return

    unmerged_mtz = args[0]

    report = Report.from_unmerged_mtz(unmerged_mtz, params, report_dir=".")

    # xtriage
    xtriage_success, xtriage_warnings, xtriage_danger = None, None, None
    if params.xtriage_analysis:
        xtriage_success, xtriage_warnings, xtriage_danger = report.xtriage_report()

    json_data = {}

    if params.xtriage_analysis:
        json_data["xtriage"] = xtriage_success + xtriage_warnings + xtriage_danger

    overall_stats_table, merging_stats_table, stats_plots = (
        report.resolution_plots_and_stats()
    )

    json_data.update(stats_plots)
    json_data.update(report.batch_dependent_plots())
    json_data.update(report.intensity_stats_plots(run_xtriage=False))
    json_data.update(report.pychef_plots())

    resolution_graphs = OrderedDict(
        (k, json_data[k])
        for k in (
            "cc_one_half",
            "i_over_sig_i",
            "second_moments",
            "wilson_intensity_plot",
            "completeness",
            "multiplicity_vs_resolution",
        )
        if k in json_data
    )

    if params.include_radiation_damage:
        batch_graphs = OrderedDict(
            (k, json_data[k])
            for k in (
                "scale_rmerge_vs_batch",
                "i_over_sig_i_vs_batch",
                "completeness_vs_dose",
                "rcp_vs_dose",
                "scp_vs_dose",
                "rd_vs_batch_difference",
            )
        )
    else:
        batch_graphs = OrderedDict(
            (k, json_data[k])
            for k in ("scale_rmerge_vs_batch", "i_over_sig_i_vs_batch")
        )

    misc_graphs = OrderedDict(
        (k, json_data[k])
        for k in ("cumulative_intensity_distribution", "l_test", "multiplicities")
        if k in json_data
    )

    for k, v in report.multiplicity_plots().iteritems():
        misc_graphs[k] = {"img": v}

    styles = {}
    for axis in ("h", "k", "l"):
        styles["multiplicity_%s" % axis] = "square-plot"

    from jinja2 import Environment, ChoiceLoader, PackageLoader

    loader = ChoiceLoader(
        [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
    )
    env = Environment(loader=loader)

    if params.log_include:
        with open(params.log_include, "rb") as f:
            log_text = f.read().decode("utf-8")
    else:
        log_text = ""

    template = env.get_template("report.html")
    html = template.render(
        page_title=params.title,
        filename=os.path.abspath(unmerged_mtz),
        space_group=report.intensities.space_group_info().symbol_and_number(),
        unit_cell=str(report.intensities.unit_cell()),
        mtz_history=[h.strip() for h in report.mtz_object.history()],
        xtriage_success=xtriage_success,
        xtriage_warnings=xtriage_warnings,
        xtriage_danger=xtriage_danger,
        overall_stats_table=overall_stats_table,
        merging_stats_table=merging_stats_table,
        cc_half_significance_level=params.cc_half_significance_level,
        resolution_graphs=resolution_graphs,
        batch_graphs=batch_graphs,
        misc_graphs=misc_graphs,
        styles=styles,
        xia2_version=Version,
        log_text=log_text,
    )

    with open("%s-report.json" % params.prefix, "wb") as f:
        json.dump(json_data, f, indent=params.json.indent)

    with open("%s-report.html" % params.prefix, "wb") as f:
        f.write(html.encode("utf-8", "xmlcharrefreplace"))


if __name__ == "__main__":
    import sys

    run(sys.argv[1:])
