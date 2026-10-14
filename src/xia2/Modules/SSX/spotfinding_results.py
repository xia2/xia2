"""
Reuse of spotfinding results, to avoid repeating spotfinding on the same images.

Spotfinding results (in pixel coordinates) do not depend on the experimental
geometry, so results from e.g. crystal assessment or geometry refinement can be
reused for the main processing after reimporting with a refined geometry, or
results generated outside of xia2 can be used.

Results are matched to experiments by the underlying image (file path and index
within that file), with the reflection table ids and experiment identifiers
relabelled to match the experiments being processed.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import shutil
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from dials.array_family import flex
from dxtbx import flumpy
from dxtbx.model import ExperimentList
from dxtbx.serialize import load

from xia2.Modules.SSX.data_integration_programs import SpotfindingParams

xia2_logger = logging.getLogger(__name__)

ImageKey = tuple[str, int]

# Marker file written into a batch directory when the strong.refl in that
# directory has been populated from existing spotfinding results.
REUSED_SPOTFINDING_MARKER = "spotfinding_reused"


def image_keys(experiments: ExperimentList) -> list[ImageKey]:
    """
    Identify the image of each single-image experiment, by the file path and
    index within that file.
    """
    keys: list[ImageKey] = []
    n_seen: dict[int, int] = defaultdict(int)  # for imagesets without scans
    one_file_per_image: dict[int, bool] = {}
    for expt in experiments:
        iset = expt.imageset
        if expt.scan and iset.get_scan():
            i = expt.scan.get_image_range()[0] - iset.get_scan().get_image_range()[0]
        else:
            # Stills: experiments are in the same order as the imageset images
            i = n_seen[id(iset)]
            n_seen[id(iset)] += 1
        if id(iset) not in one_file_per_image:
            one_file_per_image[id(iset)] = len(set(iset.paths())) > 1
        # The imageset indices are only indices within the file for a single
        # multi-image file; otherwise they are positions in the list of files.
        index = 0 if one_file_per_image[id(iset)] else int(iset.indices()[i])
        keys.append((os.path.realpath(iset.get_path(i)), index))
    return keys


def spotfinding_signature(
    spotfinding_params: SpotfindingParams,
    mask: pathlib.Path | None,
    import_phil: pathlib.Path | None,
) -> dict:
    """The options affecting spotfinding results, for checking validity of
    previous results."""
    return {
        "min_spot_size": spotfinding_params.min_spot_size,
        "max_spot_size": spotfinding_params.max_spot_size,
        "d_min": spotfinding_params.d_min,
        "d_max": spotfinding_params.d_max,
        "phil": spotfinding_params.phil.read_text()
        if spotfinding_params.phil
        else None,
        "mask": os.fspath(mask) if mask else None,
        "import_phil": os.fspath(import_phil) if import_phil else None,
    }


@dataclass(frozen=True)
class SpotfindingSource:
    experiments: pathlib.Path
    reflections: pathlib.Path | None  # None if no spots found on any image


class SpotfindingResults:
    """
    A collection of spotfinding results, indexed by image.

    Results from spotfinding run during processing are saved in a directory,
    along with the options used, and are discarded if the options change.
    External results (DIALS format experiments and strong reflections) can
    also be provided, which are used without checking the options.
    """

    def __init__(
        self,
        directory: pathlib.Path | None,
        signature: dict,
        external: list[SpotfindingSource] | None = None,
    ):
        self.directory = directory
        self._sources: list[SpotfindingSource] = []
        self._index: dict[ImageKey, tuple[int, int]] = {}
        self._loaded: tuple[pathlib.Path, flex.reflection_table] | None = None
        for source in external or []:
            n = self._add_to_index(source)
            xia2_logger.info(
                f"Using external spotfinding results for {n} images from {source.reflections}"
            )
        if directory:
            self._load_saved(signature)

    def _load_saved(self, signature: dict) -> None:
        assert self.directory
        params_file = self.directory / "spotfinding_params.json"
        if params_file.is_file():
            with params_file.open() as f:
                previous = json.load(f)
            if previous != signature:
                xia2_logger.info(
                    "Spotfinding options have changed, previous spotfinding results will not be reused"
                )
                shutil.rmtree(self.directory)
        if not self.directory.is_dir():
            self.directory.mkdir()
            with params_file.open("w") as f:
                json.dump(signature, f, indent=2)
        for expt_file in self.directory.glob("results_*.expt"):
            refl_file = expt_file.with_suffix(".refl")
            self._add_to_index(
                SpotfindingSource(expt_file, refl_file if refl_file.is_file() else None)
            )

    def _add_to_index(self, source: SpotfindingSource) -> int:
        experiments = load.experiment_list(source.experiments, check_format=False)
        n = len(self._sources)
        self._sources.append(source)
        for i, key in enumerate(image_keys(experiments)):
            self._index[key] = (n, i)
        return len(experiments)

    def _load_reflections(self, path: pathlib.Path) -> flex.reflection_table:
        # Consecutive lookups are usually for the same source, so keep the last one.
        if not self._loaded or self._loaded[0] != path:
            table = flex.reflection_table.from_file(path)
            if "xyzobs.px.value" not in table or "id" not in table:
                raise ValueError(
                    f"Spotfinding results in {path} must contain xyzobs.px.value and id columns"
                )
            self._loaded = (path, table)
        return self._loaded[1]

    def add(
        self,
        experiments_file: pathlib.Path,
        reflections: flex.reflection_table | None,
    ) -> None:
        """Save the spotfinding results for the experiments, for future reuse."""
        if not self.directory:
            return
        name = f"results_{len(list(self.directory.glob('results_*.expt'))) + 1}"
        refl_file = None
        if reflections:
            refl_file = self.directory / f"{name}.refl"
            reflections.as_file(refl_file)
        # Save the experiments last, as these mark the results as complete.
        expt_file = self.directory / f"{name}.expt"
        shutil.copy(experiments_file, expt_file)
        self._add_to_index(SpotfindingSource(expt_file, refl_file))

    def get(
        self, experiments: ExperimentList
    ) -> tuple[bool, flex.reflection_table | None]:
        """
        Get the spotfinding results for all images of the experiments.

        Returns (False, None) if there are not existing results for every image.
        Otherwise returns (True, reflections), with the reflections labelled
        to match the experiments, or None if no spots were found.
        """
        try:
            locations = [self._index[key] for key in image_keys(experiments)]
        except KeyError:
            return (False, None)

        new_ids_by_source: dict[int, dict[int, int]] = defaultdict(dict)
        for new_id, (source, old_id) in enumerate(locations):
            new_ids_by_source[source][old_id] = new_id

        reflections = flex.reflection_table()
        for source, id_map in new_ids_by_source.items():
            refl_file = self._sources[source].reflections
            if not refl_file:
                continue
            table = self._load_reflections(refl_file)
            ids = flumpy.to_numpy(table["id"])
            old_ids = np.array(list(id_map.keys()))
            sel = np.isin(ids, old_ids)
            if not sel.any():
                continue
            table = table.select(flumpy.from_numpy(sel))
            id_lookup = np.full(max(ids.max(), old_ids.max()) + 1, -1, dtype=np.int32)
            id_lookup[old_ids] = np.array(list(id_map.values()))
            table["id"] = flumpy.from_numpy(id_lookup[ids[sel]])
            for k in list(table.experiment_identifiers().keys()):
                del table.experiment_identifiers()[k]
            reflections.extend(table)

        if not reflections:
            return (True, None)
        if "imageset_id" in reflections:
            # Would refer to the imagesets of the source experiments.
            del reflections["imageset_id"]
        if "panel" not in reflections:
            if any(len(d) > 1 for d in experiments.detectors()):
                raise ValueError(
                    "Spotfinding results must contain a panel column for multi-panel detectors"
                )
            reflections["panel"] = flex.size_t(reflections.size(), 0)
        for i, expt in enumerate(experiments):
            reflections.experiment_identifiers()[i] = expt.identifier
        reflections.sort("id")
        return (True, reflections)


def populate_batches_from_existing_results(
    batch_directories: list[pathlib.Path],
    spotfinding_results: SpotfindingResults,
) -> None:
    """
    Write existing spotfinding results into each batch directory that is fully
    covered by them, marking the directory so that spotfinding is not rerun.
    """
    n_reused = 0
    for directory in batch_directories:
        marker = directory / REUSED_SPOTFINDING_MARKER
        marker.unlink(missing_ok=True)
        experiments = load.experiment_list(
            directory / "imported.expt", check_format=False
        )
        found, strong = spotfinding_results.get(experiments)
        if not found:
            continue
        if strong:
            strong.as_file(directory / "strong.refl")
        else:
            (directory / "strong.refl").unlink(missing_ok=True)
        marker.touch()
        n_reused += 1
    if n_reused:
        xia2_logger.info(
            f"Using existing spotfinding results for {n_reused} of {len(batch_directories)} batches"
        )
