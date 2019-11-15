# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import os
from collections import OrderedDict
from six.moves import cStringIO as StringIO

import xia2.Handlers.Environment
import xia2.Handlers.Files
from cctbx.array_family import flex
import libtbx.phil
from iotbx import merging_statistics
from iotbx.reflection_file_reader import any_reflection_file
from mmtbx.scaling import printed_output

from dials.pychef import dose_phil_str
from dials.report.analysis import batch_dependent_properties
from dials.report.plots import (
    i_over_sig_i_vs_batch_plot,
    scale_rmerge_vs_batch_plot,
    ResolutionPlotsAndStats,
    IntensityStatisticsPlots,
)
from dials.util.batch_handling import batch_manager

from xia2.Modules.Analysis import batch_phil_scope, phil_scope, separate_unmerged


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


class Report(object):
    def __init__(
        self, intensities, params, batches=None, scales=None, dose=None, report_dir=None
    ):

        self.params = params

        self.intensities = intensities
        self.batches = batches
        self.scales = scales
        self.dose = dose
        self.report_dir = report_dir
        self._xanalysis = None

        assert self.intensities is not None
        # assert self.batches is not None

        if self.batches is not None and len(self.params.batch) == 0:
            separate = separate_unmerged(self.intensities, self.batches)
            scope = libtbx.phil.parse(batch_phil_scope)
            for i, batches in separate.batches.iteritems():
                batch_params = scope.extract().batch[0]
                batch_params.id = i
                batch_params.range = (
                    flex.min(batches.data()),
                    flex.max(batches.data()),
                )
                self.params.batch.append(batch_params)

        if self.params.anomalous:
            self.intensities = self.intensities.as_anomalous_array()
            if self.batches is not None:
                self.batches = self.batches.as_anomalous_array()

        self.intensities.setup_binner(n_bins=self.params.resolution_bins)
        self.merged_intensities = self.intensities.merge_equivalents().array()

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
        if self.report_dir is not None:
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

    def resolution_plots_and_stats(self):
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

        is_centric = self.intensities.space_group().is_centric()
        plotter = ResolutionPlotsAndStats(
            self.merging_stats, self.merging_stats_anom, is_centric
        )
        d = OrderedDict()
        d.update(plotter.cc_one_half_plot(method=self.params.cc_half_method))
        d.update(plotter.i_over_sig_i_plot())
        d.update(plotter.completeness_plot())
        d.update(plotter.multiplicity_vs_resolution_plot())
        overall_stats = plotter.overall_statistics_table(self.params.cc_half_method)
        merging_stats = plotter.merging_statistics_table(self.params.cc_half_method)
        return overall_stats, merging_stats, d

    def intensity_stats_plots(self, run_xtriage=True):
        plotter = IntensityStatisticsPlots(
            self.intensities,
            anomalous=self.params.anomalous,
            n_resolution_bins=self.params.resolution_bins,
            xtriage_analyses=self._xanalysis,
            run_xtriage_analysis=run_xtriage,
        )
        d = {}
        d.update(plotter.generate_resolution_dependent_plots())
        d.update(plotter.generate_miscellanous_plots())
        return d

    def pychef_plots(self, n_bins=8):

        import dials.pychef

        intensities = self.intensities
        batches = self.batches
        dose = self.dose

        if self.params.chef_min_completeness:
            d_min = dials.pychef.resolution_limit(
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
            dose = dials.pychef.batches_to_dose(batches.data(), self.params.dose)
        else:
            dose = dose.data()
        pychef_stats = dials.pychef.Statistics(intensities, dose, n_bins=n_bins)

        return pychef_stats.to_dict()

    @classmethod
    def from_unmerged_mtz(cls, unmerged_mtz, params, report_dir=None):
        reader = any_reflection_file(unmerged_mtz)
        assert reader.file_type() == "ccp4_mtz"
        arrays = reader.as_miller_arrays(merge_equivalents=False)

        for ma in arrays:
            if ma.info().labels == ["BATCH"]:
                batches = ma
            elif ma.info().labels == ["I", "SIGI"]:
                intensities = ma
            elif ma.info().labels == ["I(+)", "SIGI(+)", "I(-)", "SIGI(-)"]:
                intensities = ma
            elif ma.info().labels == ["SCALEUSED"]:
                scales = ma

        assert intensities is not None
        assert batches is not None
        mtz_object = reader.file_content()

        crystal_name = (
            filter(
                lambda c: c != "HKL_base",
                map(lambda c: c.name(), mtz_object.crystals()),
            )
            or ["DEFAULT"]
        )[0]
        report_dir = (
            report_dir
            or xia2.Handlers.Environment.Environment.generate_directory(
                [crystal_name, "report"]
            )
        )

        indices = mtz_object.extract_original_index_miller_indices()
        intensities = intensities.customized_copy(
            indices=indices, info=intensities.info()
        )
        batches = batches.customized_copy(indices=indices, info=batches.info())
        report = cls(
            intensities, params, batches=batches, scales=scales, report_dir=report_dir
        )
        report.mtz_object = mtz_object  # nasty but xia2.report relys on this attribute
        return report

    @classmethod
    def from_data_manager(cls, data_manager, params=None):
        if params is None:
            params = phil_scope.extract()
            params.dose.batch = []
        intensities, batches, scales = data_manager.reflections_as_miller_arrays(
            combined=True
        )

        params.batch = []
        scope = libtbx.phil.parse(batch_phil_scope)
        dose_phil = libtbx.phil.parse(dose_phil_str).extract()
        for expt in data_manager.experiments:
            batch_params = scope.extract().batch[0]
            batch_params.id = expt.identifier
            batch_params.range = expt.scan.get_batch_range()
            params.batch.append(batch_params)
            dose_batch = copy.deepcopy(dose_phil.dose.batch[0])
            dose_batch.range = expt.scan.get_batch_range()
            dose_batch.dose_start = 1
            dose_batch.dose_step = 1
            params.dose.batch.append(dose_batch)

        intensities.set_observation_type_xray_intensity()
        return cls(intensities, params, batches=batches, scales=scales)
