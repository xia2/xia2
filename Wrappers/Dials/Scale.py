import json
import logging
import os

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex

logger = logging.getLogger("xia2.Wrappers.Dials.Scale")


def DialsScale(DriverType=None, decay_correction=None):
    """A factory for DialsScaleWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)

    class DialsScaleWrapper(DriverInstance.__class__):
        """A wrapper for dials.scale"""

        def __init__(self):
            # generic things
            super().__init__()

            self.set_executable("dials.scale")

            # clear all the header junk
            self.reset()

            self._model = None
            self._full_matrix = True
            self._absorption_correction = True
            self._error_model = "basic"
            self._outlier_rejection = "standard"
            self._outlier_zmax = None
            self._min_partiality = None
            self._partiality_cutoff = None
            self._d_min = None
            self._d_max = None
            self._crystal_name = None
            self._project_name = None
            self._overwrite_existing_models = None

            # scale and filter parameters
            self._filtering_method = None
            self._deltacchalf_max_cycles = None
            self._deltacchalf_min_completeness = None
            self._deltacchalf_stdcutoff = None
            self._scale_and_filter_results = None

            # input and output files
            self._unmerged_reflections = None

            self._experiments_json = []
            self._reflection_files = []

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
            self._spacing = None
            self._cycles = None
            self._brotation = None
            self._bfactor_tie = None
            # self._surface_tie = None
            # self._surface_link = True
            self._lmax = None

            # dose_decay model parameters
            self._share_decay = None
            self._resolution_dependence = None

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
            self._html = None
            self._unmerged_reflections = None
            self._merged_reflections = None
            self._best_unit_cell = None

        # getter and setter methods

        def add_experiments_json(self, experiments_json):
            self._experiments_json.append(experiments_json)

        def add_reflections_file(self, reflections_file):
            self._reflection_files.append(reflections_file)

        def clear_datafiles(self):
            self._experiments_json = []
            self._reflection_files = []
            self._scaled_experiments = []
            self._scaled_reflections = []

        def set_resolution(self, d_min=None, d_max=None):
            """Set the resolution limit for the scaling -
            default is to include all reflections."""

            self._d_min = d_min
            self._d_max = d_max

        def set_bfactor(self, bfactor=True, brotation=None):
            """Switch on/off bfactor refinement, optionally with the
            spacing for the bfactor refinement (in degrees.)"""

            self._bfactor = bfactor

            if brotation:
                self._brotation = brotation

        def set_decay_bins(self, n_bins):
            self._n_resolution_bins = n_bins

        def set_array_absorption_bins(self, n_bins):
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

        def set_share_decay(self, share):
            self._share_decay = share

        def set_resolution_dependence(self, resolution_dependence):
            self._resolution_dependence = resolution_dependence

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

        def set_error_model(self, error_model="basic"):
            self._error_model = error_model

        def set_outlier_rejection(self, outlier_rejection):
            self._outlier_rejection = outlier_rejection

        def set_outlier_zmax(self, z_max):
            self._outlier_zmax = z_max

        def get_scaled_mtz(self):
            return self._merged_reflections

        def set_crystal_name(self, name):
            self._crystal_name = name

        def set_project_name(self, name):
            self._project_name = name

        def get_scaled_reflections(self):
            return self._scaled_reflections

        def get_scaled_experiments(self):
            return self._scaled_experiments

        def set_scaled_mtz(self, filepath):
            self._merged_reflections = filepath

        def set_html(self, filepath):
            self._html = filepath

        def get_html(self):
            return self._html

        def get_scaled_unmerged_mtz(self):
            return self._unmerged_reflections

        def set_scaled_unmerged_mtz(self, filepath):
            self._unmerged_reflections = filepath

        def set_best_unit_cell(self, unit_cell):
            self._best_unit_cell = unit_cell

        def set_overwrite_existing_models(self, overwrite):
            self._overwrite_existing_models = overwrite

        def set_filtering_method(self, filtering_method):
            self._filtering_method = filtering_method

        def set_deltacchalf_max_cycles(self, max_cycles):
            self._deltacchalf_max_cycles = max_cycles

        def set_deltacchalf_min_completeness(self, min_completeness):
            self._deltacchalf_min_completeness = min_completeness

        def set_deltacchalf_stdcutoff(self, stdcutoff):
            self._deltacchalf_stdcutoff = stdcutoff

        def get_scale_and_filter_results(self):
            return self._scale_and_filter_results

        def scale(self):
            """Actually perform the scaling."""

            self.clear_command_line()  # reset the command line in case has already
            # been run previously

            assert len(self._experiments_json)
            assert len(self._reflection_files)
            assert len(self._experiments_json) == len(self._reflection_files)

            for f in self._experiments_json + self._reflection_files:
                assert os.path.isfile(f)
                self.add_command_line(f)

            nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
            if isinstance(nproc, int) and nproc > 1:
                self.add_command_line("nproc=%i" % nproc)

            if self._intensities == "summation":
                self.add_command_line("intensity_choice=sum")
            elif self._intensities == "profile":
                self.add_command_line("intensity_choice=profile")

            # Handle all model options. Model can be none - would trigger auto
            # models in dials.scale.
            if self._model is not None:
                self.add_command_line("model=%s" % self._model)
                # Decay correction can refer to any model (physical, array, KB)
                if self._bfactor:
                    self.add_command_line("%s.decay_correction=True" % self._model)
                else:
                    self.add_command_line("%s.decay_correction=False" % self._model)

            if self._model in ("physical", "dose_decay", "array"):
                # These options can refer to array, physical or dose_decay model
                if self._absorption_correction:
                    self.add_command_line("%s.absorption_correction=True" % self._model)
                else:
                    self.add_command_line(
                        "%s.absorption_correction=False" % self._model
                    )

            if self._model in ("physical", "array"):
                # These options can refer to array, physical or dose_decay model
                if self._bfactor and self._brotation is not None:
                    self.add_command_line(
                        f"{self._model}.decay_interval={self._brotation:g}"
                    )

            if self._model == "dose_decay" and self._share_decay is not None:
                self.add_command_line(f"{self._model}.share.decay={self._share_decay}")

            if self._model == "dose_decay" and self._resolution_dependence is not None:
                self.add_command_line(
                    f"{self._model}.resolution_dependence={self._resolution_dependence}"
                )

            # Option only relevant for spherical harmonic absorption in physical model.
            if (
                self._model in ("physical", "dose_decay")
                and self._absorption_correction
                and self._lmax is not None
            ):
                self.add_command_line("%s.lmax=%i" % (self._model, self._lmax))

            # 'Spacing' i.e. scale interval only relevant to physical model.
            if self._model in ("physical", "dose_decay") and self._spacing:
                self.add_command_line(f"{self._model}.scale_interval={self._spacing:g}")

            self.add_command_line("full_matrix=%s" % self._full_matrix)
            self.add_command_line("error_model=%s" % self._error_model)
            self.add_command_line("outlier_rejection=%s" % self._outlier_rejection)

            if self._min_partiality is not None:
                self.add_command_line("min_partiality=%s" % self._min_partiality)

            if self._partiality_cutoff is not None:
                self.add_command_line("partiality_cutoff=%s" % self._partiality_cutoff)

            # next any 'generic' parameters

            if self._isigma_selection is not None:
                self.add_command_line(
                    "reflection_selection.Isigma_range=%f,%f"
                    % tuple(self._isigma_selection)
                )

            if self._d_min is not None:
                self.add_command_line("cut_data.d_min=%g" % self._d_min)

            if self._d_max is not None:
                self.add_command_line("cut_data.d_max=%g" % self._d_max)

            if self._cycles is not None:
                self.add_command_line("max_iterations=%d" % self._cycles)

            if self._outlier_zmax:
                self.add_command_line("outlier_zmax=%d" % self._outlier_zmax)

            if self._n_resolution_bins:
                self.add_command_line("n_resolution_bins=%d" % self._n_resolution_bins)
            if self._n_absorption_bins:
                self.add_command_line("n_absorption_bins=%d" % self._n_absorption_bins)
            if self._best_unit_cell is not None:
                self.add_command_line(
                    "best_unit_cell=%s,%s,%s,%s,%s,%s" % self._best_unit_cell
                )
            if self._overwrite_existing_models is not None:
                self.add_command_line("overwrite_existing_models=True")

            if not self._scaled_experiments:
                self._scaled_experiments = os.path.join(
                    self.get_working_directory(), "%i_scaled.expt" % self.get_xpid()
                )
            if not self._scaled_reflections:
                self._scaled_reflections = os.path.join(
                    self.get_working_directory(), "%i_scaled.refl" % self.get_xpid()
                )
            if self._unmerged_reflections:
                self.add_command_line(
                    "output.unmerged_mtz=%s" % self._unmerged_reflections
                )

            if self._merged_reflections:
                self.add_command_line("output.merged_mtz=%s" % self._merged_reflections)

            if not self._html:
                self._html = os.path.join(
                    self.get_working_directory(), "%i_scaling.html" % self.get_xpid()
                )
            self.add_command_line("output.html=%s" % self._html)

            if self._crystal_name:
                self.add_command_line("output.crystal_name=%s" % self._crystal_name)

            if self._project_name:
                self.add_command_line("output.project_name=%s" % self._project_name)

            if self._filtering_method:
                self.add_command_line("filtering.method=%s" % self._filtering_method)
                scale_and_filter_filename = (
                    "%s_scale_and_filter_results.json" % self.get_xpid()
                )
                self.add_command_line(
                    "output.scale_and_filter_results=%s" % scale_and_filter_filename
                )
                if self._deltacchalf_max_cycles:
                    self.add_command_line(
                        "filtering.deltacchalf.max_cycles=%i"
                        % self._deltacchalf_max_cycles
                    )
                if self._deltacchalf_min_completeness:
                    self.add_command_line(
                        "filtering.deltacchalf.min_completeness=%i"
                        % self._deltacchalf_min_completeness
                    )
                if self._deltacchalf_stdcutoff:
                    self.add_command_line(
                        "filtering.deltacchalf.stdcutoff=%i"
                        % self._deltacchalf_stdcutoff
                    )

            self.add_command_line("output.experiments=%s" % self._scaled_experiments)
            self.add_command_line("output.reflections=%s" % self._scaled_reflections)

            # run using previously determined scales
            self.start()
            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
            except Exception:
                logger.warning(
                    "dials.scale failed, see log file for more details:\n  %s",
                    self.get_log_file(),
                )
                raise

            logger.debug("dials.scale status: OK")

            if self._filtering_method and os.path.isfile(scale_and_filter_filename):
                with open(scale_and_filter_filename) as fh:
                    from dials.algorithms.scaling import scale_and_filter

                    self._scale_and_filter_results = (
                        scale_and_filter.AnalysisResults.from_dict(json.load(fh))
                    )

            return "OK"

        def get_unmerged_reflection_file(self):
            """Return a single unmerged mtz, for resolution cutoff analysis."""
            return self._unmerged_reflections

    return DialsScaleWrapper()
