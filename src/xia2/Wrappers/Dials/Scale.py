from __future__ import annotations

import json
import logging
import os

from dials.algorithms.scaling import scale_and_filter

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Citations import Citations
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
            self._absorption_level = None  # or low, medium, high
            self._error_model = None
            self._error_model_grouping = None
            self._shared_absorption = False
            self._error_model = None
            self._error_model_grouping = None
            self._error_model_groups = None
            self._outlier_rejection = None
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
            self._deltacchalf_max_percent_removed = None
            self._deltacchalf_mode = None
            self._deltacchalf_group_size = None
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
            self._surface_weight = None
            self._lmax = None

            # dose_decay model parameters
            self._share_decay = None
            self._resolution_dependence = None

            # Array model terms
            self._n_resolution_bins = None
            self._n_absorption_bins = None

            self._isigma_selection = None
            self._reflection_selection_method = None

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

        def set_anomalous(self, anomalous=True):
            """Switch on/off separating of anomalous pairs."""
            self._anomalous = anomalous

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

        def set_surface_weight(self, surface_weight):
            self._surface_weight = surface_weight

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

        def set_shared_absorption(self, share=True):
            self._shared_absorption = share

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

        def set_reflection_selection_method(self, reflection_selection_method):
            self._reflection_selection_method = reflection_selection_method

        def set_error_model(self, error_model="basic"):
            self._error_model = error_model

        def set_error_model_grouping_method(self, grouping="combined"):
            self._error_model_grouping = grouping

        def set_error_model_groups(self, groups):
            "Groups should be a list of groups e.g. ['0,1', '2,3']"
            self._error_model_groups = groups

        def set_outlier_rejection(self, outlier_rejection):
            self._outlier_rejection = outlier_rejection

        def set_outlier_zmax(self, z_max):
            self._outlier_zmax = z_max

        def set_absorption_level(self, level):
            self._absorption_level = level

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

        def set_deltacchalf_max_percent_removed(self, max_percent_removed):
            self._deltacchalf_max_percent_removed = max_percent_removed

        def set_deltacchalf_min_completeness(self, min_completeness):
            self._deltacchalf_min_completeness = min_completeness

        def set_deltacchalf_mode(self, mode):
            self._deltacchalf_mode = mode

        def set_deltacchalf_group_size(self, group_size):
            self._deltacchalf_group_size = group_size

        def set_deltacchalf_stdcutoff(self, stdcutoff):
            self._deltacchalf_stdcutoff = stdcutoff

        def get_scale_and_filter_results(self) -> scale_and_filter.AnalysisResults:
            return self._scale_and_filter_results

        def scale(self):
            """Actually perform the scaling."""
            Citations.cite("dials.scale")
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
                self.add_command_line(f"nproc={nproc}")

            if self._anomalous:
                self.add_command_line("anomalous=True")

            if self._intensities == "summation":
                self.add_command_line("intensity_choice=sum")
            elif self._intensities == "profile":
                self.add_command_line("intensity_choice=profile")

            # Handle all model options. Model can be none - would trigger auto
            # models in dials.scale.
            if self._model is not None:
                self.add_command_line(f"model={self._model}")
                # Decay correction can refer to any model (physical, array, KB)
                if self._bfactor:
                    self.add_command_line(f"{self._model}.decay_correction=True")
                else:
                    self.add_command_line(f"{self._model}.decay_correction=False")

            if self._model in ("physical", "dose_decay", "array"):
                # These options can refer to array, physical or dose_decay model
                if self._absorption_correction:
                    self.add_command_line(f"{self._model}.absorption_correction=True")
                else:
                    self.add_command_line(f"{self._model}.absorption_correction=False")

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
                self.add_command_line(f"{self._model}.lmax={self._lmax}")
            if self._absorption_level:
                self.add_command_line(f"absorption_level={self._absorption_level}")

            # 'Spacing' i.e. scale interval only relevant to physical model.
            if self._model in ("physical", "dose_decay") and self._spacing:
                self.add_command_line(f"{self._model}.scale_interval={self._spacing:g}")
            if self._model == "physical" and self._surface_weight:
                self.add_command_line(
                    f"{self._model}.surface_weight={self._surface_weight}"
                )
            if self._shared_absorption:
                self.add_command_line("share.absorption=True")

            self.add_command_line(f"full_matrix={self._full_matrix}")
            if self._error_model:
                self.add_command_line(f"error_model={self._error_model}")
            if self._error_model_grouping:
                self.add_command_line(
                    f"error_model.grouping={self._error_model_grouping}"
                )
            if self._error_model_groups and self._error_model_grouping == "grouped":
                for g in self._error_model_groups:
                    self.add_command_line(f"error_model_group={g}")
            if self._outlier_rejection:
                self.add_command_line(f"outlier_rejection={self._outlier_rejection}")

            if self._min_partiality is not None:
                self.add_command_line(f"min_partiality={self._min_partiality}")

            if self._partiality_cutoff is not None:
                self.add_command_line(f"partiality_cutoff={self._partiality_cutoff}")

            # next any 'generic' parameters

            if self._isigma_selection is not None:
                self.add_command_line(
                    "reflection_selection.Isigma_range={:f},{:f}".format(
                        *tuple(self._isigma_selection)
                    )
                )

            if self._reflection_selection_method is not None:
                self.add_command_line(
                    f"reflection_selection.method={self._reflection_selection_method}"
                )

            if self._d_min is not None:
                self.add_command_line(f"cut_data.d_min={self._d_min:g}")

            if self._d_max is not None:
                self.add_command_line(f"cut_data.d_max={self._d_max:g}")

            if self._cycles is not None:
                self.add_command_line(f"max_iterations={self._cycles}")

            if self._outlier_zmax:
                self.add_command_line(f"outlier_zmax={self._outlier_zmax}")

            if self._n_resolution_bins:
                self.add_command_line(f"n_resolution_bins={self._n_resolution_bins}")
            if self._n_absorption_bins:
                self.add_command_line(f"n_absorption_bins={self._n_absorption_bins}")
            if self._best_unit_cell is not None:
                self.add_command_line(
                    "best_unit_cell={},{},{},{},{},{}".format(*self._best_unit_cell)
                )
            if self._overwrite_existing_models is not None:
                self.add_command_line("overwrite_existing_models=True")

            if not self._scaled_experiments:
                self._scaled_experiments = os.path.join(
                    self.get_working_directory(), f"{self.get_xpid()}_scaled.expt"
                )
            if not self._scaled_reflections:
                self._scaled_reflections = os.path.join(
                    self.get_working_directory(), f"{self.get_xpid()}_scaled.refl"
                )
            if self._unmerged_reflections:
                self.add_command_line(
                    f"output.unmerged_mtz={self._unmerged_reflections}"
                )

            if self._merged_reflections:
                self.add_command_line(f"output.merged_mtz={self._merged_reflections}")

            if not self._html:
                self._html = os.path.join(
                    self.get_working_directory(), f"{self.get_xpid()}_scaling.html"
                )
            self.add_command_line(f"output.html={self._html}")

            if self._crystal_name:
                self.add_command_line(f"output.crystal_name={self._crystal_name}")

            if self._project_name:
                self.add_command_line(f"output.project_name={self._project_name}")

            if self._filtering_method:
                self.add_command_line(f"filtering.method={self._filtering_method}")
                scale_and_filter_filename = (
                    f"{self.get_xpid()}_scale_and_filter_results.json"
                )
                self.add_command_line(
                    f"output.scale_and_filter_results={scale_and_filter_filename}"
                )
                if self._deltacchalf_max_cycles:
                    self.add_command_line(
                        f"filtering.deltacchalf.max_cycles={self._deltacchalf_max_cycles}"
                    )
                if self._deltacchalf_max_percent_removed:
                    self.add_command_line(
                        f"filtering.deltacchalf.max_percent_removed={self._deltacchalf_max_percent_removed}"
                    )
                if self._deltacchalf_min_completeness:
                    self.add_command_line(
                        f"filtering.deltacchalf.min_completeness={self._deltacchalf_min_completeness}"
                    )
                if self._deltacchalf_mode:
                    self.add_command_line(
                        f"filtering.deltacchalf.mode={self._deltacchalf_mode}"
                    )
                if self._deltacchalf_group_size:
                    self.add_command_line(
                        f"filtering.deltacchalf.group_size={self._deltacchalf_group_size}"
                    )
                if self._deltacchalf_stdcutoff:
                    self.add_command_line(
                        f"filtering.deltacchalf.stdcutoff={self._deltacchalf_stdcutoff}"
                    )

            self.add_command_line(f"output.experiments={self._scaled_experiments}")
            self.add_command_line(f"output.reflections={self._scaled_reflections}")

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
                    self._scale_and_filter_results = (
                        scale_and_filter.AnalysisResults.from_dict(json.load(fh))
                    )

            return "OK"

        def get_unmerged_reflection_file(self):
            """Return a single unmerged mtz, for resolution cutoff analysis."""
            return self._unmerged_reflections

    return DialsScaleWrapper()
