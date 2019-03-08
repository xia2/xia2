#!/usr/bin/env python
# Aimless.py
#   Copyright (C) 2011 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 31st August 2011
#
# A wrapper for the CCP4 program Aimless, for scaling & merging reflections.
# This is a replacement for the more venerable program Scala, and shares the
# same interface as the Scala wrapper. Mostly.

from __future__ import absolute_import, division, print_function

import os

from libtbx import Auto

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug


def DialsScale(DriverType=None, decay_correction=None):
    """A factory for DialsScaleWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsScaleWrapper(DriverInstance.__class__):
        """A wrapper for dials.scale"""

        def __init__(self):
            # generic things
            super(DialsScaleWrapper, self).__init__()

            self.set_executable("dials.scale")

            # clear all the header junk
            self.reset()

            self._model = None
            self._full_matrix = True
            self._absorption_correction = True
            self._optimise_errors = True
            self._outlier_rejection = "standard"
            self._outlier_zmax = None
            self._min_partiality = None
            self._partiality_cutoff = None
            self._dmin = None
            self._dmax = None
            self._crystal_name = None

            # input and output files
            self._unmerged_reflections = None

            self._experiments_json = []
            self._reflections_pickle = []

            # scaling parameters
            self._resolution = None

            # this flag indicates that the input reflections are already
            # scaled and just need merging e.g. from XDS/XSCALE.
            self._onlymerge = False

            # by default, switch this on
            if decay_correction is None:
                self._bfactor = True
            else:
                self._bfactor = decay_correction

            # this will often be wanted
            self._anomalous = False

            # these are only relevant for 'rotation' mode scaling
            self._spacing = 5
            self._cycles = None
            self._brotation = None
            self._bfactor_tie = None
            # self._surface_tie = None
            # self._surface_link = True
            self._lmax = None

            # Array model terms
            self._n_resolution_bins = None
            self._n_absorption_bins = None

            self._isigma_selection = None

            self._intensities = None

            self._project_crystal_dataset = {}
            self._runs = []

            # for adding data on merge - one dname
            self._pname = None
            self._xname = None
            self._dname = None

            self._scaled_experiments = None
            self._scaled_reflections = None
            self._unmerged_reflections = None
            self._merged_reflections = None
            self._best_unit_cell = None

        # getter and setter methods

        def add_experiments_json(self, experiments_json):
            self._experiments_json.append(experiments_json)

        def add_reflections_pickle(self, reflections_pickle):
            self._reflections_pickle.append(reflections_pickle)

        def clear_datafiles(self):
            self._experiments_json = []
            self._reflections_pickle = []
            self._scaled_experiments = []
            self._scaled_reflections = []

        def set_resolution(self, resolution):
            """Set the resolution limit for the scaling -
            default is to include all reflections."""

            self._resolution = resolution

        def set_bfactor(self, bfactor=True, brotation=None):
            """Switch on/off bfactor refinement, optionally with the
            spacing for the bfactor refinement (in degrees.)"""

            self._bfactor = bfactor

            if brotation:
                self._brotation = brotation

        def set_decay_bins(self, n_bins):
            self._n_resolution_bins = n_bins

        def set_absorption_bins(self, n_bins):
            self._n_absorption_bins = n_bins

        def set_min_partiality(self, min_partiality):
            self._min_partiality = min_partiality

        def set_partiality_cutoff(self, v):
            self._partiality_cutoff = v

        # def set_surface_tie(self, surface_tie):
        # self._surface_tie = surface_tie

        # def set_surface_link(self, surface_link):
        # self._surface_link = surface_link

        def set_lmax(self, lmax):
            self._lmax = lmax

        def set_model(self, model):
            self._model = model

        def set_full_matrix(self, full_matrix=True):
            self._full_matrix = full_matrix

        def set_absorption_correction(self, absorption_correction=True):
            self._absorption_correction = absorption_correction

        def set_spacing(self, spacing):
            self._spacing = spacing

        def set_cycles(self, cycles):
            """Set the maximum number of cycles allowed for the scaling -
            this assumes the default convergence parameters."""

            self._cycles = cycles

        def set_intensities(self, intensities):
            intensities = intensities.lower()
            assert intensities in ("summation", "profile", "combine")
            self._intensities = intensities

        def set_isigma_selection(self, isigma_selection):
            assert len(isigma_selection) == 2
            self._isigma_selection = isigma_selection

        def set_optimise_errors(self, optimise_errors=True):
            self._optimise_errors = optimise_errors

        def set_outlier_rejection(self, outlier_rejection):
            self._outlier_rejection = outlier_rejection

        def set_outlier_zmax(self, z_max):
            self._outlier_zmax = z_max

        def get_scaled_mtz(self):
            return self._merged_reflections

        def set_crystal_name(self, name):
            self._crystal_name = name

        def get_scaled_unmerged_mtz(self):
            return self._unmerged_reflections

        def get_scaled_reflections(self):
            return self._scaled_reflections

        def get_scaled_experiments(self):
            return self._scaled_experiments

        def set_scaled_experiments(self, filepath):
            self._scaled_experiments = filepath

        def set_scaled_reflections(self, filepath):
            self._scaled_reflections = filepath

        def set_scaled_mtz(self, filepath):
            self._merged_reflections = filepath

        def set_scaled_unmerged_mtz(self, filepath):
            self._unmerged_reflections = filepath

        def set_best_unit_cell(self, unit_cell):
            self._best_unit_cell = unit_cell

        def scale(self):
            """Actually perform the scaling."""

            self.clear_command_line()  # reset the command line in case has already
            # been run previously

            assert len(self._experiments_json)
            assert len(self._reflections_pickle)
            assert len(self._experiments_json) == len(self._reflections_pickle)

            for f in self._experiments_json + self._reflections_pickle:
                assert os.path.isfile(f)
                self.add_command_line(f)

            nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
            if isinstance(nproc, int) and nproc > 1:
                self.add_command_line("nproc=%i" % nproc)
            # if PhilIndex.params.xia2.settings.small_molecule == False:
            # self.input('bins 20')

            if self._intensities == "summation":
                self.add_command_line("intensity_choice=sum")
            elif self._intensities == "profile":
                self.add_command_line("intensity_choice=profile")

            if self._model is not None:
                self.add_command_line("model=%s" % self._model)
            self.add_command_line("full_matrix=%s" % self._full_matrix)
            self.add_command_line("scale_interval=%g" % self._spacing)
            self.add_command_line("optimise_errors=%s" % self._optimise_errors)
            self.add_command_line("outlier_rejection=%s" % self._outlier_rejection)

            self.add_command_line("absorption_term=%s" % self._absorption_correction)
            if self._absorption_correction and self._lmax is not None:
                self.add_command_line("lmax=%i" % self._lmax)

            if self._min_partiality is not None:
                min_partiality = self._min_partiality

            if self._partiality_cutoff is not None:
                partiality_cutoff = self._partiality_cutoff

            self.add_command_line("decay_term=%s" % self._bfactor)
            if self._bfactor and self._brotation is not None:
                self.add_command_line("decay_interval=%g" % self._brotation)

            # next any 'generic' parameters

            if self._isigma_selection is not None:
                self.add_command_line(
                    "reflection_selection.Isigma_range=%f,%f"
                    % tuple(self._isigma_selection)
                )

            if self._resolution:
                self.add_command_line("cut_data.d_min=%g" % self._resolution)

            if self._cycles is not None:
                self.add_command_line("max_iterations=%d" % self._cycles)

            if self._outlier_zmax:
                self.add_command_line("outlier_zmax=%d" % self._outlier_zmax)

            if self._n_resolution_bins:
                self.add_command_line("n_resolution_bins=%d" % self._n_resolution_bins)
            if self._n_absorption_bins:
                self.add_command_line("n_absorption_bins=%d" % self._n_absorption_bins)
            if self._best_unit_cell is not None:
                self.add_command_line('best_unit_cell=%s,%s,%s,%s,%s,%s' % self._best_unit_cell)

            if not self._scaled_experiments:
                self._scaled_experiments = os.path.join(
                    self.get_working_directory(),
                    "%i_scaled_experiments.json" % self.get_xpid(),
                )
            if not self._scaled_reflections:
                self._scaled_reflections = os.path.join(
                    self.get_working_directory(),
                    "%i_scaled_reflections.pickle" % self.get_xpid(),
                )
            if not self._unmerged_reflections:
                self._unmerged_reflections = os.path.join(
                    self.get_working_directory(),
                    "%i_scaled_unmerged.mtz" % self.get_xpid(),
                )
            if not self._merged_reflections:
                self._merged_reflections = os.path.join(
                    self.get_working_directory(), "%i_scaled.mtz" % self.get_xpid()
                )
            if self._crystal_name:
                self.add_command_line("output.crystal_name=%s" % self._crystal_name)

            self.add_command_line("output.experiments='%s'" % self._scaled_experiments)
            self.add_command_line("output.reflections='%s'" % self._scaled_reflections)

            self.add_command_line(
                "output.unmerged_mtz='%s'" % self._unmerged_reflections
            )
            self.add_command_line("output.merged_mtz='%s'" % self._merged_reflections)

            # run using previously determined scales
            self.start()
            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
            except Exception:
                Chatter.write(
                    "dials.scale failed, see log file for more details:\n  %s"
                    % self.get_log_file()
                )
                raise

            Debug.write("dials.scale status: OK")

            # here get a list of all output files...
            output = self.get_all_output()

            Chatter.write("Completed a round of scaling using dials.scale")
            return "OK"

        def get_scaled_reflection_files(self):
            return self._scalr_scaled_reflection_files

        def get_unmerged_reflection_file(self):
            return self._unmerged_reflections

    return DialsScaleWrapper()


if __name__ == "__main__":
    import sys
    from xia2.lib.bits import auto_logfiler

    args = sys.argv[1:]
    assert len(args) == 2
    s = DialsScale()
    auto_logfiler(s)

    s.add_experiments_json(args[0])
    s.add_reflections_pickle(args[1])
    s.set_full_matrix(False)
    s.set_model("kb")

    s.scale()

    s.write_log_file("scale.log")
