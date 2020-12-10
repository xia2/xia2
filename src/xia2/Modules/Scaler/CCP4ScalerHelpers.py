# Helpers for the "CCP4" Scaler implementation - this contains little
# functions which wrap the wrappers which are needed. It will also contain
# small functions for computing e.g. resolution limits.


import inspect
import logging
import math
import os

import xia2.Wrappers.CCP4.Pointless
import xia2.Wrappers.Dials.Symmetry
from cctbx.sgtbx import lattice_symmetry_group
from iotbx import mtz
from scitbx.matrix import sqr
from xia2.Experts.ResolutionExperts import remove_blank
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.lib.bits import auto_logfiler
from xia2.Modules import MtzUtils

logger = logging.getLogger("xia2.Modules.Scaler.CCP4ScalerHelpers")


def nint(a):
    return int(round(a) - 0.5) + (a > 0)


def ersatz_resolution(reflection_file, batch_ranges):
    mtz_obj = mtz.object(reflection_file)

    miller = mtz_obj.extract_miller_indices()
    dmax, dmin = mtz_obj.max_min_resolution()

    ipr_column = None
    sigipr_column = None
    i_column = None
    sigi_column = None
    batch_column = None

    uc = None

    for crystal in mtz_obj.crystals():

        if crystal.name() == "HKL_Base":
            continue

        uc = crystal.unit_cell()

        for dataset in crystal.datasets():
            for column in dataset.columns():

                if column.label() == "IPR":
                    ipr_column = column
                elif column.label() == "SIGIPR":
                    sigipr_column = column
                elif column.label() == "BATCH":
                    batch_column = column
                elif column.label() == "I":
                    i_column = column
                elif column.label() == "SIGI":
                    sigi_column = column

    assert ipr_column or i_column
    assert sigipr_column or sigi_column
    assert batch_column

    if ipr_column is None:
        ipr_column = i_column
    if sigipr_column is None:
        sigipr_column = sigi_column

    ipr_values = ipr_column.extract_values()
    sigipr_values = sigipr_column.extract_values()
    batch_values = batch_column.extract_values()
    batches = batch_values.as_double().iround()
    resolutions = {}

    for start, end in batch_ranges:
        sel = (batches >= start) & (batches <= end)
        d = uc.d(miller.select(sel))
        isig = ipr_values.select(sel) / sigipr_values.select(sel)
        resolutions[(start, end)] = compute_resolution(dmax, dmin, d, isig)

    return resolutions


def meansd(values):
    mean = sum(values) / len(values)
    var = sum((v - mean) * (v - mean) for v in values) / len(values)
    return mean, math.sqrt(var)


def compute_resolution(dmax, dmin, d, isig):
    # XXX As far as I can tell this function doesn't do anything useful as it
    # just returns the unmodified dmin that was passed as input! Please refer
    # to return 1.0 / math.sqrt(s) below & remove comment when you are happy...

    bins = {}

    smax = 1.0 / (dmax * dmax)
    smin = 1.0 / (dmin * dmin)

    for j, dj in enumerate(d):
        s = 1.0 / (dj * dj)
        n = nint(100.0 * (s - smax) / (smin - smax))
        bins.setdefault(n, []).append(isig[j])

    # compute starting point i.e. maximum point on the curve, to cope with
    # cases where low resolution has low I / sigma - see #1690.

    max_misig = 0.0
    max_bin = 0

    for b in sorted(bins):
        misig = meansd(bins[b])[0]

        if misig > max_misig:
            max_misig = misig
            max_bin = b

    for b in sorted(bins):
        if b < max_bin:
            continue

        s = smax + b * (smin - smax) / 100.0
        misig = meansd(bins[b])[0]
        if misig < 1.0:
            return 1.0 / math.sqrt(s)

    return dmin


def _prepare_pointless_hklin(working_directory, hklin, phi_width):
    """Prepare some data for pointless - this will take only 180 degrees
    of data if there is more than this (through a "pointless" command) else
    will simply return hklin."""

    # also remove blank images?

    if not PhilIndex.params.xia2.settings.small_molecule:
        logger.debug("Excluding blank images")

        hklout = os.path.join(
            working_directory, "%s_noblank.mtz" % (os.path.split(hklin)[-1][:-4])
        )

        FileHandler.record_temporary_file(hklout)

        hklin = remove_blank(hklin, hklout)

    # find the number of batches

    batches = MtzUtils.batches_from_mtz(hklin)
    n_batches = max(batches) - min(batches)

    phi_limit = 180

    if (
        n_batches * phi_width < phi_limit
        or PhilIndex.params.xia2.settings.small_molecule
    ):
        return hklin

    hklout = os.path.join(
        working_directory, "%s_prepointless.mtz" % (os.path.split(hklin)[-1][:-4])
    )

    pl = xia2.Wrappers.CCP4.Pointless.Pointless()
    pl.set_working_directory(working_directory)
    auto_logfiler(pl)
    pl.set_hklin(hklin)
    pl.set_hklout(hklout)

    first = min(batches)
    last = first + int(phi_limit / phi_width)

    logger.debug(
        "Preparing data for pointless - %d batches (%d degrees)"
        % ((last - first), phi_limit)
    )

    pl.limit_batches(first, last)

    # we will want to delete this one exit
    FileHandler.record_temporary_file(hklout)

    return hklout


############### HELPER CLASS #########################


class CCP4ScalerHelper:
    """A class to help the CCP4 Scaler along a little."""

    def __init__(self):
        self._working_directory = os.getcwd()

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory

    def get_working_directory(self):
        return self._working_directory

    def Pointless(self):
        """Create a Pointless wrapper from the xia2 wrapper - and set the
        working directory and log file stuff as a part of this..."""
        pointless = xia2.Wrappers.CCP4.Pointless.Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)
        return pointless

    def dials_symmetry(self):
        symmetry = xia2.Wrappers.Dials.Symmetry.DialsSymmetry()
        symmetry.set_working_directory(self.get_working_directory())
        auto_logfiler(symmetry)
        return symmetry

    def pointless_indexer_jiffy(self, hklin, refiner):
        """A jiffy to centralise the interactions between pointless
        and the Indexer."""

        need_to_return = False
        probably_twinned = False

        if PhilIndex.params.xia2.settings.symmetry.program == "dials":
            symmetry = self.dials_symmetry()
        else:
            symmetry = self.Pointless()

        symmetry.set_hklin(hklin)
        symmetry.decide_pointgroup()

        rerun_pointless = False

        possible = symmetry.get_possible_lattices()

        correct_lattice = None

        logger.debug("Possible lattices (pointless):")

        logger.debug(" ".join(possible))

        for lattice in possible:
            state = refiner.set_refiner_asserted_lattice(lattice)
            if state == refiner.LATTICE_CORRECT:
                logger.debug("Agreed lattice %s" % lattice)
                correct_lattice = lattice
                break

            elif state == refiner.LATTICE_IMPOSSIBLE:
                logger.debug("Rejected lattice %s" % lattice)
                rerun_pointless = True
                continue

            elif state == refiner.LATTICE_POSSIBLE:
                logger.debug("Accepted lattice %s, will reprocess" % lattice)
                need_to_return = True
                correct_lattice = lattice
                break

        if correct_lattice is None:
            correct_lattice = refiner.get_refiner_lattice()
            rerun_pointless = True

            logger.debug("No solution found: assuming lattice from refiner")

        if rerun_pointless:
            symmetry.set_correct_lattice(correct_lattice)
            symmetry.decide_pointgroup()

        logger.debug("Pointless analysis of %s" % symmetry.get_hklin())

        pointgroup = symmetry.get_pointgroup()
        reindex_op = symmetry.get_reindex_operator()
        probably_twinned = symmetry.get_probably_twinned()

        logger.debug(f"Pointgroup: {pointgroup} ({reindex_op})")

        return pointgroup, reindex_op, need_to_return, probably_twinned

    def pointless_indexer_multisweep(self, hklin, refiners):
        """A jiffy to centralise the interactions between pointless
        and the Indexer, multisweep edition."""

        need_to_return = False
        probably_twinned = False

        pointless = self.Pointless()
        pointless.set_hklin(hklin)
        pointless.decide_pointgroup()

        rerun_pointless = False

        possible = pointless.get_possible_lattices()

        correct_lattice = None

        logger.debug("Possible lattices (pointless):")

        logger.debug(" ".join(possible))

        # any of them contain the same indexer link, so all good here.
        refiner = refiners[0]

        for lattice in possible:
            state = refiner.set_refiner_asserted_lattice(lattice)
            if state == refiner.LATTICE_CORRECT:
                logger.debug("Agreed lattice %s" % lattice)
                correct_lattice = lattice
                break

            elif state == refiner.LATTICE_IMPOSSIBLE:
                logger.debug("Rejected lattice %s" % lattice)
                rerun_pointless = True
                continue

            elif state == refiner.LATTICE_POSSIBLE:
                logger.debug("Accepted lattice %s, will reprocess" % lattice)
                need_to_return = True
                correct_lattice = lattice
                break

        if correct_lattice is None:
            correct_lattice = refiner.get_refiner_lattice()
            rerun_pointless = True

            logger.debug("No solution found: assuming lattice from refiner")

        if need_to_return:
            if (
                PhilIndex.params.xia2.settings.integrate_p1
                and not PhilIndex.params.xia2.settings.reintegrate_correct_lattice
            ):
                need_to_return = False
                rerun_pointless = True
            else:
                for refiner in refiners[1:]:
                    refiner.refiner_reset()

        if rerun_pointless:
            pointless.set_correct_lattice(correct_lattice)
            pointless.decide_pointgroup()

        logger.debug("Pointless analysis of %s" % pointless.get_hklin())

        pointgroup = pointless.get_pointgroup()
        reindex_op = pointless.get_reindex_operator()
        probably_twinned = pointless.get_probably_twinned()

        logger.debug(f"Pointgroup: {pointgroup} ({reindex_op})")

        return pointgroup, reindex_op, need_to_return, probably_twinned


# Sweep info class to replace dictionary... #884


class SweepInformation:
    def __init__(self, integrater):

        self._project_info = integrater.get_integrater_project_info()
        self._sweep_name = integrater.get_integrater_sweep_name()
        self._integrater = integrater
        sweep = integrater.get_integrater_sweep()
        self._batches = sweep.get_frames_to_process()
        if self._batches is None:
            self._batches = integrater.get_integrater_batches()
        self._batch_offset = 0

        self._image_to_epoch = integrater.get_integrater_sweep().get_image_to_epoch()
        self._image_to_dose = {}

        self._reflections = None
        self._experiments = None

    def to_dict(self):
        obj = {}
        obj["__id__"] = "SweepInformation"

        attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
        for a in attributes:
            if a[0].startswith("__"):
                continue
            elif a[0] == "_integrater":
                obj[a[0]] = a[1].to_dict()
            else:
                obj[a[0]] = a[1]
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "SweepInformation"
        return_obj = cls.__new__(cls)
        for k, v in obj.items():
            if k == "_integrater":
                from libtbx.utils import import_python_object

                integrater_cls = import_python_object(
                    import_path=".".join((v["__module__"], v["__name__"])),
                    error_prefix="",
                    target_must_be="",
                    where_str="",
                ).object
                v = integrater_cls.from_dict(v)
            setattr(return_obj, k, v)
        return return_obj

    def get_project_info(self):
        return self._project_info

    def get_sweep_name(self):
        return self._sweep_name

    def get_integrater(self):
        return self._integrater

    def get_batches(self):
        return self._batches

    def set_batches(self, batches):
        logger.debug(
            "Setting batches for sweep %s: %i to %i"
            % (self.get_sweep_name(), batches[0], batches[1])
        )
        self._batches = batches

    def set_batch_offset(self, batch_offset):
        self._batch_offset = batch_offset

    def get_batch_offset(self):
        return self._batch_offset

    def get_batch_range(self):
        return min(self._batches), max(self._batches)

    def get_header(self):
        return self._integrater.get_header()

    def get_template(self):
        return self._integrater.get_template()

    def get_integrater_resolution(self):
        return self._integrater.get_integrater_high_resolution()

    def get_reflections(self):
        if self._reflections:
            return self._reflections
        else:
            return self._integrater.get_integrater_intensities()

    def set_reflections(self, reflections):
        self._reflections = reflections

    def set_experiments(self, experiments):
        self._experiments = experiments

    def get_experiments(self):
        return self._experiments


class SweepInformationHandler:
    def __init__(self, epoch_to_integrater):

        self._sweep_information = {}

        for epoch in epoch_to_integrater:
            self._sweep_information[epoch] = SweepInformation(
                epoch_to_integrater[epoch]
            )

        self._first = sorted(self._sweep_information)[0]

    def to_dict(self):
        obj = {}
        obj["__id__"] = "SweepInformationHandler"
        obj["_sweep_information"] = {
            k: v.to_dict() for k, v in self._sweep_information.items()
        }
        return obj

    @classmethod
    def from_dict(cls, obj):
        assert obj["__id__"] == "SweepInformationHandler"
        return_obj = cls.__new__(cls)
        return_obj._sweep_information = {
            k: SweepInformation.from_dict(v)
            for k, v in obj["_sweep_information"].items()
        }
        return_obj._first = sorted(return_obj._sweep_information)[0]
        return return_obj

    def get_epochs(self):
        return sorted(self._sweep_information)

    def remove_epoch(self, epoch):
        del self._sweep_information[epoch]
        self._first = sorted(self._sweep_information)[0]

    def get_sweep_information(self, epoch):
        return self._sweep_information[epoch]

    def get_project_info(self):
        si = self._sweep_information[self._first]
        pname, xname, dname = si.get_project_info()

        for e in self._sweep_information:
            si = self._sweep_information[e]

            assert si.get_project_info()[0] == pname
            assert si.get_project_info()[1] == xname

        return pname, xname


def mosflm_B_matrix(uc):
    parameters = uc.parameters()
    r_parameters = uc.reciprocal_parameters()

    a = parameters[:3]
    al = [math.pi * p / 180.0 for p in parameters[3:]]
    b = r_parameters[:3]
    be = [math.pi * p / 180.0 for p in r_parameters[3:]]

    mosflm_B = sqr(
        (
            b[0],
            b[1] * math.cos(be[2]),
            b[2] * math.cos(be[1]),
            0,
            b[1] * math.sin(be[2]),
            -b[2] * math.sin(be[1]) * math.cos(al[0]),
            0,
            0,
            1.0 / a[2],
        )
    )

    return mosflm_B


def get_umat_bmat_lattice_symmetry_from_mtz(mtz_file):
    """Get the U matrix and lattice symmetry derived from the unit cell
    constants from an MTZ file."""
    m = mtz.object(mtz_file)
    # assert first U matrix from batches is OK
    uc = m.crystals()[0].unit_cell()

    lattice_symm = lattice_symmetry_group(uc, max_delta=0.0)
    return tuple(m.batches()[0].umat()), mosflm_B_matrix(uc), lattice_symm
