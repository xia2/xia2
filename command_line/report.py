# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import json
import os
from collections import OrderedDict
from six.moves import cStringIO as StringIO

import iotbx.phil
import xia2.Handlers.Environment
import xia2.Handlers.Files
from cctbx.array_family import flex
from mmtbx.scaling import printed_output
from xia2.Modules.Analysis import *
from dials.util.intensity_explorer import data_from_unmerged_mtz, IntensityDist
from dials.util.options import OptionParser
from dials.util.batch_handling import batch_manager
from dials.report.analysis import batch_dependent_properties
from dials.report.plots import (
    i_over_sig_i_vs_batch_plot,
    scale_rmerge_vs_batch_plot,
    ResolutionPlotsAndStats,
    IntensityStatisticsPlots,
)


class xtriage_output(printed_output):
    def __init__(self, out):
        super(xtriage_output, self).__init__(out)
        self.gui_output = True
        self._out_orig = self.out
        self.out = StringIO()
        self._sub_header_to_out = {}

    def show_big_header(self, text):
        pass

    def show_header(self, text):
        self._out_orig.write(self.out.getvalue())
        self.out = StringIO()
        super(xtriage_output, self).show_header(text)

    def show_sub_header(self, title):
        self._out_orig.write(self.out.getvalue())
        self.out = StringIO()
        self._current_sub_header = title
        assert title not in self._sub_header_to_out
        self._sub_header_to_out[title] = self.out

    def flush(self):
        self._out_orig.write(self.out.getvalue())
        self.out.flush()
        self._out_orig.flush()


class xia2_report_base(object):
    def __init__(self, params, base_dir=None):

        self.params = params

        self.intensities = None
        self.batches = None
        self.scales = None
        self.dose = None
        self._xanalysis = None
        self.report_dir = None

    def report(self):
        assert self.intensities is not None
        # assert self.batches is not None

        if self.batches is not None and len(self.params.batch) == 0:
            from xia2.Modules.MultiCrystalAnalysis import separate_unmerged

            separate = separate_unmerged(self.intensities, self.batches)
            scope = phil.parse(batch_phil_scope)
            for i, batches in separate.batches.iteritems():
                batch_params = scope.extract().batch[0]
                batch_params.id = i
                batch_params.range = (
                    flex.min(batches.data()),
                    flex.max(batches.data()),
                )
                self.params.batch.append(batch_params)

        self._compute_merging_stats()

        if self.params.anomalous:
            self.intensities = self.intensities.as_anomalous_array()
            if self.batches is not None:
                self.batches = self.batches.as_anomalous_array()

        self.intensities.setup_binner(n_bins=self.params.resolution_bins)
        self.merged_intensities = self.intensities.merge_equivalents().array()

        # if params.include_probability_plots:
        #  rtable, elist = data_from_unmerged_mtz(unmerged_mtz)
        #  self.z_score_data = IntensityDist(rtable, elist).rtable

    def _compute_merging_stats(self):

        from iotbx import merging_statistics

        self.merging_stats = merging_statistics.dataset_statistics(
            self.intensities,
            n_bins=self.params.resolution_bins,
            cc_one_half_significance_level=self.params.cc_half_significance_level,
            eliminate_sys_absent=self.params.eliminate_sys_absent,
            use_internal_variance=self.params.use_internal_variance,
            assert_is_not_unique_set_under_symmetry=False,
        )

        intensities_anom = self.intensities.as_anomalous_array()
        intensities_anom = intensities_anom.map_to_asu().customized_copy(
            info=self.intensities.info()
        )
        self.merging_stats_anom = merging_statistics.dataset_statistics(
            intensities_anom,
            n_bins=self.params.resolution_bins,
            anomalous=True,
            cc_one_half_significance_level=self.params.cc_half_significance_level,
            eliminate_sys_absent=self.params.eliminate_sys_absent,
            use_internal_variance=self.params.use_internal_variance,
            assert_is_not_unique_set_under_symmetry=False,
        )

    def multiplicity_plots(self):
        from xia2.command_line.plot_multiplicity import plot_multiplicity, master_phil

        settings = master_phil.extract()
        settings.size_inches = (5, 5)
        settings.show_missing = True
        settings.slice_index = 0

        mult_json_files = {}
        mult_img_files = {}

        rd = self.report_dir or "."

        for settings.slice_axis in ("h", "k", "l"):
            settings.plot.filename = os.path.join(
                rd,
                "multiplicities_%s_%i.png"
                % (settings.slice_axis, settings.slice_index),
            )
            settings.json.filename = os.path.join(
                rd,
                "multiplicities_%s_%i.json"
                % (settings.slice_axis, settings.slice_index),
            )
            # settings.slice_axis = axis
            plot_multiplicity(self.intensities, settings)
            mult_json_files[settings.slice_axis] = settings.json.filename
            with open(settings.plot.filename, "rb") as fh:
                mult_img_files[settings.slice_axis] = (
                    fh.read().encode("base64").replace("\n", "")
                )

        return OrderedDict(
            ("multiplicity_%s" % axis, mult_img_files[axis]) for axis in ("h", "k", "l")
        )

    def symmetry_table_html(self):

        symmetry_table_html = """
  <p>
    <b>Unit cell:</b> %s
    <br>
    <b>Space group:</b> %s
  </p>
""" % (
            self.intensities.space_group_info().symbol_and_number(),
            str(self.intensities.unit_cell()),
        )
        return symmetry_table_html

    def xtriage_report(self):
        xtriage_success = []
        xtriage_warnings = []
        xtriage_danger = []
        s = StringIO()
        pout = printed_output(out=s)
        from mmtbx.scaling.xtriage import xtriage_analyses
        from mmtbx.scaling.xtriage import master_params as xtriage_master_params

        xtriage_params = xtriage_master_params.fetch(sources=[]).extract()
        xtriage_params.scaling.input.xray_data.skip_sanity_checks = True
        xanalysis = xtriage_analyses(
            miller_obs=self.merged_intensities,
            unmerged_obs=self.intensities,
            text_out=pout,
            params=xtriage_params,
        )
        with open(os.path.join(self.report_dir, "xtriage.log"), "wb") as f:
            f.write(s.getvalue())
        xia2.Handlers.Files.FileHandler.record_log_file(
            "Xtriage", os.path.join(self.report_dir, "xtriage.log")
        )
        xs = StringIO()
        xout = xtriage_output(xs)
        xanalysis.show(out=xout)
        xout.flush()
        sub_header_to_out = xout._sub_header_to_out
        issues = xanalysis.summarize_issues()
        # issues.show()

        for level, text, sub_header in issues._issues:
            summary = sub_header_to_out.get(sub_header, StringIO()).getvalue()
            d = {"level": level, "text": text, "summary": summary, "header": sub_header}
            if level == 0:
                xtriage_success.append(d)
            elif level == 1:
                xtriage_warnings.append(d)
            elif level == 2:
                xtriage_danger.append(d)
        self._xanalysis = xanalysis
        return xtriage_success, xtriage_warnings, xtriage_danger

    def batch_dependent_plots(self):

        binned_batches, rmerge, isigi, scalesvsbatch = batch_dependent_properties(
            self.batches, self.intensities, self.scales
        )

        batches = [{"id": b.id, "range": b.range} for b in self.params.batch]
        bm = batch_manager(binned_batches, batches)
        d = {}
        d.update(i_over_sig_i_vs_batch_plot(bm, isigi))
        d.update(scale_rmerge_vs_batch_plot(bm, rmerge, scalesvsbatch))

        return d

    def merging_stats_data(self):
        is_centric = self.intensities.space_group().is_centric()
        plotter = ResolutionPlotsAndStats(
            self.merging_stats, self.merging_stats_anom, is_centric
        )
        d = OrderedDict()
        if self.params.cc_half_method == "sigma_tau":
            d.update(plotter.cc_one_half_plot(method="sigma_tau"))
        else:
            d.update(plotter.cc_one_half_plot())
        d.update(plotter.i_over_sig_i_plot())
        d.update(plotter.completeness_plot())
        d.update(plotter.multiplicity_vs_resolution_plot())
        overall_stats = plotter.overall_statistics_table(self.params.cc_half_method)
        merging_stats = plotter.merging_statistics_table(self.params.cc_half_method)
        return overall_stats, merging_stats, d

    def intensity_stats_plots(self):
        plotter = IntensityStatisticsPlots(
            self.intensities,
            anomalous=self.params.anomalous,
            n_resolution_bins=self.params.resolution_bins,
            xtriage_analyses=self._xanalysis,
        )
        d = {}
        d.update(plotter.generate_resolution_dependent_plots())
        d.update(plotter.generate_miscellanous_plots())
        return d

    def pychef_plots(self, n_bins=8):

        from xia2.Modules import PyChef

        intensities = self.intensities
        batches = self.batches
        dose = self.dose

        if self.params.chef_min_completeness:
            d_min = PyChef.resolution_limit(
                mtz_file=self.unmerged_mtz,
                min_completeness=self.params.chef_min_completeness,
                n_bins=n_bins,
            )
            print("Estimated d_min for CHEF analysis: %.2f" % d_min)
            sel = flex.bool(intensities.size(), True)
            d_spacings = intensities.d_spacings().data()
            sel &= d_spacings >= d_min
            intensities = intensities.select(sel)
            batches = batches.select(sel)
            if dose is not None:
                dose = dose.select(sel)

        if dose is None:
            dose = PyChef.batches_to_dose(batches.data(), self.params.dose)
        else:
            dose = dose.data()
        pychef_stats = PyChef.Statistics(intensities, dose, n_bins=n_bins)

        return pychef_stats.to_dict()

    def z_score_hist(self):
        """
        Plot a histogram of z-scores.

        :return: A dictionary describing a Plotly plot.
        :rtype:`dict`
        """

        z_scores = self.z_score_data["intensity.z_score"]
        hist = flex.histogram(z_scores, -10, 10, 100)

        return {
            "z_score_histogram": {
                "data": [
                    {
                        "x": hist.slot_centers().as_numpy_array().tolist(),
                        "y": hist.slots().as_numpy_array().tolist(),
                        "type": "bar",
                        "name": "z_hist",
                    }
                ],
                "layout": {
                    "title": "Histogram of z-scores",
                    "xaxis": {"title": "z-score", "range": [-10, 10]},
                    "yaxis": {"title": "Number of reflections"},
                    "bargap": 0,
                },
            }
        }

    def normal_probability_plot(self):
        """
        Display a normal probability plot of the z-scores of the intensities.

        :return: A dictionary describing a Plotly plot.
        :rtype:`dict`
        """

        z_scores = self.z_score_data["intensity.z_score"]
        osm = self.z_score_data["intensity.order_statistic_medians"]

        return {
            "normal_probability_plot": {
                "data": [
                    {
                        "x": osm.as_numpy_array().tolist(),
                        "y": z_scores.as_numpy_array().tolist(),
                        "type": "scattergl",
                        "mode": "markers",
                        "name": "Data",
                    },
                    {
                        "x": [-5, 5],
                        "y": [-5, 5],
                        "type": "scatter",
                        "mode": "lines",
                        "name": "z = m",
                    },
                ],
                "layout": {
                    "title": "Normal probability plot",
                    "xaxis": {"title": "z-score order statistic medians, m"},
                    "yaxis": {
                        "title": "Ordered z-score responses, z",
                        "range": [-10, 10],
                    },
                },
            }
        }

    def z_vs_multiplicity(self):
        """
        Plot z-score as a function of multiplicity of observation.

        :return: A dictionary describing a Plotly plot.
        :rtype:`dict`
        """

        multiplicity = self.z_score_data["multiplicity"]
        z_scores = self.z_score_data["intensity.z_score"]

        return {
            "z_score_vs_multiplicity": {
                "data": [
                    {
                        "x": multiplicity.as_numpy_array().tolist(),
                        "y": z_scores.as_numpy_array().tolist(),
                        "type": "scattergl",
                        "mode": "markers",
                        "name": "Data",
                    }
                ],
                "layout": {
                    "title": "z-scores versus multiplicity",
                    "xaxis": {"title": "Multiplicity"},
                    "yaxis": {"title": "z-score"},
                },
            }
        }

    def z_time_series(self):
        """
        Plot a crude time-series of z-scores, with image number serving as a
        proxy for time.

        :return: A dictionary describing a Plotly plot.
        :rtype:`dict`
        """

        batch_number = self.z_score_data["xyzobs.px.value"].parts()[2]
        z_scores = self.z_score_data["intensity.z_score"]

        return {
            "z_score_time_series": {
                "data": [
                    {
                        "x": batch_number.as_numpy_array().tolist(),
                        "y": z_scores.as_numpy_array().tolist(),
                        "type": "scattergl",
                        "mode": "markers",
                        "name": "Data",
                    }
                ],
                "layout": {
                    "title": "z-scores versus image number",
                    "xaxis": {"title": "Image number"},
                    "yaxis": {"title": "z-score"},
                },
            }
        }

    def z_vs_I(self):
        """
        Plot z-scores versus intensity.

        :return: A dictionary describing a Plotly plot.
        :rtype:`dict`
        """

        intensity = self.z_score_data["intensity.mean.value"]
        z_scores = self.z_score_data["intensity.z_score"]

        return {
            "z_score_vs_I": {
                "data": [
                    {
                        "x": intensity.as_numpy_array().tolist(),
                        "y": z_scores.as_numpy_array().tolist(),
                        "type": "scattergl",
                        "mode": "markers",
                        "name": "Data",
                    }
                ],
                "layout": {
                    "title": "z-scores versus weighted mean intensity",
                    "xaxis": {"title": "Intensity (photon count)", "type": "log"},
                    "yaxis": {"title": "z-score"},
                },
            }
        }

    def z_vs_I_over_sigma(self):
        """
        Plot z-scores versus intensity.

        :return: A dictionary describing a Plotly plot.
        :rtype:`dict`
        """

        i_over_sigma = (
            self.z_score_data["intensity.mean.value"]
            / self.z_score_data["intensity.mean.std_error"]
        )
        z_scores = self.z_score_data["intensity.z_score"]

        return {
            "z_score_vs_I_over_sigma": {
                "data": [
                    {
                        "x": i_over_sigma.as_numpy_array().tolist(),
                        "y": z_scores.as_numpy_array().tolist(),
                        "type": "scattergl",
                        "mode": "markers",
                        "name": "Data",
                    }
                ],
                "layout": {
                    "title": u"z-scores versus I/σ",
                    "xaxis": {"title": u"I/σ", "type": "log"},
                    "yaxis": {"title": "z-score"},
                },
            }
        }


class xia2_report(xia2_report_base):
    def __init__(self, unmerged_mtz, params, base_dir=None):

        from iotbx.reflection_file_reader import any_reflection_file

        self.unmerged_mtz = unmerged_mtz
        self.params = params

        reader = any_reflection_file(unmerged_mtz)
        assert reader.file_type() == "ccp4_mtz"
        arrays = reader.as_miller_arrays(merge_equivalents=False)

        self.intensities = None
        self.batches = None
        self.scales = None
        self.dose = None
        self._xanalysis = None

        for ma in arrays:
            if ma.info().labels == ["BATCH"]:
                self.batches = ma
            elif ma.info().labels == ["DOSE"]:
                self.dose = ma
            elif ma.info().labels == ["I", "SIGI"]:
                self.intensities = ma
            elif ma.info().labels == ["I(+)", "SIGI(+)", "I(-)", "SIGI(-)"]:
                self.intensities = ma
            elif ma.info().labels == ["SCALEUSED"]:
                self.scales = ma

        assert self.intensities is not None
        assert self.batches is not None
        self.mtz_object = reader.file_content()

        crystal_name = (
            filter(
                lambda c: c != "HKL_base",
                map(lambda c: c.name(), self.mtz_object.crystals()),
            )
            or ["DEFAULT"]
        )[0]
        self.report_dir = (
            base_dir
            or xia2.Handlers.Environment.Environment.generate_directory(
                [crystal_name, "report"]
            )
        )

        self.indices = self.mtz_object.extract_original_index_miller_indices()
        self.intensities = self.intensities.customized_copy(
            indices=self.indices, info=self.intensities.info()
        )
        self.batches = self.batches.customized_copy(
            indices=self.indices, info=self.batches.info()
        )

        if len(self.params.batch) == 0:
            from xia2.Modules.MultiCrystalAnalysis import separate_unmerged

            separate = separate_unmerged(self.intensities, self.batches)
            scope = phil.parse(batch_phil_scope)
            for i, batches in separate.batches.iteritems():
                batch_params = scope.extract().batch[0]
                batch_params.id = i
                batch_params.range = (
                    flex.min(batches.data()),
                    flex.max(batches.data()),
                )
                self.params.batch.append(batch_params)

        self._compute_merging_stats()

        if params.anomalous:
            self.intensities = self.intensities.as_anomalous_array()
            self.batches = self.batches.as_anomalous_array()

        self.intensities.setup_binner(n_bins=self.params.resolution_bins)
        self.merged_intensities = self.intensities.merge_equivalents().array()

        if params.include_probability_plots:
            rtable, elist = data_from_unmerged_mtz(unmerged_mtz)
            self.z_score_data = IntensityDist(rtable, elist).rtable


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

    report = xia2_report(unmerged_mtz, params, base_dir=".")

    symmetry_table_html = report.symmetry_table_html()

    # xtriage
    xtriage_success, xtriage_warnings, xtriage_danger = None, None, None
    if params.xtriage_analysis:
        xtriage_success, xtriage_warnings, xtriage_danger = report.xtriage_report()

    json_data = {}

    if params.xtriage_analysis:
        json_data["xtriage"] = xtriage_success + xtriage_warnings + xtriage_danger

    overall_stats_table, merging_stats_table, stats_plots = report.merging_stats_data()

    json_data.update(stats_plots)
    json_data.update(report.batch_dependent_plots())
    json_data.update(report.intensity_stats_plots())
    json_data.update(report.pychef_plots())
    if params.include_probability_plots:
        json_data.update(report.z_score_hist())
        json_data.update(report.normal_probability_plot())
        json_data.update(report.z_vs_multiplicity())
        json_data.update(report.z_time_series())
        json_data.update(report.z_vs_I())
        json_data.update(report.z_vs_I_over_sigma())

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

    if params.include_probability_plots:
        misc_graphs = OrderedDict(
            (k, json_data[k])
            for k in (
                "cumulative_intensity_distribution",
                "l_test",
                "multiplicities",
                "z_score_histogram",
                "normal_probability_plot",
                "z_score_vs_multiplicity",
                "z_score_time_series",
                "z_score_vs_I",
                "z_score_vs_I_over_sigma",
            )
            if k in json_data
        )
    else:
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
        log_text = open(params.log_include).read()
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
        f.write(html.encode("ascii", "xmlcharrefreplace"))


if __name__ == "__main__":
    import sys

    run(sys.argv[1:])
