# An interface for programs which do integration - this will handle
# all of the input and output, delegating the actual processing to an
# implementation of this interfacing.
#
# The following are considered critical:
#
# Input:
# An implementation of the indexer class.
#
# Output:
# [processed reflections?]
#
# This is a complex problem to solve...
#
# Assumptions & Assertions:
#
# (1) Integration includes any cell and orientation refinement.
#     This should be handled under the prepare phase.
# (2) If there is no indexer implementation provided as input,
#     it's ok to go make one, or raise an exception (maybe.)
#
# This means...
#
# (1) That this needs to have the posibility of specifying images for
#     use in both cell refinement (as a list of wedges, similar to
#     the indexer interface) and as a SINGLE WEDGE for use in integration.
# (2) This may default to a local implementation using the same program,
#     e.g. XDS or Mosflm - will not necessarily select the best one.
#     This is left to the implementation to sort out.


import inspect
import json
import logging
import math
import os

import xia2.Schema.Interfaces.Indexer
import xia2.Schema.Interfaces.Refiner

# symmetry operator management functionality
from xia2.Experts.SymmetryExpert import compose_symops, symop_to_mat
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import banner
from xia2.Schema.Exceptions.BadLatticeError import BadLatticeError

# interfaces that this inherits from ...
from xia2.Schema.Interfaces.FrameProcessor import FrameProcessor
from dxtbx.serialize.load import _decode_dict

logger = logging.getLogger("xia2.Schema.Interfaces.Integrater")


class Integrater(FrameProcessor):
    """An interface to present integration functionality in a similar
    way to the indexer interface."""

    def __init__(self):

        super().__init__()

        # admin junk
        self._intgr_working_directory = os.getcwd()

        # a pointer to an implementation of the indexer class from which
        # to get orientation (maybe) and unit cell, lattice (definitely)
        self._intgr_indexer = None
        self._intgr_refiner = None

        # optional parameters - added user for # 3183
        self._intgr_reso_high = 0.0
        self._intgr_reso_low = 0.0
        self._intgr_reso_user = False

        # presence of ice rings - 0 indicates "no" anything else
        # indicates "yes". FIXME this should be able to identify
        # different resolution rings.
        self._intgr_ice = 0
        self._intgr_excluded_regions = []

        # required parameters
        self._intgr_wedge = None

        # implementation dependent parameters - these should be keyed by
        # say 'mosflm':{'yscale':0.9999} etc.
        self._intgr_program_parameters = {}

        # the same, but for export to other instances of this interface
        # via the .xinfo hierarchy
        self._intgr_export_program_parameters = {}

        # batches to integrate, batches which were integrated - this is
        # to allow programs like rebatch to work c/f self._intgr_wedge
        # note well that this may have to be implemented via mtzdump?
        # or just record the images which were integrated...
        self._intgr_batches_out = [0, 0]

        # flags which control how the execution is performed
        # in the main integrate() method below.
        self._intgr_done = False
        self._intgr_prepare_done = False
        self._intgr_finish_done = False

        # the output reflections
        self._intgr_hklout_raw = None
        self._intgr_hklout = None
        # 'hkl' or 'pickle', if pickle then self._intgr_hklout returns a refl table.
        self._output_format = "hkl"

        # a place to store the project, crystal, wavelength, sweep information
        # to interface with the scaling...
        self._intgr_epoch = 0
        self._intgr_pname = None
        self._intgr_xname = None
        self._intgr_dname = None
        self._intgr_sweep = None
        self._intgr_sweep_name = None

        # results - refined cell and number of reflections
        self._intgr_cell = None
        self._intgr_n_ref = None

        # reindexing operations etc. these will come from feedback
        # from the scaling to ensure that the setting is uniform
        self._intgr_spacegroup_number = 0
        self._intgr_reindex_operator = None
        self._intgr_reindex_matrix = None

        # extra information which could be helpful for integration
        self._intgr_anomalous = False

        # mosaic spread information
        self._intgr_mosaic_min = None
        self._intgr_mosaic_mean = None
        self._intgr_mosaic_max = None

        self._intgr_per_image_statistics = None

    # serialization functions

    def to_dict(self):
        obj = {}
        obj["__id__"] = "Integrater"
        obj["__module__"] = self.__class__.__module__
        obj["__name__"] = self.__class__.__name__

        attributes = inspect.getmembers(self, lambda m: not inspect.isroutine(m))
        for a in attributes:
            if a[0] in ("_intgr_indexer", "_intgr_refiner") and a[1] is not None:
                obj[a[0]] = a[1].to_dict()
            elif a[0] == "_fp_imageset":
                from dxtbx.serialize.imageset import imageset_to_dict

                obj[a[0]] = imageset_to_dict(a[1])
            elif a[0] == "_intgr_sweep":
                # XXX I guess we probably want this?
                continue
            elif a[0].startswith("_intgr_") or a[0].startswith("_fp_"):
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "Integrater"
        return_obj = cls()
        for k, v in obj.items():
            if k in ("_intgr_indexer", "_intgr_refiner") and v is not None:
                from libtbx.utils import import_python_object

                cls = import_python_object(
                    import_path=".".join((v["__module__"], v["__name__"])),
                    error_prefix="",
                    target_must_be="",
                    where_str="",
                ).object
                v = cls.from_dict(v)
            if isinstance(v, dict):
                if v.get("__id__") == "ExperimentList":
                    from dxtbx.model.experiment_list import ExperimentListFactory

                    v = ExperimentListFactory.from_dict(v)
                elif v.get("__id__") == "imageset":
                    from dxtbx.serialize.imageset import imageset_from_dict

                    v = imageset_from_dict(v, check_format=False)
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

    # ------------------------------------------------------------------
    # These methods need to be overloaded by the actual implementation -
    # they are all called from within the main integrate() method. The
    # roles of each of these could be as follows -
    #
    # prepare - prerefine the unit cell
    # integrate - measure the intensities of all reflections
    # finish - reindex these to the correct setting
    #
    # though this is just one interpretation...
    # ------------------------------------------------------------------

    def _integrate_prepare(self):
        raise NotImplementedError("overload me")

    def _integrate(self):
        raise NotImplementedError("overload me")

    def _integrate_finish(self):
        raise NotImplementedError("overload me")

    # ------------------------------------
    # end methods which MUST be overloaded
    # ------------------------------------

    def _integrater_reset(self):
        """Reset the integrater, e.g. if the autoindexing solution
        has changed."""

        # reset the status flags
        self.set_integrater_prepare_done(False)
        self.set_integrater_done(False)
        self.set_integrater_finish_done(False)

        # reset the "knowledge" from the data
        # note well - if we have set a resolution limit
        # externally then this will have to be respected...
        # e.g. - added user for # 3183

        if not self._intgr_reso_user:
            self._intgr_reso_high = 0.0
            self._intgr_reso_low = 0.0

        self._intgr_hklout_raw = None
        self._intgr_hklout = None
        self._intgr_program_parameters = {}

        self._integrater_reset_callback()

    def set_integrater_sweep(self, sweep, reset=True):
        self._intgr_sweep = sweep
        if reset:
            self._integrater_reset()

    def get_integrater_sweep(self):
        return self._intgr_sweep

    # setters and getters for the "done"-ness of different operations
    # note that this cascades

    def set_integrater_prepare_done(self, done=True):
        self._intgr_prepare_done = done
        if not done:
            self.set_integrater_done(False)

    def set_integrater_done(self, done=True):
        self._intgr_done = done

        # FIXME should I remove / reset the reindexing operation here?
        # probably...!

        if not done:
            self._intgr_reindex_operator = None

        if not done:
            self.set_integrater_finish_done(False)

    def set_integrater_finish_done(self, done=True):
        self._intgr_finish_done = done

    # getters of the status - note how these cascade the get to ensure
    # that everything is up-to-date...

    def get_integrater_prepare_done(self):
        if not self.get_integrater_refiner():
            return self._intgr_prepare_done

        refiner = self.get_integrater_refiner()
        if not refiner.get_refiner_done() and self._intgr_prepare_done:
            for sweep in refiner._refinr_sweeps:
                logger.debug(
                    "Resetting integrater for sweep {} as refiner updated.".format(
                        sweep._name
                    )
                )
                sweep._integrater._integrater_reset()

        return self._intgr_prepare_done

    def get_integrater_done(self):

        if not self.get_integrater_prepare_done():
            logger.debug("Resetting integrater done as prepare not done")
            self.set_integrater_done(False)

        return self._intgr_done

    def get_integrater_finish_done(self):

        if not self.get_integrater_done():
            logger.debug("Resetting integrater finish done as integrate not done")
            self.set_integrater_finish_done(False)

        return self._intgr_finish_done

    # end job control stuff - next getters for results

    def get_integrater_cell(self):
        """Get the (post) refined unit cell."""

        self.integrate()
        return self._intgr_cell

    def get_integrater_n_ref(self):
        """Get the number of reflections in the data set."""

        self.integrate()
        return self._intgr_n_ref

    # getters and setters of administrative information

    def set_working_directory(self, working_directory):
        self._intgr_working_directory = working_directory

    def get_working_directory(self):
        return self._intgr_working_directory

    def set_integrater_sweep_name(self, sweep_name):
        self._intgr_sweep_name = sweep_name

    def get_integrater_sweep_name(self):
        return self._intgr_sweep_name

    def set_integrater_project_info(self, project_name, crystal_name, dataset_name):
        """Set the metadata information, to allow passing on of information
        both into the reflection files (if possible) or to the scaling stages
        for dataset administration."""

        self._intgr_pname = project_name
        self._intgr_xname = crystal_name
        self._intgr_dname = dataset_name

    def get_integrater_project_info(self):
        return self._intgr_pname, self._intgr_xname, self._intgr_dname

    def get_integrater_epoch(self):
        return self._intgr_epoch

    def set_integrater_epoch(self, epoch):
        self._intgr_epoch = epoch

    def set_integrater_wedge(self, start, end):
        """Set the wedge of images to process."""

        start = start - self.get_frame_offset()
        end = end - self.get_frame_offset()

        self._intgr_wedge = (start, end)

        # get the epoch for the sweep if not already defined
        epoch = self.get_scan().get_epochs()[0]

        if epoch > 0 and self._intgr_epoch == 0:
            self._intgr_epoch = epoch

        logger.debug("Sweep epoch: %d" % self._intgr_epoch)

        self.set_integrater_done(False)

    def get_integrater_wedge(self):
        """Get the wedge of images assigned to this integrater."""

        return self._intgr_wedge

    def get_integrater_resolution(self):
        """Get both resolution limits, high then low."""
        return self._intgr_reso_high, self._intgr_reso_low

    def get_integrater_high_resolution(self):
        return self._intgr_reso_high

    def get_integrater_low_resolution(self):
        return self._intgr_reso_low

    def get_integrater_user_resolution(self):
        """Return a boolean: were the resolution limits set by
        the user? See bug # 3183"""
        return self._intgr_reso_user

    def set_integrater_resolution(self, dmin, dmax, user=False):
        """Set both resolution limits."""

        if self._intgr_reso_user and not user:
            raise RuntimeError("cannot override user set limits")

        if user:
            self._intgr_reso_user = True

        self._intgr_reso_high = min(dmin, dmax)
        self._intgr_reso_low = max(dmin, dmax)

        self.set_integrater_done(False)

    def set_integrater_high_resolution(self, dmin, user=False):
        """Set high resolution limit."""

        if self._intgr_reso_user and not user:
            raise RuntimeError("cannot override user set limits")

        if user:
            self._intgr_reso_user = True

        self._intgr_reso_high = dmin
        self.set_integrater_done(False)

    def set_integrater_low_resolution(self, dmax):
        """Set low resolution limit."""

        self._intgr_reso_low = dmax
        self.set_integrater_done(False)

    def set_integrater_mosaic_min_mean_max(self, m_min, m_mean, m_max):
        self._intgr_mosaic_min = m_min
        self._intgr_mosaic_mean = m_mean
        self._intgr_mosaic_max = m_max

    def get_integrater_mosaic_min_mean_max(self):
        return self._intgr_mosaic_min, self._intgr_mosaic_mean, self._intgr_mosaic_max

    # getters and setters for program specific parameters
    # => values kept in dictionary

    def set_integrater_parameter(self, program, parameter, value):
        """Set an arbitrary parameter for the program specified to
        use in integration, e.g. the YSCALE or GAIN values in Mosflm."""

        if program not in self._intgr_program_parameters:
            self._intgr_program_parameters[program] = {}

        self._intgr_program_parameters[program][parameter] = value

    def set_integrater_parameters(self, parameters):
        """Set all parameters and values."""

        self._intgr_program_parameters = parameters
        self.set_integrater_done(False)

    def get_integrater_export_parameter(self, program, parameter):
        """Get a parameter value."""

        try:
            return self._intgr_export_program_parameters[program][parameter]
        except Exception:
            return None

    def get_integrater_export_parameters(self):
        """Get all parameters and values."""

        try:
            return self._intgr_export_program_parameters
        except Exception:
            return {}

    def set_integrater_indexer(self, indexer):
        """Set the indexer implementation to use for this integration."""

        assert issubclass(indexer.__class__, xia2.Schema.Interfaces.Indexer.Indexer), (
            "%s is not an Indexer implementation" % indexer
        )

        self._intgr_indexer = indexer
        self.set_integrater_prepare_done(False)

    def set_integrater_refiner(self, refiner):
        """Set the refiner implementation to use for this integration."""

        assert issubclass(refiner.__class__, xia2.Schema.Interfaces.Refiner.Refiner), (
            "%s is not a Refiner implementation" % refiner
        )

        self._intgr_refiner = refiner
        self.set_integrater_prepare_done(False)

    def integrate(self):
        """Actually perform integration until we think we are done..."""

        while not self.get_integrater_finish_done():
            while not self.get_integrater_done():
                while not self.get_integrater_prepare_done():

                    logger.debug("Preparing to do some integration...")
                    self.set_integrater_prepare_done(True)

                    # if this raises an exception, perhaps the autoindexing
                    # solution has too high symmetry. if this the case, then
                    # perform a self._intgr_indexer.eliminate() - this should
                    # reset the indexing system

                    try:
                        self._integrate_prepare()

                    except BadLatticeError as e:
                        logger.info("Rejecting bad lattice %s", str(e))
                        self._intgr_refiner.eliminate()
                        self._integrater_reset()

                # FIXME x1698 - may be the case that _integrate() returns the
                # raw intensities, _integrate_finish() returns intensities
                # which may have been adjusted or corrected. See #1698 below.

                logger.debug("Doing some integration...")

                self.set_integrater_done(True)

                template = self.get_integrater_sweep().get_template()

                if self._intgr_sweep_name:
                    if PhilIndex.params.xia2.settings.show_template:
                        logger.notice(
                            banner(
                                "Integrating %s (%s)"
                                % (self._intgr_sweep_name, template)
                            )
                        )
                    else:
                        logger.notice(banner("Integrating %s" % self._intgr_sweep_name))
                try:

                    # 1698
                    self._intgr_hklout_raw = self._integrate()

                except BadLatticeError as e:
                    logger.info("Rejecting bad lattice %s", str(e))
                    self._intgr_refiner.eliminate()
                    self._integrater_reset()

            self.set_integrater_finish_done(True)
            try:
                # allow for the fact that postrefinement may be used
                # to reject the lattice...
                self._intgr_hklout = self._integrate_finish()

            except BadLatticeError as e:
                logger.info("Bad Lattice Error: %s", str(e))
                self._intgr_refiner.eliminate()
                self._integrater_reset()
        return self._intgr_hklout

    def set_output_format(self, output_format="hkl"):
        logger.debug("setting integrator output format to %s" % output_format)
        assert output_format in ["hkl", "pickle"]
        self._output_format = output_format

    def get_integrater_refiner(self):
        return self._intgr_refiner

    def get_integrater_intensities(self):
        self.integrate()
        return self._intgr_hklout

    def get_integrater_batches(self):
        self.integrate()
        return self._intgr_batches_out

    # Should anomalous pairs be treated separately? Implementations
    # of Integrater are free to ignore this.

    def set_integrater_anomalous(self, anomalous):
        self._intgr_anomalous = anomalous

    def get_integrater_anomalous(self):
        return self._intgr_anomalous

    # ice rings

    def set_integrater_ice(self, ice):
        self._intgr_ice = ice

    def get_integrater_ice(self):
        return self._intgr_ice

    # excluded_regions is a list of tuples representing
    # upper and lower resolution ranges to exclude
    def set_integrater_excluded_regions(self, excluded_regions):
        self._intgr_excluded_regions = excluded_regions

    def get_integrater_excluded_regions(self):
        return self._intgr_excluded_regions

    def set_integrater_spacegroup_number(self, spacegroup_number):
        # FIXME check that this is appropriate with what the
        # indexer things is currently correct. Also - should this
        # really just refer to a point group??

        logger.debug("Set spacegroup as %d" % spacegroup_number)

        # certainly should wipe the reindexing operation! erp! only
        # if the spacegroup number is DIFFERENT
        if spacegroup_number == self._intgr_spacegroup_number:
            return

        self._intgr_reindex_operator = None
        self._intgr_reindex_matrix = None

        self._intgr_spacegroup_number = spacegroup_number

        self.set_integrater_finish_done(False)

    def get_integrater_spacegroup_number(self):
        return self._intgr_spacegroup_number

    def integrater_reset_reindex_operator(self):
        """Reset the reindex operator."""

        return self.set_integrater_reindex_operator("h,k,l", compose=False)

    def set_integrater_reindex_operator(
        self, reindex_operator, compose=True, reason=None
    ):
        """Assign a symmetry operator to the reflections - note
        that this is cumulative..."""

        reindex_operator = reindex_operator.lower().strip()

        # see if we really need to do anything
        if reindex_operator == "h,k,l" and self._intgr_reindex_operator == "h,k,l":
            return

        # ok we need to do something - either just record the new
        # operation or compose it with the existing operation

        self.set_integrater_finish_done(False)

        if reason:
            logger.debug(
                "Reindexing to %s (compose=%s) because %s"
                % (reindex_operator, compose, reason)
            )

        if self._intgr_reindex_operator is None or not compose:
            self._intgr_reindex_operator = reindex_operator

        else:
            old_operator = self._intgr_reindex_operator
            self._intgr_reindex_operator = compose_symops(
                reindex_operator, old_operator
            )

            logger.debug(
                "Composing %s and %s -> %s"
                % (old_operator, reindex_operator, self._intgr_reindex_operator)
            )

        # convert this to a 3x3 matrix form for e.g. XDS CORRECT
        self._intgr_reindex_matrix = symop_to_mat(self._intgr_reindex_operator)

        self._set_integrater_reindex_operator_callback()

    def get_integrater_reindex_operator(self):
        return self._intgr_reindex_operator

    def get_integrater_reindex_matrix(self):
        return self._intgr_reindex_matrix

    # ------------------------------------------------
    # callback methods - overloading these is optional
    # ------------------------------------------------

    def _integrater_reset_callback(self):
        """Overload this if you have other things which need to be reset."""
        pass

    def _set_integrater_reindex_operator_callback(self):
        pass

    def show_per_image_statistics(self):
        lines = []
        assert self._intgr_per_image_statistics is not None

        stats = self._intgr_per_image_statistics

        # analyse stats here, perhaps raising an exception if we
        # are unhappy with something, so that the indexing solution
        # can be eliminated in the integrater.

        images = sorted(stats)

        # these may not be present if only a couple of the
        # images were integrated...

        try:
            stddev_pixel = [stats[i]["rmsd_pixel"] for i in images]

            # fix to bug # 2501 - remove the extreme values from this
            # list...

            stddev_pixel = sorted(set(stddev_pixel))

            # only remove the extremes if there are enough values
            # that this is meaningful... very good data may only have
            # two values!

            if len(stddev_pixel) > 4:
                stddev_pixel = stddev_pixel[1:-1]

            low, high = min(stddev_pixel), max(stddev_pixel)

            lines.append("Processed batches %d to %d" % (min(images), max(images)))

            lines.append(f"Standard Deviation in pixel range: {low:.2f} {high:.2f}")

            overloads = None
            fraction_weak = None
            isigi = None

            # print a one-spot-per-image rendition of this...
            stddev_pixel = [stats[i]["rmsd_pixel"] for i in images]
            if "overloads" in list(stats.values())[0]:
                overloads = [stats[i]["overloads"] for i in images]
            strong = [stats[i]["strong"] for i in images]
            if "fraction_weak" in list(stats.values())[0]:
                fraction_weak = [stats[i]["fraction_weak"] for i in images]
            if "isigi" in list(stats.values())[0]:
                isigi = [stats[i]["isigi"] for i in images]

            # FIXME need to allow for blank images in here etc.

            status_record = ""
            for i, stddev in enumerate(stddev_pixel):
                if fraction_weak is not None and fraction_weak[i] > 0.99:
                    status_record += "."
                elif isigi is not None and isigi[i] < 1.0:
                    status_record += "."
                elif stddev > 2.5:
                    status_record += "!"
                elif stddev > 1.0:
                    status_record += "%"
                elif overloads is not None and overloads[i] > 0.01 * strong[i]:
                    status_record += "O"
                else:
                    status_record += "o"

            if len(status_record) > 60:
                lines.append("Integration status per image (60/record):")
            else:
                lines.append("Integration status per image:")

            for chunk in (
                status_record[i : i + 60] for i in range(0, len(status_record), 60)
            ):
                lines.append(chunk)
            lines.append('"o" => good        "%" => ok        "!" => bad rmsd')
            lines.append('"O" => overloaded  "#" => many bad  "." => weak')
            lines.append('"@" => abandoned')

            # next look for variations in the unit cell parameters
            if "unit_cell" in list(stats.values())[0]:
                unit_cells = [stats[i]["unit_cell"] for i in images]

                # compute average
                uc_mean = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

                for uc in unit_cells:
                    for j in range(6):
                        uc_mean[j] += uc[j]

                for j in range(6):
                    uc_mean[j] /= len(unit_cells)

                max_rel_dev = 0.0

                for uc in unit_cells:
                    for j in range(6):
                        if (math.fabs(uc[j] - uc_mean[j]) / uc_mean[j]) > max_rel_dev:
                            max_rel_dev = math.fabs(uc[j] - uc_mean[j]) / uc_mean[j]

                lines.append("Maximum relative deviation in cell: %.3f" % max_rel_dev)

        except KeyError:
            raise RuntimeError("Refinement not performed...")

        return "\n".join(lines)
