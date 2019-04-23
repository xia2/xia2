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


class batch_manager(object):
    def __init__(self, batches, batch_params):
        self.batch_params = batch_params
        self.batch_params.sort(key=lambda b: b.range[0])
        self.batches = batches
        self.reduced_batches, self._batch_increments = self._reduce()

    def _reduce(self):
        reduced_batches = flex.int(self.batches)
        batch_increments = []
        incr = 0
        for batch in self.batch_params:
            sel = (reduced_batches >= batch.range[0]) & (
                reduced_batches <= batch.range[1]
            )
            reduced_batches.set_selected(
                sel, reduced_batches.select(sel) - (batch.range[0] - incr) + 1
            )
            batch_increments.append(incr)
            incr += batch.range[1] - batch.range[0] + 1
        assert len(set(reduced_batches)) == len(reduced_batches)
        return list(reduced_batches), batch_increments

    def batch_plot_shapes_and_annotations(self):
        light_grey = "#d3d3d3"
        grey = "#808080"
        shapes = []
        annotations = []
        batches = flex.int(self.batches)
        text = flex.std_string(batches.size())
        for i, batch in enumerate(self.batch_params):
            fillcolor = [light_grey, grey][i % 2]  # alternate colours
            shapes.append(
                {
                    "type": "rect",
                    # x-reference is assigned to the x-values
                    "xref": "x",
                    # y-reference is assigned to the plot paper [0,1]
                    "yref": "paper",
                    "x0": self._batch_increments[i],
                    "y0": 0,
                    "x1": self._batch_increments[i] + (batch.range[1] - batch.range[0]),
                    "y1": 1,
                    "fillcolor": fillcolor,
                    "opacity": 0.2,
                    "line": {"width": 0},
                }
            )
            annotations.append(
                {
                    # x-reference is assigned to the x-values
                    "xref": "x",
                    # y-reference is assigned to the plot paper [0,1]
                    "yref": "paper",
                    "x": self._batch_increments[i]
                    + (batch.range[1] - batch.range[0]) / 2,
                    "y": 1,
                    "text": "%s" % batch.id,
                    "showarrow": False,
                    "yshift": 20,
                    #'arrowhead': 7,
                    #'ax': 0,
                    #'ay': -40
                }
            )
            sel = (batches >= batch.range[0]) & (batches <= batch.range[1])
            text.set_selected(
                sel,
                flex.std_string(
                    [
                        "%s: %s" % (batch.id, j - batch.range[0] + 1)
                        for j in batches.select(sel)
                    ]
                ),
            )
        return shapes, annotations, list(text)


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

        self.d_star_sq_bins = [
            (1 / bin_stats.d_min ** 2) for bin_stats in self.merging_stats.bins
        ]
        self.d_star_sq_tickvals, self.d_star_sq_ticktext = d_star_sq_to_d_ticks(
            self.d_star_sq_bins, nticks=5
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

    def merging_statistics_table(self):

        headers = [
            u"Resolution (Å)",
            "N(obs)",
            "N(unique)",
            "Multiplicity",
            "Completeness",
            "Mean(I)",
            "Mean(I/sigma)",
            "Rmerge",
            "Rmeas",
            "Rpim",
            "CC1/2",
        ]
        if not self.intensities.space_group().is_centric():
            headers.append("CCano")
        rows = []

        def safe_format(format_str, item):
            return format_str % item if item is not None else ""

        for bin_stats in self.merging_stats.bins:
            row = [
                "%.2f - %.2f" % (bin_stats.d_max, bin_stats.d_min),
                bin_stats.n_obs,
                bin_stats.n_uniq,
                "%.2f" % bin_stats.mean_redundancy,
                "%.2f" % (100 * bin_stats.completeness),
                "%.1f" % bin_stats.i_mean,
                "%.1f" % bin_stats.i_over_sigma_mean,
                safe_format("%.3f", bin_stats.r_merge),
                safe_format("%.3f", bin_stats.r_meas),
                safe_format("%.3f", bin_stats.r_pim),
            ]
            if self.params.cc_half_method == "sigma_tau":
                row.append(
                    "%.3f%s"
                    % (
                        bin_stats.cc_one_half_sigma_tau,
                        "*" if bin_stats.cc_one_half_sigma_tau_significance else "",
                    )
                )
            else:
                row.append(
                    "%.3f%s"
                    % (
                        bin_stats.cc_one_half,
                        "*" if bin_stats.cc_one_half_significance else "",
                    )
                )

            if not self.intensities.space_group().is_centric():
                row.append(
                    "%.3f%s"
                    % (bin_stats.cc_anom, "*" if bin_stats.cc_anom_significance else "")
                )
            rows.append(row)

        merging_stats_table = [headers]
        merging_stats_table.extend(rows)

        return merging_stats_table

    def overall_statistics_table(self):

        headers = ["", "Overall", "Low resolution", "High resolution"]

        stats = (
            self.merging_stats.overall,
            self.merging_stats.bins[0],
            self.merging_stats.bins[-1],
        )

        rows = [
            [u"Resolution (Å)"] + ["%.2f - %.2f" % (s.d_max, s.d_min) for s in stats],
            ["Observations"] + ["%i" % s.n_obs for s in stats],
            ["Unique reflections"] + ["%i" % s.n_uniq for s in stats],
            ["Multiplicity"] + ["%.1f" % s.mean_redundancy for s in stats],
            ["Completeness"] + ["%.2f%%" % (s.completeness * 100) for s in stats],
            # ['Mean intensity'] + ['%.1f' %s.i_mean for s in stats],
            ["Mean I/sigma(I)"] + ["%.1f" % s.i_over_sigma_mean for s in stats],
            ["Rmerge"] + ["%.3f" % s.r_merge for s in stats],
            ["Rmeas"] + ["%.3f" % s.r_meas for s in stats],
            ["Rpim"] + ["%.3f" % s.r_pim for s in stats],
        ]

        if self.params.cc_half_method == "sigma_tau":
            rows.append(["CC1/2"] + ["%.3f" % s.cc_one_half_sigma_tau for s in stats])
        else:
            rows.append(["CC1/2"] + ["%.3f" % s.cc_one_half for s in stats])
        rows = [[u"<strong>%s</strong>" % r[0]] + r[1:] for r in rows]

        overall_stats_table = [headers]
        overall_stats_table.extend(rows)

        return overall_stats_table

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

    def i_over_sig_i_plot(self):

        i_over_sig_i_bins = [
            bin_stats.i_over_sigma_mean for bin_stats in self.merging_stats.bins
        ]

        return {
            "i_over_sig_i": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,  # d_star_sq
                        "y": i_over_sig_i_bins,
                        "type": "scatter",
                        "name": "I/sigI vs resolution",
                    }
                ],
                "layout": {
                    "title": "<I/sig(I)> vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {"title": "<I/sig(I)>", "rangemode": "tozero"},
                },
            }
        }

    def i_over_sig_i_vs_batch_plot(self):

        result = i_sig_i_vs_batch(self.intensities, self.batches)
        bm = batch_manager(result.batches, self.params.batch)
        reduced_batches = bm.reduced_batches
        shapes, annotations, text = bm.batch_plot_shapes_and_annotations()
        if len(annotations) > 30:
            # at a certain point the annotations become unreadable
            annotations = None

        return {
            "i_over_sig_i_vs_batch": {
                "data": [
                    {
                        "x": reduced_batches,
                        "y": result.data,
                        "type": "scatter",
                        "name": "I/sigI vs batch",
                        "opacity": 0.75,
                    }
                ],
                "layout": {
                    "title": "<I/sig(I)> vs batch",
                    "xaxis": {"title": "N"},
                    "yaxis": {"title": "<I/sig(I)>", "rangemode": "tozero"},
                    "shapes": shapes,
                    "annotations": annotations,
                },
            }
        }

    def cc_one_half_plot(self):

        if self.params.cc_half_method == "sigma_tau":
            cc_one_half_bins = [
                bin_stats.cc_one_half_sigma_tau for bin_stats in self.merging_stats.bins
            ]
            cc_one_half_critical_value_bins = [
                bin_stats.cc_one_half_sigma_tau_critical_value
                for bin_stats in self.merging_stats.bins
            ]
        else:
            cc_one_half_bins = [
                bin_stats.cc_one_half for bin_stats in self.merging_stats.bins
            ]
            cc_one_half_critical_value_bins = [
                bin_stats.cc_one_half_critical_value
                for bin_stats in self.merging_stats.bins
            ]
        cc_anom_bins = [bin_stats.cc_anom for bin_stats in self.merging_stats.bins]
        cc_anom_critical_value_bins = [
            bin_stats.cc_anom_critical_value for bin_stats in self.merging_stats.bins
        ]

        return {
            "cc_one_half": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,  # d_star_sq
                        "y": cc_one_half_bins,
                        "type": "scatter",
                        "name": "CC-half",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)"},
                    },
                    {
                        "x": self.d_star_sq_bins,  # d_star_sq
                        "y": cc_one_half_critical_value_bins,
                        "type": "scatter",
                        "name": "CC-half critical value (p=0.01)",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dot"},
                    },
                    (
                        {
                            "x": self.d_star_sq_bins,  # d_star_sq
                            "y": cc_anom_bins,
                            "type": "scatter",
                            "name": "CC-anom",
                            "mode": "lines",
                            "line": {"color": "rgb(255, 127, 14)"},
                        }
                        if not self.intensities.space_group().is_centric()
                        else {}
                    ),
                    (
                        {
                            "x": self.d_star_sq_bins,  # d_star_sq
                            "y": cc_anom_critical_value_bins,
                            "type": "scatter",
                            "name": "CC-anom critical value (p=0.01)",
                            "mode": "lines",
                            "line": {"color": "rgb(255, 127, 14)", "dash": "dot"},
                        }
                        if not self.intensities.space_group().is_centric()
                        else {}
                    ),
                ],
                "layout": {
                    "title": "CC-half vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {
                        "title": "CC-half",
                        "range": [min(cc_one_half_bins + cc_anom_bins + [0]), 1],
                    },
                },
                "help": """\
The correlation coefficients, CC1/2, between random half-datasets. A correlation
coefficient of +1 indicates good correlation, and 0 indicates no correlation.
CC1/2 is typically close to 1 at low resolution, falling off to close to zero at
higher resolution. A typical resolution cutoff based on CC1/2 is around 0.3-0.5.

[1] Karplus, P. A., & Diederichs, K. (2012). Science, 336(6084), 1030-1033.
    https://doi.org/10.1126/science.1218231
[2] Diederichs, K., & Karplus, P. A. (2013). Acta Cryst D, 69(7), 1215-1222.
    https://doi.org/10.1107/S0907444913001121
[3] Evans, P. R., & Murshudov, G. N. (2013). Acta Cryst D, 69(7), 1204-1214.
    https://doi.org/10.1107/S0907444913000061
""",
            }
        }

    def scale_rmerge_vs_batch_plot(self):

        if self.scales is not None:
            sc_vs_b = scales_vs_batch(self.scales, self.batches)
        rmerge_vs_b = rmerge_vs_batch(self.intensities, self.batches)
        bm = batch_manager(rmerge_vs_b.batches, self.params.batch)
        reduced_batches = bm.reduced_batches
        shapes, annotations, text = bm.batch_plot_shapes_and_annotations()
        if len(annotations) > 30:
            # at a certain point the annotations become unreadable
            annotations = None

        return {
            "scale_rmerge_vs_batch": {
                "data": [
                    (
                        {
                            "x": reduced_batches,
                            "y": sc_vs_b.data,
                            "type": "scatter",
                            "name": "Scale",
                            "opacity": 0.75,
                            "text": text,
                        }
                        if self.scales is not None
                        else {}
                    ),
                    {
                        "x": reduced_batches,
                        "y": rmerge_vs_b.data,
                        "yaxis": "y2",
                        "type": "scatter",
                        "name": "Rmerge",
                        "opacity": 0.75,
                        "text": text,
                    },
                ],
                "layout": {
                    "title": "Scale and Rmerge vs batch",
                    "xaxis": {"title": "N"},
                    "yaxis": {"title": "Scale", "rangemode": "tozero"},
                    "yaxis2": {
                        "title": "Rmerge",
                        "overlaying": "y",
                        "side": "right",
                        "rangemode": "tozero",
                    },
                    "shapes": shapes,
                    "annotations": annotations,
                },
            }
        }

    def completeness_plot(self):

        completeness_bins = [
            bin_stats.completeness for bin_stats in self.merging_stats.bins
        ]
        anom_completeness_bins = [
            bin_stats.anom_completeness for bin_stats in self.merging_stats_anom.bins
        ]

        return {
            "completeness": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,
                        "y": completeness_bins,
                        "type": "scatter",
                        "name": "Completeness",
                    },
                    (
                        {
                            "x": self.d_star_sq_bins,
                            "y": anom_completeness_bins,
                            "type": "scatter",
                            "name": "Anomalous completeness",
                        }
                        if not self.intensities.space_group().is_centric()
                        else {}
                    ),
                ],
                "layout": {
                    "title": "Completeness vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {"title": "Completeness", "range": (0, 1)},
                },
            }
        }

    def multiplicity_histogram(self):

        merging = self.intensities.merge_equivalents()
        multiplicities = merging.redundancies().complete_array(new_data_value=0)
        mult_acentric = multiplicities.select_acentric().data()
        mult_centric = multiplicities.select_centric().data()

        multiplicities_acentric = {}
        multiplicities_centric = {}

        for x in sorted(set(mult_acentric)):
            multiplicities_acentric[x] = mult_acentric.count(x)
        for x in sorted(set(mult_centric)):
            multiplicities_centric[x] = mult_centric.count(x)

        return {
            "multiplicities": {
                "data": [
                    {
                        "x": multiplicities_acentric.keys(),
                        "y": multiplicities_acentric.values(),
                        "type": "bar",
                        "name": "Acentric",
                        "opacity": 0.75,
                    },
                    {
                        "x": multiplicities_centric.keys(),
                        "y": multiplicities_centric.values(),
                        "type": "bar",
                        "name": "Centric",
                        "opacity": 0.75,
                    },
                ],
                "layout": {
                    "title": "Distribution of multiplicities",
                    "xaxis": {"title": "Multiplicity"},
                    "yaxis": {
                        "title": "Frequency",
                        #'rangemode': 'tozero'
                    },
                    "bargap": 0,
                    "barmode": "overlay",
                },
            }
        }

    def multiplicity_vs_resolution_plot(self):

        multiplicity_bins = [
            bin_stats.mean_redundancy for bin_stats in self.merging_stats.bins
        ]
        anom_multiplicity_bins = [
            bin_stats.mean_redundancy for bin_stats in self.merging_stats_anom.bins
        ]

        return {
            "multiplicity_vs_resolution": {
                "data": [
                    {
                        "x": self.d_star_sq_bins,
                        "y": multiplicity_bins,
                        "type": "scatter",
                        "name": "Multiplicity",
                    },
                    (
                        {
                            "x": self.d_star_sq_bins,
                            "y": anom_multiplicity_bins,
                            "type": "scatter",
                            "name": "Anomalous multiplicity",
                        }
                        if not self.intensities.space_group().is_centric()
                        else {}
                    ),
                ],
                "layout": {
                    "title": "Multiplicity vs resolution",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": self.d_star_sq_tickvals,
                        "ticktext": self.d_star_sq_ticktext,
                    },
                    "yaxis": {"title": "Multiplicity"},
                },
            }
        }

    def second_moments_plot(self):

        acentric = self.merged_intensities.select_acentric()
        centric = self.merged_intensities.select_centric()
        if acentric.size():
            acentric.setup_binner(n_bins=self.params.resolution_bins)
            second_moments_acentric = acentric.second_moment_of_intensities(
                use_binning=True
            )
        else:
            second_moments_acentric = None
        if centric.size():
            centric.setup_binner(n_bins=self.params.resolution_bins)
            second_moments_centric = centric.second_moment_of_intensities(
                use_binning=True
            )
        else:
            second_moments_centric = None

        second_moment_d_star_sq = []
        if acentric.size():
            second_moment_d_star_sq.extend(
                second_moments_acentric.binner.bin_centers(2)
            )
        if centric.size():
            second_moment_d_star_sq.extend(second_moments_centric.binner.bin_centers(2))
        tickvals_2nd_moment, ticktext_2nd_moment = d_star_sq_to_d_ticks(
            second_moment_d_star_sq, nticks=5
        )

        return {
            "second_moments": {
                "data": [
                    (
                        {
                            "x": list(
                                second_moments_acentric.binner.bin_centers(2)
                            ),  # d_star_sq
                            "y": second_moments_acentric.data[1:-1],
                            "type": "scatter",
                            "name": "<I^2> acentric",
                        }
                        if acentric.size()
                        else {}
                    ),
                    (
                        {
                            "x": list(
                                second_moments_centric.binner.bin_centers(2)
                            ),  # d_star_sq
                            "y": second_moments_centric.data[1:-1],
                            "type": "scatter",
                            "name": "<I^2> centric",
                        }
                        if centric.size()
                        else {}
                    ),
                ],
                "layout": {
                    "title": "Second moment of I",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": tickvals_2nd_moment,
                        "ticktext": ticktext_2nd_moment,
                    },
                    "yaxis": {"title": "<I^2>", "rangemode": "tozero"},
                },
            }
        }

    def cumulative_intensity_distribution_plot(self):
        if not self._xanalysis or not self._xanalysis.twin_results:
            return {}
        nz_test = self._xanalysis.twin_results.nz_test
        return {
            "cumulative_intensity_distribution": {
                "data": [
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.ac_obs),
                        "type": "scatter",
                        "name": "Acentric observed",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)"},
                    },
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.c_obs),
                        "type": "scatter",
                        "name": "Centric observed",
                        "mode": "lines",
                        "line": {"color": "rgb(255, 127, 14)"},
                    },
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.ac_untwinned),
                        "type": "scatter",
                        "name": "Acentric theory",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dot"},
                        "opacity": 0.8,
                    },
                    {
                        "x": list(nz_test.z),
                        "y": list(nz_test.c_untwinned),
                        "type": "scatter",
                        "name": "Centric theory",
                        "mode": "lines",
                        "line": {"color": "rgb(255, 127, 14)", "dash": "dot"},
                        "opacity": 0.8,
                    },
                ],
                "layout": {
                    "title": "Cumulative intensity distribution",
                    "xaxis": {"title": "z", "range": (0, 1)},
                    "yaxis": {"title": "P(Z <= Z)", "range": (0, 1)},
                },
            }
        }

    def l_test_plot(self):
        if not self._xanalysis or not self._xanalysis.twin_results:
            return {}
        l_test = self._xanalysis.twin_results.l_test
        return {
            "l_test": {
                "data": [
                    {
                        "x": list(l_test.l_values),
                        "y": list(l_test.l_cumul_untwinned),
                        "type": "scatter",
                        "name": "Untwinned",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dashdot"},
                    },
                    {
                        "x": list(l_test.l_values),
                        "y": list(l_test.l_cumul_perfect_twin),
                        "type": "scatter",
                        "name": "Perfect twin",
                        "mode": "lines",
                        "line": {"color": "rgb(31, 119, 180)", "dash": "dot"},
                        "opacity": 0.8,
                    },
                    {
                        "x": list(l_test.l_values),
                        "y": list(l_test.l_cumul),
                        "type": "scatter",
                        "name": "Observed",
                        "mode": "lines",
                        "line": {"color": "rgb(255, 127, 14)"},
                    },
                ],
                "layout": {
                    "title": "L test (Padilla and Yeates)",
                    "xaxis": {"title": "|l|", "range": (0, 1)},
                    "yaxis": {"title": "P(L >= l)", "range": (0, 1)},
                },
            }
        }

    def wilson_plot(self):
        if not self._xanalysis or not self._xanalysis.wilson_scaling:
            return {}
        wilson_scaling = self._xanalysis.wilson_scaling
        tickvals_wilson, ticktext_wilson = d_star_sq_to_d_ticks(
            wilson_scaling.d_star_sq, nticks=5
        )

        return {
            "wilson_intensity_plot": {
                "data": (
                    [
                        {
                            "x": list(wilson_scaling.d_star_sq),
                            "y": list(wilson_scaling.mean_I_obs_data),
                            "type": "scatter",
                            "name": "Observed",
                        },
                        {
                            "x": list(wilson_scaling.d_star_sq),
                            "y": list(wilson_scaling.mean_I_obs_theory),
                            "type": "scatter",
                            "name": "Expected",
                        },
                        {
                            "x": list(wilson_scaling.d_star_sq),
                            "y": list(wilson_scaling.mean_I_normalisation),
                            "type": "scatter",
                            "name": "Smoothed",
                        },
                    ]
                ),
                "layout": {
                    "title": "Wilson intensity plot",
                    "xaxis": {
                        "title": u"Resolution (Å)",
                        "tickvals": tickvals_wilson,
                        "ticktext": ticktext_wilson,
                    },
                    "yaxis": {"type": "log", "title": "Mean(I)", "rangemode": "tozero"},
                },
            }
        }

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


def d_star_sq_to_d_ticks(d_star_sq, nticks):
    from cctbx import uctbx

    d_spacings = uctbx.d_star_sq_as_d(flex.double(d_star_sq))
    min_d_star_sq = min(d_star_sq)
    dstep = (max(d_star_sq) - min_d_star_sq) / nticks
    tickvals = list(min_d_star_sq + (i * dstep) for i in range(nticks))
    ticktext = ["%.2f" % (uctbx.d_star_sq_as_d(dsq)) for dsq in tickvals]
    return tickvals, ticktext


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

    overall_stats_table = report.overall_statistics_table()
    merging_stats_table = report.merging_statistics_table()
    symmetry_table_html = report.symmetry_table_html()

    # xtriage
    xtriage_success, xtriage_warnings, xtriage_danger = None, None, None
    if params.xtriage_analysis:
        xtriage_success, xtriage_warnings, xtriage_danger = report.xtriage_report()

    json_data = {}

    if params.xtriage_analysis:
        json_data["xtriage"] = xtriage_success + xtriage_warnings + xtriage_danger

    json_data.update(report.multiplicity_vs_resolution_plot())
    json_data.update(report.multiplicity_histogram())
    json_data.update(report.completeness_plot())
    json_data.update(report.scale_rmerge_vs_batch_plot())
    json_data.update(report.cc_one_half_plot())
    json_data.update(report.i_over_sig_i_plot())
    json_data.update(report.i_over_sig_i_vs_batch_plot())
    json_data.update(report.second_moments_plot())
    json_data.update(report.cumulative_intensity_distribution_plot())
    json_data.update(report.l_test_plot())
    json_data.update(report.wilson_plot())
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
