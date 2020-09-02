# LIBTBX_SET_DISPATCHER_NAME xia2.html

import glob
import html
import json
import logging
import os
import re
import sys
import traceback
from collections import OrderedDict

from libtbx import phil
import xia2
from xia2.Modules.Report import Report
from xia2.Handlers.Citations import Citations
import xia2.Handlers.Streams

logger = logging.getLogger("xia2.command_line.html")


def run(args):
    assert os.path.exists("xia2.json")
    from xia2.Schema.XProject import XProject

    xinfo = XProject.from_json(filename="xia2.json")
    generate_xia2_html(xinfo, args=args)


def generate_xia2_html(xinfo, filename="xia2.html", params=None, args=[]):
    assert params is None or len(args) == 0
    if params is None:
        from xia2.Modules.Analysis import phil_scope

        interp = phil_scope.command_line_argument_interpreter()
        params, unhandled = interp.process_and_fetch(
            args, custom_processor="collect_remaining"
        )
        params = params.extract()

    xia2_txt = os.path.join(os.path.abspath(os.path.curdir), "xia2.txt")
    assert os.path.isfile(xia2_txt), xia2_txt

    with open(xia2_txt, "r") as f:
        xia2_output = html.escape(f.read())

    styles = {}

    columns = []
    columns.append(
        [
            "",
            "Wavelength (Å)",
            "Resolution range (Å)",
            "Completeness (%)",
            "Multiplicity",
            "CC-half",
            "I/sigma",
            "Rmerge(I)",
            # anomalous statistics
            "Anomalous completeness (%)",
            "Anomalous multiplicity",
        ]
    )

    individual_dataset_reports = {}

    for cname, xcryst in xinfo.get_crystals().items():
        reflection_files = xcryst.get_scaled_merged_reflections()
        for wname, unmerged_mtz in reflection_files["mtz_unmerged"].items():
            xwav = xcryst.get_xwavelength(wname)

            from xia2.Modules.MultiCrystalAnalysis import batch_phil_scope

            scope = phil.parse(batch_phil_scope)
            scaler = xcryst._scaler
            try:
                for si in scaler._sweep_information.values():
                    batch_params = scope.extract().batch[0]
                    batch_params.id = si["sname"]
                    batch_params.range = si["batches"]
                    params.batch.append(batch_params)
            except AttributeError:
                for si in scaler._sweep_handler._sweep_information.values():
                    batch_params = scope.extract().batch[0]
                    batch_params.id = si.get_sweep_name()
                    batch_params.range = si.get_batch_range()
                    params.batch.append(batch_params)

            report_path = xinfo.path.joinpath(cname, "report")
            report_path.mkdir(parents=True, exist_ok=True)
            report = Report.from_unmerged_mtz(
                unmerged_mtz, params, report_dir=str(report_path)
            )

            xtriage_success, xtriage_warnings, xtriage_danger = None, None, None
            if params.xtriage_analysis:
                try:
                    (
                        xtriage_success,
                        xtriage_warnings,
                        xtriage_danger,
                    ) = report.xtriage_report()
                except Exception as e:
                    params.xtriage_analysis = False
                    logger.debug("Exception running xtriage:")
                    logger.debug(e, exc_info=True)

            (
                overall_stats_table,
                merging_stats_table,
                stats_plots,
            ) = report.resolution_plots_and_stats()

            d = {}
            d["merging_statistics_table"] = merging_stats_table
            d["overall_statistics_table"] = overall_stats_table

            individual_dataset_reports[wname] = d

            json_data = {}

            if params.xtriage_analysis:
                json_data["xtriage"] = (
                    xtriage_success + xtriage_warnings + xtriage_danger
                )

            json_data.update(stats_plots)
            json_data.update(report.batch_dependent_plots())
            json_data.update(report.intensity_stats_plots(run_xtriage=False))
            json_data.update(report.pychef_plots())
            json_data.update(report.pychef_plots(n_bins=1))

            from scitbx.array_family import flex

            max_points = 500
            for g in (
                "scale_rmerge_vs_batch",
                "completeness_vs_dose",
                "rcp_vs_dose",
                "scp_vs_dose",
                "rd_vs_batch_difference",
            ):
                for i, data in enumerate(json_data[g]["data"]):
                    x = data["x"]
                    n = len(x)
                    if n > max_points:
                        step = n // max_points
                        sel = (flex.int_range(n) % step) == 0
                        data["x"] = list(flex.int(data["x"]).select(sel))
                        data["y"] = list(flex.double(data["y"]).select(sel))

            resolution_graphs = OrderedDict(
                (k + "_" + wname, json_data[k])
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
                    (k + "_" + wname, json_data[k])
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
                    (k + "_" + wname, json_data[k])
                    for k in ("scale_rmerge_vs_batch", "i_over_sig_i_vs_batch")
                )

            misc_graphs = OrderedDict(
                (k, json_data[k])
                for k in (
                    "cumulative_intensity_distribution",
                    "l_test",
                    "multiplicities",
                )
                if k in json_data
            )

            for k, v in report.multiplicity_plots().items():
                misc_graphs[k + "_" + wname] = {"img": v}

            d["resolution_graphs"] = resolution_graphs
            d["batch_graphs"] = batch_graphs
            d["misc_graphs"] = misc_graphs
            d["xtriage"] = {
                "success": xtriage_success,
                "warnings": xtriage_warnings,
                "danger": xtriage_danger,
            }

            merging_stats = report.merging_stats
            merging_stats_anom = report.merging_stats_anom

            overall = merging_stats.overall
            overall_anom = merging_stats_anom.overall
            outer_shell = merging_stats.bins[-1]
            outer_shell_anom = merging_stats_anom.bins[-1]

            column = [
                wname,
                str(xwav.get_wavelength()),
                "%.2f - %.2f (%.2f - %.2f)"
                % (overall.d_max, overall.d_min, outer_shell.d_max, outer_shell.d_min),
                "%.2f (%.2f)"
                % (overall.completeness * 100, outer_shell.completeness * 100),
                f"{overall.mean_redundancy:.2f} ({outer_shell.mean_redundancy:.2f})",
                f"{overall.cc_one_half:.4f} ({outer_shell.cc_one_half:.4f})",
                "%.2f (%.2f)"
                % (overall.i_over_sigma_mean, outer_shell.i_over_sigma_mean),
                f"{overall.r_merge:.4f} ({outer_shell.r_merge:.4f})",
                # anomalous statistics
                "%.2f (%.2f)"
                % (
                    overall_anom.anom_completeness * 100,
                    outer_shell_anom.anom_completeness * 100,
                ),
                "%.2f (%.2f)"
                % (overall_anom.mean_redundancy, outer_shell_anom.mean_redundancy),
            ]
            columns.append(column)

    table = [[c[i] for c in columns] for i in range(len(columns[0]))]

    from cctbx import sgtbx

    space_groups = xcryst.get_likely_spacegroups()
    space_groups = [
        sgtbx.space_group_info(symbol=str(symbol)) for symbol in space_groups
    ]
    space_group = space_groups[0].symbol_and_number()
    alternative_space_groups = [sg.symbol_and_number() for sg in space_groups[1:]]
    unit_cell = str(report.intensities.unit_cell())

    # reflection files

    for cname, xcryst in xinfo.get_crystals().items():
        # hack to replace path to reflection files with DataFiles directory
        data_dir = os.path.join(os.path.abspath(os.path.curdir), "DataFiles")
        g = glob.glob(os.path.join(data_dir, "*"))
        reflection_files = xcryst.get_scaled_merged_reflections()
        for k, rfile in reflection_files.items():
            if isinstance(rfile, str):
                for datafile in g:
                    if os.path.basename(datafile) == os.path.basename(rfile):
                        reflection_files[k] = datafile
                        break
            else:
                for kk in rfile:
                    for datafile in g:
                        if os.path.basename(datafile) == os.path.basename(rfile[kk]):
                            reflection_files[k][kk] = datafile
                            break

        headers = ["Dataset", "File name"]
        merged_mtz = reflection_files["mtz"]
        mtz_files = [
            headers,
            [
                "All datasets",
                '<a href="%s">%s</a>'
                % (os.path.relpath(merged_mtz), os.path.basename(merged_mtz)),
            ],
        ]

        for wname, unmerged_mtz in reflection_files["mtz_unmerged"].items():
            mtz_files.append(
                [
                    wname,
                    '<a href="%s">%s</a>'
                    % (os.path.relpath(unmerged_mtz), os.path.basename(unmerged_mtz)),
                ]
            )

        sca_files = [headers]
        if "sca" in reflection_files:
            for wname, merged_sca in reflection_files["sca"].items():
                sca_files.append(
                    [
                        wname,
                        '<a href="%s">%s</a>'
                        % (os.path.relpath(merged_sca), os.path.basename(merged_sca)),
                    ]
                )

        unmerged_sca_files = [headers]
        if "sca_unmerged" in reflection_files:
            for wname, unmerged_sca in reflection_files["sca_unmerged"].items():
                unmerged_sca_files.append(
                    [
                        wname,
                        '<a href="%s">%s</a>'
                        % (
                            os.path.relpath(unmerged_sca),
                            os.path.basename(unmerged_sca),
                        ),
                    ]
                )

    # other files
    other_files = []
    other_files.append(["File name", "Description"])
    for other_file, description in sorted(
        [
            ("xia2.cif", "Crystallographic information file"),
            ("xia2.mmcif", "Macromolecular crystallographic information file"),
            ("shelxt.hkl", "merged structure factors for SHELXT"),
            ("shelxt.ins", "SHELXT instruction file"),
        ]
        + [
            (fn, "XPREP input file")
            for fn in os.listdir(os.path.join(data_dir))
            if fn.endswith(".p4p")
        ]
    ):
        if os.path.exists(os.path.join(data_dir, other_file)):
            other_files.append(
                [
                    '<a href="DataFiles/{filename}">{filename}</a>'.format(
                        filename=other_file
                    ),
                    description,
                ]
            )

    # log files
    log_files_table = []
    log_dir = os.path.join(os.path.abspath(os.path.curdir), "LogFiles")
    g = glob.glob(os.path.join(log_dir, "*.log"))
    for logfile in g:
        html_file = make_logfile_html(logfile)
        html_file = os.path.splitext(logfile)[0] + ".html"
        if os.path.exists(html_file):
            log_files_table.append(
                [
                    os.path.basename(logfile),
                    '<a href="%s">original</a>' % os.path.relpath(logfile),
                    '<a href="%s">html</a>' % os.path.relpath(html_file),
                ]
            )
        else:
            log_files_table.append(
                [
                    os.path.basename(logfile),
                    '<a href="%s">original</a>' % os.path.relpath(logfile),
                    " ",
                ]
            )

    references = {
        cdict["acta"]: cdict.get("url") for cdict in Citations.get_citations_dicts()
    }

    from jinja2 import Environment, ChoiceLoader, PackageLoader

    loader = ChoiceLoader(
        [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
    )
    env = Environment(loader=loader)

    template = env.get_template("xia2.html")
    html_source = template.render(
        page_title="xia2 processing report",
        xia2_output=xia2_output,
        space_group=space_group,
        alternative_space_groups=alternative_space_groups,
        unit_cell=unit_cell,
        overall_stats_table=table,
        cc_half_significance_level=params.cc_half_significance_level,
        mtz_files=mtz_files,
        sca_files=sca_files,
        unmerged_sca_files=unmerged_sca_files,
        other_files=other_files,
        log_files_table=log_files_table,
        individual_dataset_reports=individual_dataset_reports,
        references=references,
        styles=styles,
    )

    with open("%s-report.json" % os.path.splitext(filename)[0], "w") as fh:
        json.dump(json_data, fh, indent=2)

    with open(filename, "wb") as f:
        f.write(html_source.encode("utf-8", "xmlcharrefreplace"))


def make_logfile_html(logfile):
    tables = extract_loggraph_tables(logfile)
    if not tables:
        return

    rst = []
    ## local files in xia2 distro
    # c3css = os.path.join(xia2_root_dir, 'c3', 'c3.css')
    # c3js = os.path.join(xia2_root_dir, 'c3', 'c3.min.js')
    # d3js = os.path.join(xia2_root_dir, 'd3', 'd3.min.js')

    # webhosted files
    c3css = "https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.10/c3.css"
    c3js = "https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.10/c3.min.js"
    d3js = "https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min.js"

    rst.append(".. raw:: html")
    rst.append(
        "\n    ".join(
            [
                "",
                "<!-- Load c3.css -->",
                '<link href="%s" rel="stylesheet" type="text/css">' % c3css,
                "<!-- Load d3.js and c3.js -->",
                '<script src="%s" charset="utf-8"></script>' % d3js,
                '<script src="%s"></script>' % c3js,
                "",
            ]
        )
    )

    for table in tables:
        try:
            for graph_name, htmlcode in table_to_c3js_charts(table).items():
                rst.append(".. raw:: html")
                rst.append("\n    ".join(htmlcode.split("\n")))
        except Exception as e:
            logger.info("=" * 80)
            logger.info("Error (%s) while processing table", str(e))
            logger.info("  '%s'", table.title)
            logger.info("in %s", logfile)
            logger.info("=" * 80)
            logger.debug(
                "Exception raised while processing log file %s, table %s",
                logfile,
                table.title,
            )
            logger.debug(traceback.format_exc())

    rst = "\n".join(rst)

    html_file = "%s.html" % (os.path.splitext(logfile)[0])
    with open(html_file, "wb") as f:
        f.write(rst2html(rst))
    return html_file


def rst2html(rst):
    from docutils.core import publish_string
    from docutils.writers.html4css1 import Writer, HTMLTranslator

    class xia2HTMLTranslator(HTMLTranslator):
        def __init__(self, document):
            HTMLTranslator.__init__(self, document)

        def visit_table(self, node):
            self.context.append(self.compact_p)
            self.compact_p = True
            classes = " ".join(["docutils", self.settings.table_style]).strip()
            self.body.append(self.starttag(node, "table", CLASS=classes, border="0"))

        def write_colspecs(self):
            self.colspecs = []

    xia2_root_dir = os.path.dirname(xia2.__file__)

    args = {"stylesheet_path": os.path.join(xia2_root_dir, "css", "voidspace.css")}

    w = Writer()
    w.translator_class = xia2HTMLTranslator

    return publish_string(rst, writer=w, settings=None, settings_overrides=args)


def extract_loggraph_tables(logfile):
    from iotbx import data_plots

    return data_plots.import_ccp4i_logfile(file_name=logfile)


def table_to_c3js_charts(table):
    html_graphs = {}
    draw_chart_template = """
var chart_%(name)s = c3.generate({
    bindto: '#chart_%(name)s',
    data: %(data)s,
    axis: %(axis)s,
    legend: {
      position: 'right'
    },
});
"""
    divs = []

    for i_graph, graph_name in enumerate(table.graph_names):
        # print graph_name

        script = ['<script type="text/javascript">']

        name = re.sub("[^a-zA-Z]", "", graph_name)

        row_dicts = []
        graph_columns = table.graph_columns[i_graph]
        for row in zip(*[table.data[i_col] for i_col in graph_columns]):
            row_dict = {"name": ""}
            for i_col, c in enumerate(row):
                row_dict[table.column_labels[graph_columns[i_col]]] = c
            row_dicts.append(row_dict)

        data_dict = {
            "json": row_dicts,
            "keys": {
                "x": table.column_labels[graph_columns[0]],
                "value": [table.column_labels[i_col] for i_col in graph_columns[1:]],
            },
        }

        xlabel = table.column_labels[graph_columns[0]]
        if xlabel in ("1/d^2", "1/resol^2"):
            xlabel = "Resolution (Å)"
            tick = """\
tick: {
          format: function (x) { return (1/Math.sqrt(x)).toFixed(2); }
        }
"""
        else:
            tick = ""

        axis = """
    {
      x: {
        label: {
          text: '%(text)s',
          position: 'outer-center'
        },
        %(tick)s
      }
    }
""" % {
            "text": xlabel,
            "tick": tick,
        }

        script.append(
            draw_chart_template
            % ({"name": name, "id": name, "data": json.dumps(data_dict), "axis": axis})
        )

        divs = [
            f"""\
<div>
  <p>{html.escape(graph_name)}</p>
  <div class="graph" id="chart_{name}"></div>
</div>"""
        ]

        script.append("</script>")

        html_graphs[
            graph_name
        ] = """
<!--Div that will hold the chart-->
%(div)s

%(script)s

  """ % (
            {"script": "\n".join(script), "div": "\n".join(divs)}
        )

    return html_graphs


if __name__ == "__main__":
    args = sys.argv[1:]
    xia2.Handlers.Streams.setup_logging(logfile="xia2.html.log")
    run(args)
