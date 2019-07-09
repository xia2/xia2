#!/usr/bin/env python
# DialsRefiner.py
#   Copyright (C) 2015 Diamond Light Source, Richard Gildea
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#

from __future__ import absolute_import, division, print_function

import os

from dials.array_family import flex

from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import auto_logfiler
from xia2.Schema.Interfaces.Refiner import Refiner
from xia2.Wrappers.Dials.CombineExperiments import (
    CombineExperiments as _CombineExperiments,
)
from xia2.Wrappers.Dials.Refine import Refine as _Refine
from xia2.Wrappers.Dials.Report import Report as _Report


class DialsRefiner(Refiner):
    def __init__(self):
        super(DialsRefiner, self).__init__()

    # factory functions

    def CombineExperiments(self):
        combiner = _CombineExperiments()
        combiner.set_working_directory(self.get_working_directory())
        auto_logfiler(combiner)
        for idxr in self._refinr_indexers.values():
            combiner.add_experiments(idxr.get_indexer_payload("experiments_filename"))
            combiner.add_reflections(idxr.get_indexed_filename())
        return combiner

    def Refine(self):
        refine = _Refine()
        params = PhilIndex.params.dials.refine
        refine.set_phil_file(params.phil_file)
        refine.set_working_directory(self.get_working_directory())
        if PhilIndex.params.dials.fast_mode:
            # scan-static refinement in fast mode
            refine.set_scan_varying(False)
        else:
            refine.set_scan_varying(params.scan_varying)
        refine.set_reflections_per_degree(params.reflections_per_degree)
        refine.set_interval_width_degrees(params.interval_width_degrees)
        refine.set_outlier_algorithm(PhilIndex.params.dials.outlier.algorithm)
        if PhilIndex.params.dials.fix_geometry:
            refine.set_detector_fix("all")
            refine.set_beam_fix("all")
        refine.set_close_to_spindle_cutoff(
            PhilIndex.params.dials.close_to_spindle_cutoff
        )
        auto_logfiler(refine, "REFINE")

        return refine

    def Report(self):
        report = _Report()
        report.set_working_directory(self.get_working_directory())
        auto_logfiler(report, "REPORT")
        return report

    def _refine_prepare(self):
        pass

    def _refine(self):
        for epoch, idxr in self._refinr_indexers.iteritems():
            experiments = idxr.get_indexer_experiment_list()

            indexed_experiments = idxr.get_indexer_payload("experiments_filename")
            indexed_reflections = idxr.get_indexer_payload("indexed_filename")

            if len(experiments) > 1:
                xsweeps = idxr._indxr_sweeps
                assert len(xsweeps) == len(experiments)
                assert (
                    len(self._refinr_sweeps) == 1
                )  # don't currently support joint refinement
                xsweep = self._refinr_sweeps[0]
                i = xsweeps.index(xsweep)
                experiments = experiments[i : i + 1]

                # Extract and output experiment and reflections for current sweep
                indexed_experiments = os.path.join(
                    self.get_working_directory(), "%s_indexed.expt" % xsweep.get_name()
                )
                indexed_reflections = os.path.join(
                    self.get_working_directory(), "%s_indexed.refl" % xsweep.get_name()
                )

                from dxtbx.serialize import dump

                dump.experiment_list(experiments, indexed_experiments)

                reflections = flex.reflection_table.from_file(
                    idxr.get_indexer_payload("indexed_filename")
                )
                sel = reflections["id"] == i
                assert sel.count(True) > 0
                imageset_id = reflections["imageset_id"].select(sel)
                assert imageset_id.all_eq(imageset_id[0])
                sel = reflections["imageset_id"] == imageset_id[0]
                reflections = reflections.select(sel)
                # set indexed reflections to id == 0 and imageset_id == 0
                reflections["id"].set_selected(reflections["id"] == i, 0)
                reflections["imageset_id"] = flex.int(len(reflections), 0)
                reflections.as_pickle(indexed_reflections)

            assert (
                len(experiments.crystals()) == 1
            )  # currently only handle one lattice/sweep
            crystal_model = experiments.crystals()[0]
            lattice = idxr.get_indexer_lattice()

            from dxtbx.serialize import load

            scan_static = PhilIndex.params.dials.refine.scan_static

            # XXX Temporary workaround for dials.refine error for scan_varying
            # refinement with smaller wedges
            start, end = experiments[0].scan.get_oscillation_range()
            total_phi_range = end - start

            if (
                PhilIndex.params.dials.refine.scan_varying
                and total_phi_range > 5
                and not PhilIndex.params.dials.fast_mode
            ):
                scan_varying = PhilIndex.params.dials.refine.scan_varying
            else:
                scan_varying = False

            if scan_static:
                refiner = self.Refine()
                refiner.set_experiments_filename(indexed_experiments)
                refiner.set_indexed_filename(indexed_reflections)
                refiner.set_scan_varying(False)
                refiner.run()
                self._refinr_experiments_filename = (
                    refiner.get_refined_experiments_filename()
                )
                self._refinr_indexed_filename = refiner.get_refined_filename()
            else:
                self._refinr_experiments_filename = indexed_experiments
                self._refinr_indexed_filename = indexed_reflections

            if scan_varying:
                refiner = self.Refine()
                refiner.set_experiments_filename(self._refinr_experiments_filename)
                refiner.set_indexed_filename(self._refinr_indexed_filename)
                if total_phi_range < 36:
                    refiner.set_interval_width_degrees(total_phi_range / 2)
                refiner.run()
                self._refinr_experiments_filename = (
                    refiner.get_refined_experiments_filename()
                )
                self._refinr_indexed_filename = refiner.get_refined_filename()

            if scan_static or scan_varying:
                FileHandler.record_log_file(
                    "%s REFINE" % idxr.get_indexer_full_name(), refiner.get_log_file()
                )
                report = self.Report()
                report.set_experiments_filename(self._refinr_experiments_filename)
                report.set_reflections_filename(self._refinr_indexed_filename)
                html_filename = os.path.join(
                    self.get_working_directory(),
                    "%i_dials.refine.report.html" % report.get_xpid(),
                )
                report.set_html_filename(html_filename)
                report.run()
                FileHandler.record_html_file(
                    "%s REFINE" % idxr.get_indexer_full_name(), html_filename
                )

            experiments = load.experiment_list(self._refinr_experiments_filename)
            self.set_refiner_payload("models.expt", self._refinr_experiments_filename)
            self.set_refiner_payload("observations.refl", self._refinr_indexed_filename)

            # this is the result of the cell refinement
            self._refinr_cell = experiments.crystals()[0].get_unit_cell().parameters()

    def _refine_finish(self):
        pass
