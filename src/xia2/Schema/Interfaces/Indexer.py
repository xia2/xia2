# An interface for programs which perform indexing - this will handle
# all of the aspects of the interface which are common between indexing
# progtrams, and which must be presented in order to satisfy the contract
# for the indexer interface.
#
# The following are considered to be critical for this class:
#
# Images to index - optional this could be decided by the implementation
# Refined beam position
# Refined distance
# Mosaic spread
#
# Input: ?Selected lattice?
# Input: ?Cell?
# Output: Selected lattice
# Output: Unit cell
# Output: Aux information - may include matrix files &c. This is going to
#         be in the "payload" and will be program specific.
#
# Methods:
#
# index() -> delegated to implementation._index()
#
# Notes:
#
# All properties of this class are prefixed with either indxr for protected
# things or Indexer for public things.
#
# Error Conditions:
#
# A couple of conditions will give indexing errors -
# (1) if no solution matching the input was found
# (2) if the images were blank
# (3) if the indexing just failed (bad beam, etc.)
#
# These need to be handled properly with helpful error messages.
#


import inspect
import json
import logging
import os
from functools import reduce

from cctbx.sgtbx import bravais_types
from dxtbx.serialize.load import _decode_dict
from xia2.Experts.LatticeExpert import SortLattices
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import banner

logger = logging.getLogger("xia2.Schema.Interfaces.Indexer")


class _IndexerHelper:
    """
    Manage autoindexing results in a useful way.

    Ensure that the indexing solutions are properly managed, including in the case
    of pseudo-symmetry.
    """

    def __init__(self, lattice_cell_dict):
        """Initialise myself from a dictionary keyed by crystal lattice
        classes (e.g. tP) containing unit cells for these lattices."""

        self._sorted_list = SortLattices(lattice_cell_dict.items())

    def get(self):
        """Get the highest currently allowed lattice."""
        return self._sorted_list[0]

    def get_all(self):
        """Return a list of all allowed lattices, as [(lattice, cell)]."""
        return self._sorted_list

    def repr(self):
        """Return a string representation."""

        return [
            "%s %s" % (l[0], "%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f" % l[1])
            for l in self._sorted_list
        ]

    def insert(self, lattice, cell):
        """Insert a new solution, e.g. from some postprocessing from
        the indexer. N.B. this will be re-sorted."""

        lattices = [(lattice, cell)]

        for l in self._sorted_list:
            lattices.append(l)

        self._sorted_list = SortLattices(lattices)

    def eliminate(self, indxr_print=True):
        """Eliminate the highest currently allowed lattice."""

        if len(self._sorted_list) <= 1:
            raise RuntimeError("cannot eliminate only solution")

        if indxr_print:
            logger.info("Eliminating indexing solution:")
            logger.info(self.repr()[0])

        self._sorted_list = self._sorted_list[1:]


def beam_centre(detector, beam):
    s0 = beam.get_s0()
    x, y = (None, None)
    for panel_id, panel in enumerate(detector):
        try:
            x, y = panel.get_bidirectional_ray_intersection(s0)
        except RuntimeError:
            continue
        else:
            if panel.is_coord_valid_mm((x, y)):
                break

    return panel_id, (x, y)


def beam_centre_raw_image(detector, beam):
    panel_id, (x, y) = beam_centre(detector, beam)
    panel = detector[panel_id]
    x_px, y_px = panel.millimeter_to_pixel((x, y))
    offset = panel.get_raw_image_offset()
    return panel.pixel_to_millimeter((x_px + offset[0], y_px + offset[1]))


class Indexer:
    """A class interface to present autoindexing functionality in a standard
    way for all indexing programs. Note that this interface defines the
    contract - what the implementation actually does is a matter for the
    implementation."""

    LATTICE_POSSIBLE = "LATTICE_POSSIBLE"
    LATTICE_IMPOSSIBLE = "LATTICE_IMPOSSIBLE"
    LATTICE_CORRECT = "LATTICE_CORRECT"

    def __init__(self):

        self._indxr_working_directory = os.getcwd()

        # (optional) input parameters
        self._indxr_input_lattice = None
        self._indxr_input_cell = None
        self._indxr_user_input_lattice = False

        # job management parameters
        self._indxr_done = False
        self._indxr_prepare_done = False
        self._indxr_finish_done = False
        self._indxr_sweep_name = None
        self._indxr_pname = None
        self._indxr_xname = None
        self._indxr_dname = None

        # links to where my data is coming from
        self._indxr_sweeps = []
        self._indxr_imagesets = []

        # the helper to manage the solutions table
        self._indxr_helper = None

        # output items - best solution
        self._indxr_lattice = None
        self._indxr_cell = None

        # a place to store other plausible solutions - used
        # for populating the helper in the main index() method
        self._indxr_other_lattice_cell = {}

        # refined experimental parameters
        self._indxr_mosaic = None
        self._indxr_refined_beam_centre = None
        self._indxr_refined_distance = None
        self._indxr_resolution_estimate = 0.0
        self._indxr_low_resolution = 0.0

        # refined dxtbx experimental objects
        # XXX here we would be better storing a dials experiment object
        self._indxr_refined_beam = None
        self._indxr_refined_detector = None
        self._indxr_refined_goniometer = None
        self._indxr_refined_scan = None

        self._indxr_experiment_list = None

        # spot list in an as yet to be defined standard reference frame
        self._indxr_spot_list = None

        # error information
        self._indxr_error = None

        # extra indexing guff - a dictionary which the implementation
        # can store things in
        self._indxr_payload = {}

        self._indxr_print = True

        self.LATTICE_CORRECT = Indexer.LATTICE_CORRECT
        self.LATTICE_POSSIBLE = Indexer.LATTICE_POSSIBLE
        self.LATTICE_IMPOSSIBLE = Indexer.LATTICE_IMPOSSIBLE

    # admin functions

    def set_working_directory(self, working_directory):
        self._indxr_working_directory = working_directory

    def get_working_directory(self):
        return self._indxr_working_directory

    # serialization functions

    def to_dict(self):
        obj = {}
        obj["__id__"] = "Indexer"
        obj["__module__"] = self.__class__.__module__
        obj["__name__"] = self.__class__.__name__

        attributes = inspect.getmembers(self, lambda m: not inspect.isroutine(m))
        for a in attributes:
            if a[0] == "_indxr_helper" and a[1] is not None:
                lattice_cell_dict = {}
                lattice_list = a[1].get_all()
                for l, c in lattice_list:
                    lattice_cell_dict[l] = c
                obj[a[0]] = lattice_cell_dict
            elif a[0] == "_indxr_experiment_list" and a[1] is not None:
                obj[a[0]] = a[1].to_dict()
            elif a[0] == "_indxr_imagesets":
                from dxtbx.serialize.imageset import imageset_to_dict

                obj[a[0]] = [imageset_to_dict(imgset) for imgset in a[1]]
            elif a[0] == "_indxr_sweeps":
                # XXX I guess we probably want this?
                continue
            elif a[0].startswith("_indxr_") or a[0].startswith("_fp_"):
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "Indexer"
        assert obj["__name__"] == cls.__name__
        return_obj = cls()
        for k, v in obj.items():
            if k == "_indxr_helper" and v is not None:
                v = _IndexerHelper(v)
            if k == "_indxr_imagesets" and len(v):
                assert v[0].get("__id__") == "imageset"
                from dxtbx.serialize.imageset import imageset_from_dict

                v = [imageset_from_dict(v_, check_format=False) for v_ in v]
            if isinstance(v, dict):
                if v.get("__id__") == "ExperimentList":
                    from dxtbx.model.experiment_list import ExperimentListFactory

                    v = ExperimentListFactory.from_dict(v, check_format=False)
            setattr(return_obj, k, v)
        return return_obj

    def as_json(self, filename=None, compact=False):
        obj = self.to_dict()
        if compact:
            text = json.dumps(
                obj, skipkeys=True, separators=(",", ":"), ensure_ascii=True
            )
        else:
            text = json.dumps(obj, skipkeys=True, indent=2, ensure_ascii=True)

        # If a filename is set then dump to file otherwise return string
        if filename is not None:
            with open(filename, "w") as outfile:
                outfile.write(text)
        else:
            return text

    @classmethod
    def from_json(cls, filename=None, string=None):
        assert [filename, string].count(None) == 1
        if filename is not None:
            with open(filename, "rb") as f:
                string = f.read()
        obj = json.loads(string, object_hook=_decode_dict)
        return cls.from_dict(obj)

    # ----------------------------------------------------------------
    # These are functions which will want to be overloaded for the
    # actual implementation - preparation may do things like gathering
    # spots on the images, index to perform the actual autoindexing
    # and then finish to do any finishing up you want... see the
    # method index() below for how these are used
    # ----------------------------------------------------------------

    def _index_prepare(self):
        """Prepare to index, e.g. finding spots on the images."""
        raise NotImplementedError("overload me")

    def _index(self):
        """Actually perform the autoindexing calculations."""
        raise NotImplementedError("overload me")

    def _index_finish(self):
        """This may be a no-op if you have no use for it..."""
        pass

    # setters and getters of the status of the tasks - note that
    # these will cascade, so setting an early task not done will
    # set later tasks not done.

    def set_indexer_prepare_done(self, done=True):
        self._indxr_prepare_done = done

        if not done:
            self.set_indexer_done(False)

    def set_indexer_done(self, done=True):
        self._indxr_done = done
        if not done:
            self.set_indexer_finish_done(False)

    def set_indexer_finish_done(self, done=True):
        self._indxr_finish_done = done

    def set_indexer_sweep(self, sweep):
        self.add_indexer_sweep(sweep)

    def get_indexer_sweep(self):
        if self._indxr_sweeps:
            return self._indxr_sweeps[0]

    def add_indexer_sweep(self, sweep):
        self._indxr_sweeps.append(sweep)

    def get_indexer_sweeps(self):
        return self._indxr_sweeps

    def set_indexer_sweep_name(self, sweep_name):
        self._indxr_sweep_name = sweep_name

    def get_indexer_sweep_name(self):
        return self._indxr_sweep_name

    def set_indexer_project_info(self, project_name, crystal_name, dataset_name):
        self._indxr_pname = project_name
        self._indxr_xname = crystal_name
        self._indxr_dname = dataset_name

    def get_indexer_project_info(self):
        return self._indxr_pname, self._indxr_xname, self._indxr_dname

    def get_indexer_full_name(self):
        return "%s %s %s %s" % tuple(
            list(self.get_indexer_project_info()) + [self._indxr_sweep_name]
        )

    # getters of the status - note well that these need to cascade
    # the status... note that for the prepare get there is no previous
    # step we could cascade to...

    def get_indexer_prepare_done(self):
        return self._indxr_prepare_done

    def get_indexer_done(self):

        if not self.get_indexer_prepare_done():
            logger.debug("Resetting indexer done as prepare not done")
            self.set_indexer_done(False)

        return self._indxr_done

    def get_indexer_finish_done(self):

        if not self.get_indexer_done():
            f = inspect.currentframe().f_back
            m = f.f_code.co_filename
            l = f.f_lineno
            logger.debug(
                "Resetting indexer finish done as index not done, from %s/%d", m, l
            )
            self.set_indexer_finish_done(False)

        return self._indxr_finish_done

    # ----------------------------------------------------------
    # "real" methods which actually do something interesting -
    # eliminate() will remove a solution from the indexing table
    # and reset the done, such that the next get() will return
    # the next solution down.
    # ----------------------------------------------------------

    def eliminate(self, indxr_print=True):
        """Eliminate the current solution for autoindexing."""

        if not self._indxr_helper:
            raise RuntimeError("no indexing done yet")

        # not allowed to eliminate a solution provided by the
        # user via set_indexer_lattice... - this is determined by
        # the fact that the set lattice has user = true as
        # an argument

        if self._indxr_user_input_lattice:
            raise RuntimeError("eliminating user supplied lattice")

        self._indxr_helper.eliminate(indxr_print=indxr_print)
        self.set_indexer_done(False)

    def _indxr_replace(self, lattice, cell, indxr_print=True):
        """Replace the highest symmetry in the solution table with this...
        Only use this method if you REALLY know what you are doing!"""

        self._indxr_helper.eliminate(indxr_print=indxr_print)
        self._indxr_helper.insert(lattice, cell)

    def index(self):

        if not self.get_indexer_finish_done():
            f = inspect.currentframe().f_back.f_back
            m = f.f_code.co_filename
            l = f.f_lineno

            logger.debug(
                "Index in %s called from %s %d" % (self.__class__.__name__, m, l)
            )

        while not self.get_indexer_finish_done():
            while not self.get_indexer_done():
                while not self.get_indexer_prepare_done():

                    # --------------
                    # call prepare()
                    # --------------

                    self.set_indexer_prepare_done(True)
                    self._index_prepare()

                # --------------------------------------------
                # then do the proper indexing - using the best
                # solution already stored if available (c/f
                # eliminate above)
                # --------------------------------------------

                self.set_indexer_done(True)

                if self.get_indexer_sweeps():
                    xsweeps = [s.get_name() for s in self.get_indexer_sweeps()]
                    if len(xsweeps) > 1:
                        # find "SWEEPn, SWEEP(n+1), (..), SWEEPm" and aggregate to "SWEEPS n-m"
                        xsweeps = [
                            (int(x[5:]), int(x[5:])) if x.startswith("SWEEP") else x
                            for x in xsweeps
                        ]
                        xsweeps[0] = [xsweeps[0]]

                        def compress(seen, nxt):
                            if (
                                isinstance(seen[-1], tuple)
                                and isinstance(nxt, tuple)
                                and (seen[-1][1] + 1 == nxt[0])
                            ):
                                seen[-1] = (seen[-1][0], nxt[1])
                            else:
                                seen.append(nxt)
                            return seen

                        xsweeps = reduce(compress, xsweeps)
                        xsweeps = [
                            (
                                "SWEEP%d" % x[0]
                                if x[0] == x[1]
                                else "SWEEPS %d to %d" % (x[0], x[1])
                            )
                            if isinstance(x, tuple)
                            else x
                            for x in xsweeps
                        ]
                    if len(xsweeps) > 1:
                        sweep_names = ", ".join(xsweeps[:-1])
                        sweep_names += " & " + xsweeps[-1]
                    else:
                        sweep_names = xsweeps[0]

                    if PhilIndex.params.xia2.settings.show_template:
                        template = self.get_indexer_sweep().get_template()
                        logger.notice(
                            banner("Autoindexing %s (%s)", sweep_names, template)
                        )
                    else:
                        logger.notice(banner("Autoindexing %s" % sweep_names))

                if not self._indxr_helper:
                    self._index()

                    if not self._indxr_done:
                        logger.debug("Looks like indexing failed - try again!")
                        continue

                    solutions = {
                        k: c["cell"] for k, c in self._indxr_other_lattice_cell.items()
                    }

                    # create a helper for the indexer to manage solutions
                    self._indxr_helper = _IndexerHelper(solutions)

                    solution = self._indxr_helper.get()

                    # compare these against the final solution, if different
                    # reject solution and return - correct solution will
                    # be used next cycle

                    if (
                        self._indxr_lattice != solution[0]
                        and not self._indxr_input_cell
                        and not PhilIndex.params.xia2.settings.integrate_p1
                    ):
                        logger.info(
                            "Rerunning indexing lattice %s to %s",
                            self._indxr_lattice,
                            solution[0],
                        )
                        self.set_indexer_done(False)

                else:
                    # rerun autoindexing with the best known current solution

                    solution = self._indxr_helper.get()
                    self._indxr_input_lattice = solution[0]
                    self._indxr_input_cell = solution[1]
                    self._index()

            # next finish up...

            self.set_indexer_finish_done(True)
            self._index_finish()

            if self._indxr_print:
                logger.info(self.show_indexer_solutions())

    def show_indexer_solutions(self):
        lines = ["All possible indexing solutions:"]
        for l in self._indxr_helper.repr():
            lines.append(l)

        crystal_model = self._indxr_experiment_list[0].crystal
        lattice = str(
            bravais_types.bravais_lattice(group=crystal_model.get_space_group())
        )
        lines.append("Indexing solution:")
        lines.append(
            "%s %s"
            % (
                lattice,
                "%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f"
                % crystal_model.get_unit_cell().parameters(),
            )
        )
        return "\n".join(lines)

    # setter methods for the input - most of these will reset the
    # indexer in one way or another

    def add_indexer_imageset(self, imageset):
        self._indxr_imagesets.append(imageset)

    # these relate to propogation of the fact that this is user assigned ->
    # so if we try to eliminate raise an exception... must be coordinated
    # with lattice setting below

    def set_indexer_user_input_lattice(self, user):
        self._indxr_user_input_lattice = user

    def get_indexer_user_input_lattice(self):
        return self._indxr_user_input_lattice

    def set_indexer_input_lattice(self, lattice):
        """Set the input lattice for this indexing job. Exactly how this
        is handled depends on the implementation. FIXED decide on the
        format for the lattice. This will be say tP."""

        self._indxr_input_lattice = lattice
        self.set_indexer_done(False)

    def set_indexer_input_cell(self, cell):
        """Set the input unit cell (optional.)"""

        if not (isinstance(cell, type(())) or isinstance(cell, type([]))):
            raise RuntimeError("cell must be a 6-tuple of floats, is %s" % str(cell))

        if len(cell) != 6:
            raise RuntimeError("cell must be a 6-tuple of floats")

        self._indxr_input_cell = tuple(map(float, cell))
        self.set_indexer_done(False)

    # getter methods for the output - all of these will call index()
    # which will guarantee that the results are up to date (recall
    # while structure above)

    def get_indexer_cell(self):
        """Get the selected unit cell."""

        self.index()
        return self._indxr_experiment_list[0].crystal.get_unit_cell().parameters()

    def get_indexer_lattice(self):
        """Get the selected lattice as tP form."""

        self.index()

        crystal_model = self._indxr_experiment_list[0].crystal
        return str(bravais_types.bravais_lattice(group=crystal_model.get_space_group()))

    def get_indexer_mosaic(self):
        """Get the estimated mosaic spread in degrees."""

        self.index()
        return self._indxr_mosaic

    def get_indexer_distance(self):
        """Get the refined distance."""

        self.index()
        experiment = self.get_indexer_experiment_list()[0]
        return experiment.detector[0].get_directed_distance()

    def get_indexer_beam_centre(self):
        """Get the refined beam."""

        self.index()
        experiment = self.get_indexer_experiment_list()[0]
        # FIXME need to consider interaction of xia2 with multi-panel detectors
        return tuple(reversed(beam_centre(experiment.detector, experiment.beam)[1]))

    def get_indexer_beam_centre_raw_image(self):
        """Get the refined beam in raw image coordinates."""

        self.index()
        experiment = self.get_indexer_experiment_list()[0]
        return tuple(
            reversed(beam_centre_raw_image(experiment.detector, experiment.beam))
        )

    def get_indexer_payload(self, this):
        """Attempt to get something from the indexer payload."""

        self.index()
        return self._indxr_payload.get(this)

    def get_indexer_low_resolution(self):
        """Get an estimate of the low resolution limit of the data."""

        self.index()
        return self._indxr_low_resolution

    def set_indexer_payload(self, this, value):
        """Set something in the payload."""

        self._indxr_payload[this] = value

    # new method to handle interaction with the pointgroup determination
    # much later on in the process - this allows a dialogue to be established.

    def set_indexer_asserted_lattice(self, asserted_lattice):
        """Assert that this lattice is correct - if this is allowed (i.e.
        is in the helpers list of kosher lattices) then it will be enabled.
        If this is different to the current favourite then processing
        may ensue, otherwise nothing will happen."""

        assert self._indxr_helper

        all_lattices = self._indxr_helper.get_all()

        if asserted_lattice not in [l[0] for l in all_lattices]:
            return self.LATTICE_IMPOSSIBLE

        # check if this is the top one - if so we don't need to
        # do anything

        if asserted_lattice == all_lattices[0][0]:

            if (
                PhilIndex.params.xia2.settings.integrate_p1
                and asserted_lattice != self.get_indexer_lattice()
                and asserted_lattice != "aP"
            ):
                if PhilIndex.params.xia2.settings.reintegrate_correct_lattice:
                    self.set_indexer_done(False)
                    return self.LATTICE_POSSIBLE
                return self.LATTICE_CORRECT

            return self.LATTICE_CORRECT

        # ok this means that we need to do something - work through
        # eliminating lattices until the "correct" one is found...

        while self._indxr_helper.get()[0] != asserted_lattice:
            self._indxr_helper.eliminate()
            if (
                not PhilIndex.params.xia2.settings.integrate_p1
                or PhilIndex.params.xia2.settings.reintegrate_correct_lattice
            ):
                self.set_indexer_done(False)

        return self.LATTICE_POSSIBLE

    def set_indexer_experiment_list(self, experiments_list):
        self._indxr_experiment_list = experiments_list

    def get_indexer_experiment_list(self):
        self.index()
        return self._indxr_experiment_list


# class for legacy Indexers that only support indexing from a single sweep
class IndexerSingleSweep(Indexer):
    def __init__(self):
        super().__init__()
        self._indxr_images = []

    def get_imageset(self):
        return self._indxr_imagesets[0]

    def get_scan(self):
        return self.get_imageset().get_scan()

    def get_detector(self):
        return self.get_imageset().get_detector()

    def set_detector(self, detector):
        self.get_imageset().set_detector(detector)

    def get_goniometer(self):
        return self.get_imageset().get_goniometer()

    def set_goniometer(self, goniometer):
        return self.get_imageset().set_goniometer(goniometer)

    def get_beam(self):
        return self.get_imageset().get_beam()

    def set_beam(self, beam):
        return self.get_imageset().set_beam(beam)

    def get_wavelength(self):
        return self.get_beam().get_wavelength()

    def get_distance(self):
        return self.get_detector()[0].get_directed_distance()

    def get_phi_width(self):
        return self.get_scan().get_oscillation()[1]

    def get_matching_images(self):
        start, end = self.get_scan().get_array_range()
        return tuple(range(start + 1, end + 1))

    def get_image_name(self, number):
        first = self.get_scan().get_image_range()[0]
        return self.get_imageset().get_path(number - first)

    def get_template(self):
        return self.get_imageset().get_template()

    def get_directory(self):
        return os.path.dirname(self.get_template())

    def add_indexer_image_wedge(self, image, reset=True):
        """Add some images for autoindexing (optional) input is a 2-tuple
        or an integer."""

        if isinstance(image, type(())):
            self._indxr_images.append(image)
        if isinstance(image, type(1)):
            self._indxr_images.append((image, image))

        if reset:
            self.set_indexer_prepare_done(False)

    def get_indexer_images(self):
        return self._indxr_images
