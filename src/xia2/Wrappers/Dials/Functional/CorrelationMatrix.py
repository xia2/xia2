from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any, List

import libtbx.phil
from dials.algorithms.correlation.analysis import CorrelationMatrix
from dials.algorithms.correlation.cluster import ClusterInfo
from dials.array_family import flex
from dials.command_line.correlation_matrix import phil_scope
from dxtbx.model import ExperimentList

from xia2.Driver.timing import record_step
from xia2.Handlers.Citations import Citations
from xia2.lib.bits import _get_number
from xia2.Modules.SSX.util import log_to_file, run_in_directory
from xia2.Wrappers.Dials.Functional import diff_phil_from_params_and_scope, handle_fail

xia2_logger = logging.getLogger(__name__)


class DialsCorrelationMatrix:
    def __init__(self, working_directory: Path | None = None) -> None:
        if working_directory:
            self._working_directory = working_directory
        else:
            self._working_directory = Path.cwd()

        self._params: libtbx.phil.scope_extract = phil_scope.extract()

        # Set defaults
        self._ids_to_identifiers_map = None
        self._use_xpid = True
        self._params.output.json = "dials.correlation_matrix.json"

        # Initial Properties
        self._correlation_clusters: list[ClusterInfo] = []
        self._cos_angle_clusters: List[ClusterInfo] = []
        self._significant_clusters: List[ClusterInfo] = []
        self._cc_json: dict[str, Any] = {}
        self._cos_json: dict[str, Any] = {}
        self._cc_table: list[list[str]] = []
        self._cos_table: list[list[str]] = []
        self._rij_graphs: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._pca_plot: dict[str, Any] = {}

    def set_buffer(self, buffer: float) -> None:
        self._params.significant_clusters.min_points_buffer = buffer

    def set_xi(self, xi: float) -> None:
        self._params.significant_clusters.xi = xi

    def set_output_json(self, json: str) -> None:
        self._params.output.json = json

    @property
    def ids_to_identifiers_map(self) -> dict | None:
        return self._ids_to_identifiers_map

    @ids_to_identifiers_map.setter
    def ids_to_identifiers_map(self, ids_to_identifiers) -> None:
        self._ids_to_identifiers_map = ids_to_identifiers

    @property
    def correlation_clusters(self) -> list[ClusterInfo]:
        return self._correlation_clusters

    @property
    def cos_angle_clusters(self) -> list[ClusterInfo]:
        return self._cos_angle_clusters

    @property
    def significant_clusters(self) -> list[ClusterInfo]:
        return self._significant_clusters

    @property
    def cc_json(self) -> dict[str, Any]:
        return self._cc_json

    @property
    def cos_json(self) -> dict[str, Any]:
        return self._cos_json

    @property
    def cc_table(self) -> list[list[str]]:
        return self._cc_table

    @property
    def cos_table(self) -> list[list[str]]:
        return self._cos_table

    @property
    def rij_graphs(self) -> OrderedDict[str, dict[str, Any]]:
        return self._rij_graphs

    @property
    def pca_plot(self) -> dict[str, Any]:
        return self._pca_plot

    @property
    def use_xpid(self) -> bool:
        return self._use_xpid

    @use_xpid.setter
    def use_xpid(self, xpid: bool) -> None:
        self._use_xpid = xpid

    @handle_fail
    def run(self, expts: ExperimentList, refls: list[flex.reflection_table]) -> None:
        xia2_logger.debug("Running dials.correlation_matrix")
        Citations.cite("dials.correlation_matrix")
        if self._use_xpid:
            self._xpid = _get_number()
            logfile = f"{self._xpid}_dials.correlation_matrix.log"
        else:
            logfile = "dials.correlation_matrix.log"
        with (
            run_in_directory(self._working_directory),
            log_to_file(logfile) as dials_logger,
            record_step("dials.correlation_matrix"),
        ):
            dials_logger.info(diff_phil_from_params_and_scope(self._params, phil_scope))
            matrices = CorrelationMatrix(
                expts,
                refls,
                self._params,
                self._ids_to_identifiers_map,
            )
            matrices.calculate_matrices()
            matrices.convert_to_html_json()
            matrices.output_json()

            self._correlation_clusters = matrices.correlation_clusters
            self._cos_angle_clusters = matrices.cos_angle_clusters
            self._significant_clusters = matrices.significant_clusters
            self._cc_json = matrices.cc_json
            self._cos_json = matrices.cos_json
            self._cc_table = matrices.cc_table
            self._cos_table = matrices.cos_table
            self._rij_graphs = matrices.rij_graphs
            self._pca_plot = matrices.pca_plot
