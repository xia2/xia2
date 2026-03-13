from __future__ import annotations

import json
import logging
from collections import OrderedDict

from dials.algorithms.scaling.scaling_library import determine_best_unit_cell
from dials.array_family import flex
from dials.util.export_mtz import match_wavelengths

from xia2.Driver.timing import record_step
from xia2.Modules.MultiCrystal.data_manager import DataManager
from xia2.Modules.MultiCrystal.ScaleAndMerge import MultiCrystalScale
from xia2.XIA2Version import Version

logger = logging.getLogger(__name__)


class FilterExistingMultiplex:
    def __init__(self, expts, refls, params):
        self.data_manager = DataManager(expts, refls)
        d_spacings: flex.double = self.data_manager._reflections["d"]
        self.params = params
        self.params.r_free_flags.d_min = flex.min(d_spacings.select(d_spacings > 0))
        self.params.r_free_flags.d_max = flex.max(d_spacings)
        self.wavelengths = match_wavelengths(
            self.data_manager.experiments, params.wavelength_tolerance
        )
        self.free_flags_in_full_set = True

    def filter_and_record(self):
        _, _, filtered, self.data_manager = MultiCrystalScale.filter(
            self.data_manager,
            self.params,
            self.free_flags_in_full_set,
            self.wavelengths,
        )
        with record_step("xia2.report(filtered)"):
            individual_report_dicts = OrderedDict()
            d = MultiCrystalScale._report_as_dict(
                filtered.report(), len(self.data_manager._experiments)
            )
            individual_report_dicts["Filtered"] = (
                MultiCrystalScale._individual_report_dict(d, "Filtered")
            )
            MultiCrystalScale._log_report_info(d)

        if self.params.multiplex_json:
            with open(self.params.multiplex_json, "r") as f:
                parent_data = json.load(f)

            for i in parent_data["datasets"]:
                if "Filtered" not in i:
                    individual_report_dicts[i] = parent_data["datasets"][i]

        from jinja2 import ChoiceLoader, Environment, PackageLoader

        space_group = (
            self.data_manager.experiments[0]
            .crystal.get_space_group()
            .info()
            .symbol_and_number()
        )
        unit_cell = determine_best_unit_cell(self.data_manager.experiments)
        image_range_table = individual_report_dicts["Filtered"]["image_range_table"]
        styles = {}

        loader = ChoiceLoader(
            [PackageLoader("xia2", "templates"), PackageLoader("dials", "templates")]
        )
        env = Environment(loader=loader)
        template = env.get_template("multiplex_filtering.html")
        html = template.render(
            page_title="xia2.multiplex-filtering report",
            space_group=space_group,
            unit_cell=str(unit_cell),
            cc_half_significance_level=self.params.resolution.cc_half_significance_level,
            image_range_tables=[image_range_table],
            individual_dataset_reports=individual_report_dicts,
            styles=styles,
            xia2_version=Version,
        )
        json_data: dict = {}
        json_data["datasets"] = {}
        for report_name, report in individual_report_dicts.items():
            json_data["datasets"][report_name] = {
                k: report[k]
                for k in (
                    "resolution_graphs",
                    "batch_graphs",
                    "xtriage",
                    "merging_stats",
                    "merging_stats_anom",
                    "misc_graphs",
                )
            }

        with open("xia2.multiplex_filtering.json", "w") as f:
            json.dump(json_data, f)

        with open("xia2.multiplex-filtering.html", "wb") as f:
            f.write(html.encode("utf-8", "xmlcharrefreplace"))
