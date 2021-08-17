# This provides the Scaler interface using XDS, pointless & CCP4 programs.
# This runs XSCALE, and feed sback to the XDSIntegrater and also runs a
# few other jiffys. Then Aimless for the merging...


import copy
import inspect
import logging
import os
import shutil

from xia2.Handlers.Citations import Citations
from xia2.Handlers.Files import FileHandler
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Syminfo import Syminfo
from xia2.lib.bits import auto_logfiler, is_mtz_file, transpose_loggraph
from xia2.lib.SymmetryLib import lattices_in_order
from xia2.Modules import MtzUtils
from xia2.Modules.Scaler.CommonScaler import CommonScaler as Scaler
from xia2.Modules.Scaler.tools import compute_average_unit_cell
from xia2.Modules.Scaler.XDSScalerHelpers import XDSScalerHelper
from xia2.Wrappers.CCP4.CCP4Factory import CCP4Factory
from xia2.Wrappers.XDS.XScaleR import XScaleR as _XScale

logger = logging.getLogger("xia2.Modules.Scaler.XDSScalerA")


class XDSScalerA(Scaler):
    """An implementation of the xia2 Scaler interface implemented with
    xds and xscale, possibly with some help from a couple of CCP4
    programs like pointless."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._sweep_information = {}

        self._reference = None

        # spacegroup and unit cell information - these will be
        # derived from an average of all of the sweeps which are
        # passed in

        self._xds_spacegroup = None
        self._factory = CCP4Factory()

        self._user_resolution_limits = {}

        # scaling correction choices - may be set one on the command line...

        # flags to keep track of the corrections we will be applying

        model = PhilIndex.params.xia2.settings.scale.model
        self._scalr_correct_absorption = "absorption" in model
        self._scalr_correct_modulation = "modulation" in model
        self._scalr_correct_decay = "decay" in model
        self._scalr_corrections = True

    def to_dict(self):
        obj = super().to_dict()
        attributes = inspect.getmembers(self, lambda m: not (inspect.isroutine(m)))
        for a in attributes:
            if a[0].startswith("_xds_"):
                obj[a[0]] = a[1]
            elif a[0] == "_sweep_information":
                d = copy.deepcopy(a[1])
                for i in d.values():
                    i["integrater"] = i["integrater"].to_dict()
                obj[a[0]] = d
        return obj

    @classmethod
    def from_dict(cls, obj):
        return_obj = super().from_dict(obj)
        for i in list(return_obj._sweep_information):
            d = return_obj._sweep_information[i]["integrater"]
            from libtbx.utils import import_python_object

            integrater_cls = import_python_object(
                import_path=".".join((d["__module__"], d["__name__"])),
                error_prefix="",
                target_must_be="",
                where_str="",
            ).object
            return_obj._sweep_information[i]["integrater"] = integrater_cls.from_dict(d)
            # expects epoch as number (or int?)
            if isinstance(i, str):
                return_obj._sweep_information[float(i)] = return_obj._sweep_information[
                    i
                ]
                del return_obj._sweep_information[i]
        return return_obj

    # This is overloaded from the Scaler interface...
    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)

    # program factory - this will provide configured wrappers
    # for the programs we need...

    def XScale(self):
        """Create a Xscale wrapper from _Xscale - set the working directory
        and log file stuff as a part of this..."""

        xscale = _XScale()

        if self._scalr_corrections:
            xscale.set_correct_decay(self._scalr_correct_decay)
            xscale.set_correct_absorption(self._scalr_correct_absorption)
            xscale.set_correct_modulation(self._scalr_correct_modulation)

        xscale.set_working_directory(self.get_working_directory())
        auto_logfiler(xscale)
        return xscale

    def _xdsin_to_batch_range(self, xdsin):
        for record in open(xdsin):
            if not record.startswith("!"):
                break
            if record.startswith("!DATA_RANGE"):
                return list(map(int, record.split()[-2:]))
        raise RuntimeError("BATCH range not found in %s" % xdsin)

    def _hklin_to_batch_range(self, hklin):
        from iotbx import mtz

        m = mtz.object(hklin)
        b = m.batches()
        return b[0].num(), b[-1].num()

    def _pointless_indexer_jiffy(self, hklin, refiner):
        """A jiffy to centralise the interactions between pointless
        (in the blue corner) and the Indexer, in the red corner."""

        # check to see if HKLIN is MTZ format, and if not, render it
        # so! no need - now pointless will accept input in XDS format.

        need_to_return = False

        pointless = self._factory.Pointless()

        batches = None

        if is_mtz_file(hklin):
            batches = self._hklin_to_batch_range(hklin)
            pointless.set_hklin(hklin)
        else:
            batches = self._xdsin_to_batch_range(hklin)
            pointless.set_xdsin(hklin)

        pointless.decide_pointgroup(batches=batches)

        rerun_pointless = False

        possible = pointless.get_possible_lattices()

        correct_lattice = None

        logger.debug("Possible lattices (pointless):")
        logger.debug(" ".join(possible))

        for lattice in possible:
            state = refiner.set_refiner_asserted_lattice(lattice)
            if state == refiner.LATTICE_CORRECT:
                logger.debug("Agreed lattice %s", lattice)
                correct_lattice = lattice
                break

            elif state == refiner.LATTICE_IMPOSSIBLE:
                logger.debug("Rejected lattice %s", lattice)

                rerun_pointless = True
                continue

            elif state == refiner.LATTICE_POSSIBLE:
                logger.debug("Accepted lattice %s ...", lattice)
                logger.debug("... will reprocess accordingly")

                need_to_return = True

                correct_lattice = lattice
                break

        if correct_lattice is None:
            correct_lattice = refiner.get_refiner_lattice()
            rerun_pointless = True

            logger.debug("No solution found: assuming lattice from refiner")

        if rerun_pointless:
            pointless.set_correct_lattice(correct_lattice)
            pointless.decide_pointgroup()

        logger.debug("Pointless analysis of %s", pointless.get_hklin())

        pointgroup = pointless.get_pointgroup()
        reindex_op = pointless.get_reindex_operator()

        logger.debug("Pointgroup: %s (%s)", pointgroup, reindex_op)

        return pointgroup, reindex_op, need_to_return

    def _scale_prepare(self):
        """Prepare the data for scaling - this will reindex it the
        reflections to the correct pointgroup and setting, for instance,
        and move the reflection files to the scale directory."""

        Citations.cite("xds")
        Citations.cite("ccp4")
        Citations.cite("pointless")

        # GATHER phase - get the reflection files together... note that
        # it is not necessary in here to keep the batch information as we
        # don't wish to rebatch the reflections prior to scaling.
        # FIXME need to think about what I will do about the radiation
        # damage analysis in here...

        self._sweep_information = {}

        # FIXME in here I want to record the batch number to
        # epoch mapping as per the CCP4 Scaler implementation.

        for epoch in self._scalr_integraters:
            intgr = self._scalr_integraters[epoch]
            pname, xname, dname = intgr.get_integrater_project_info()
            sname = intgr.get_integrater_sweep_name()
            self._sweep_information[epoch] = {
                "pname": pname,
                "xname": xname,
                "dname": dname,
                "integrater": intgr,
                "corrected_intensities": intgr.get_integrater_corrected_intensities(),
                "prepared_reflections": None,
                "scaled_reflections": None,
                "header": intgr.get_header(),
                "batches": intgr.get_integrater_batches(),
                "image_to_epoch": intgr.get_integrater_sweep().get_image_to_epoch(),
                "image_to_dose": {},
                "batch_offset": 0,
                "sname": sname,
            }

            # what are these used for?
            # pname / xname / dname - dataset identifiers
            # image to epoch / batch offset / batches - for RD analysis

            logger.debug("For EPOCH %s have:", str(epoch))
            logger.debug("ID = %s/%s/%s", pname, xname, dname)
            logger.debug("SWEEP = %s", intgr.get_integrater_sweep_name())

        # next work through all of the reflection files and make sure that
        # they are XDS_ASCII format...

        epochs = sorted(self._sweep_information)

        self._first_epoch = min(epochs)

        self._scalr_pname = self._sweep_information[epochs[0]]["pname"]
        self._scalr_xname = self._sweep_information[epochs[0]]["xname"]

        for epoch in epochs:
            intgr = self._scalr_integraters[epoch]
            pname = self._sweep_information[epoch]["pname"]
            xname = self._sweep_information[epoch]["xname"]
            dname = self._sweep_information[epoch]["dname"]
            sname = self._sweep_information[epoch]["sname"]
            if self._scalr_pname != pname:
                raise RuntimeError("all data must have a common project name")
            if self._scalr_xname != xname:
                raise RuntimeError("all data for scaling must come from one crystal")

            xsh = XDSScalerHelper()
            xsh.set_working_directory(self.get_working_directory())
            hklin = self._sweep_information[epoch]["corrected_intensities"]
            hklout = os.path.join(
                self.get_working_directory(),
                f"{pname}_{xname}_{dname}_{sname}_CORRECTED.HKL",
            )
            sweep = intgr.get_integrater_sweep()
            if sweep.get_frames_to_process() is not None:
                offset = intgr.get_frame_offset()
                # print "offset: %d" %offset
                start, end = sweep.get_frames_to_process()
                start -= offset
                end -= offset
                # end += 1 ????
                # print "limiting batches: %d-%d" %(start, end)
                xsh.limit_batches(hklin, hklout, start, end)
                self._sweep_information[epoch]["corrected_intensities"] = hklout

        # if there is more than one sweep then compare the lattices
        # and eliminate all but the lowest symmetry examples if
        # there are more than one...

        # -------------------------------------------------
        # Ensure that the integration lattices are the same
        # -------------------------------------------------

        need_to_return = False

        if len(self._sweep_information) > 1:
            lattices = set()

            # FIXME run this stuff in parallel as well...

            for epoch in self._sweep_information:
                intgr = self._sweep_information[epoch]["integrater"]
                hklin = self._sweep_information[epoch]["corrected_intensities"]
                refiner = intgr.get_integrater_refiner()

                if self._scalr_input_pointgroup:
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = "h,k,l"
                    ntr = False

                else:
                    pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                        hklin, refiner
                    )

                    logger.debug("X1698: %s: %s", pointgroup, reindex_op)

                lattice = Syminfo.get_lattice(pointgroup)
                lattices.add(lattice)

                if ntr:
                    # if we need to return, we should logically reset
                    # any reindexing operator right? right here all
                    # we are talking about is the correctness of
                    # individual pointgroups?? Bug # 3373

                    reindex_op = "h,k,l"
                    # actually, should this not be done "by magic"
                    # when a new pointgroup is assigned in the
                    # pointless indexer jiffy above?!

                    intgr.set_integrater_reindex_operator(reindex_op, compose=False)

                    need_to_return = True

            # bug # 2433 - need to ensure that all of the lattice
            # conclusions were the same...

            if len(lattices) > 1:
                ordered_lattices = []
                for l in lattices_in_order():
                    if l in lattices:
                        ordered_lattices.append(l)

                correct_lattice = ordered_lattices[0]
                logger.debug("Correct lattice asserted to be %s", correct_lattice)

                # transfer this information back to the indexers
                for epoch in self._sweep_information:
                    integrater = self._sweep_information[epoch]["integrater"]
                    refiner = integrater.get_integrater_refiner()
                    sname = integrater.get_integrater_sweep_name()

                    if not refiner:
                        continue

                    state = refiner.set_refiner_asserted_lattice(correct_lattice)
                    if state == refiner.LATTICE_CORRECT:
                        logger.debug(
                            "Lattice %s ok for sweep %s", correct_lattice, sname
                        )
                    elif state == refiner.LATTICE_IMPOSSIBLE:
                        raise RuntimeError(
                            f"Lattice {correct_lattice} impossible for {sname}"
                        )
                    elif state == refiner.LATTICE_POSSIBLE:
                        logger.debug(
                            "Lattice %s assigned for sweep %s", correct_lattice, sname
                        )
                        need_to_return = True

        # if one or more of them was not in the lowest lattice,
        # need to return here to allow reprocessing

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        # next if there is more than one sweep then generate
        # a merged reference reflection file to check that the
        # setting for all reflection files is the same...

        # if we get to here then all data was processed with the same
        # lattice

        # ----------------------------------------------------------
        # next ensure that all sweeps are set in the correct setting
        # ----------------------------------------------------------

        if self.get_scaler_reference_reflection_file():
            self._reference = self.get_scaler_reference_reflection_file()
            logger.debug("Using HKLREF %s", self._reference)

            self._xds_spacegroup = MtzUtils.space_group_number_from_mtz(self._reference)
            logger.debug("Spacegroup %d", self._xds_spacegroup)

        elif PhilIndex.params.xia2.settings.scale.reference_reflection_file:
            self._reference = (
                PhilIndex.params.xia2.settings.scale.reference_reflection_file
            )

            logger.debug("Using HKLREF %s", self._reference)

            self._xds_spacegroup = MtzUtils.space_group_number_from_mtz(self._reference)
            logger.debug("Spacegroup %d", self._xds_spacegroup)

        params = PhilIndex.params
        use_brehm_diederichs = params.xia2.settings.use_brehm_diederichs
        if len(self._sweep_information) > 1 and use_brehm_diederichs:
            brehm_diederichs_files_in = []
            for sweep_information in self._sweep_information.values():
                intgr = sweep_information["integrater"]
                hklin = sweep_information["corrected_intensities"]
                refiner = intgr.get_integrater_refiner()

                # in here need to consider what to do if the user has
                # assigned the pointgroup on the command line ...

                if not self._scalr_input_pointgroup:
                    pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                        hklin, refiner
                    )

                    if ntr:
                        # Bug # 3373

                        logger.debug("Reindex to standard (PIJ): %s", reindex_op)

                        intgr.set_integrater_reindex_operator(reindex_op, compose=False)
                        reindex_op = "h,k,l"
                        need_to_return = True

                else:
                    # 27/FEB/08 to support user assignment of pointgroups

                    logger.debug(
                        "Using input pointgroup: %s", self._scalr_input_pointgroup
                    )
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = "h,k,l"

                intgr.set_integrater_reindex_operator(reindex_op)
                intgr.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup)
                )
                sweep_information[
                    "corrected_intensities"
                ] = intgr.get_integrater_corrected_intensities()

                # convert the XDS_ASCII for this sweep to mtz - on the next
                # get this should be in the correct setting...

                dname = sweep_information["dname"]
                sname = intgr.get_integrater_sweep_name()
                hklin = sweep_information["corrected_intensities"]
                hklout = os.path.join(
                    self.get_working_directory(), f"{dname}_{sname}.mtz"
                )

                FileHandler.record_temporary_file(hklout)

                # now use pointless to make this conversion

                pointless = self._factory.Pointless()
                pointless.set_xdsin(hklin)
                pointless.set_hklout(hklout)
                pointless.xds_to_mtz()
                brehm_diederichs_files_in.append(hklout)

            # now run cctbx.brehm_diederichs to figure out the indexing hand for
            # each sweep
            from xia2.Wrappers.Cctbx.BrehmDiederichs import BrehmDiederichs

            brehm_diederichs = BrehmDiederichs()
            brehm_diederichs.set_working_directory(self.get_working_directory())
            auto_logfiler(brehm_diederichs)
            brehm_diederichs.set_input_filenames(brehm_diederichs_files_in)
            # 1 or 3? 1 seems to work better?
            brehm_diederichs.set_asymmetric(1)
            brehm_diederichs.run()

            for sweep_information in self._sweep_information.values():
                intgr = sweep_information["integrater"]

                dname = sweep_information["dname"]
                sname = intgr.get_integrater_sweep_name()

                # apply the reindexing operator
                intgr.set_integrater_reindex_operator(reindex_op)

                # and copy the reflection file to the local directory
                hklin = sweep_information["corrected_intensities"]
                hklout = os.path.join(
                    self.get_working_directory(), f"{dname}_{sname}.HKL"
                )

                logger.debug("Copying %s to %s", hklin, hklout)
                shutil.copyfile(hklin, hklout)

                # record just the local file name...
                sweep_information["prepared_reflections"] = os.path.split(hklout)[-1]

        elif len(self._sweep_information) > 1 and not self._reference:
            # need to generate a reference reflection file - generate this
            # from the reflections in self._first_epoch
            #
            # FIXME this should really use the Brehm and Diederichs method
            # if you have lots of little sweeps...

            intgr = self._sweep_information[self._first_epoch]["integrater"]

            hklin = self._sweep_information[epoch]["corrected_intensities"]
            refiner = intgr.get_integrater_refiner()

            if self._scalr_input_pointgroup:
                logger.debug("Using input pointgroup: %s", self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup
                ntr = False
                reindex_op = "h,k,l"

            else:
                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, refiner
                )

                logger.debug("X1698: %s: %s", pointgroup, reindex_op)

            if ntr:
                # Bug # 3373

                intgr.set_integrater_reindex_operator(reindex_op, compose=False)
                reindex_op = "h,k,l"
                need_to_return = True

            self._xds_spacegroup = Syminfo.spacegroup_name_to_number(pointgroup)

            # next pass this reindexing operator back to the source
            # of the reflections

            intgr.set_integrater_reindex_operator(reindex_op)
            intgr.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup)
            )
            self._sweep_information[epoch][
                "corrected_intensities"
            ] = intgr.get_integrater_corrected_intensities()

            hklin = self._sweep_information[epoch]["corrected_intensities"]

            hklout = os.path.join(
                self.get_working_directory(), "xds-pointgroup-reference-unsorted.mtz"
            )
            FileHandler.record_temporary_file(hklout)

            # now use pointless to handle this conversion

            pointless = self._factory.Pointless()
            pointless.set_xdsin(hklin)
            pointless.set_hklout(hklout)
            pointless.xds_to_mtz()

            self._reference = hklout

        if self._reference:

            from xia2.Driver.DriverFactory import DriverFactory

            def run_one_sweep(args):
                sweep_information = args[0]
                #  pointless_indexer_jiffy = args[1]
                #  factory = args[2]
                job_type = args[3]

                if job_type:
                    DriverFactory.set_driver_type(job_type)

                intgr = sweep_information["integrater"]
                hklin = sweep_information["corrected_intensities"]
                refiner = intgr.get_integrater_refiner()

                # in here need to consider what to do if the user has
                # assigned the pointgroup on the command line ...

                if not self._scalr_input_pointgroup:
                    pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                        hklin, refiner
                    )

                    if ntr:
                        # Bug # 3373

                        logger.debug("Reindex to standard (PIJ): %s", reindex_op)

                        intgr.set_integrater_reindex_operator(reindex_op, compose=False)
                        reindex_op = "h,k,l"
                        # need_to_return = True ## we are in a local function so this has no effect

                else:
                    # 27/FEB/08 to support user assignment of pointgroups

                    logger.debug(
                        "Using input pointgroup: %s", self._scalr_input_pointgroup
                    )
                    pointgroup = self._scalr_input_pointgroup
                    reindex_op = "h,k,l"

                intgr.set_integrater_reindex_operator(reindex_op)
                intgr.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup)
                )
                sweep_information[
                    "corrected_intensities"
                ] = intgr.get_integrater_corrected_intensities()

                # convert the XDS_ASCII for this sweep to mtz - on the next
                # get this should be in the correct setting...

                hklin = sweep_information["corrected_intensities"]

                # now use pointless to make this conversion

                # try with no conversion?!

                pointless = self._factory.Pointless()
                pointless.set_xdsin(hklin)
                hklout = os.path.join(
                    self.get_working_directory(),
                    "%d_xds-pointgroup-unsorted.mtz" % pointless.get_xpid(),
                )
                FileHandler.record_temporary_file(hklout)
                pointless.set_hklout(hklout)
                pointless.xds_to_mtz()

                pointless = self._factory.Pointless()
                pointless.set_hklin(hklout)
                pointless.set_hklref(self._reference)
                batches = self._hklin_to_batch_range(hklout)
                pointless.decide_pointgroup(batches=batches)

                pointgroup = pointless.get_pointgroup()
                reindex_op = pointless.get_reindex_operator()

                # for debugging print out the reindexing operations and
                # what have you...

                logger.debug("Reindex to standard: %s", reindex_op)

                # this should send back enough information that this
                # is in the correct pointgroup (from the call above) and
                # also in the correct setting, from the interaction
                # with the reference set... - though I guess that the
                # spacegroup number should not have changed, right?

                # set the reindex operation afterwards... though if the
                # spacegroup number is the same this should make no
                # difference, right?!

                intgr.set_integrater_spacegroup_number(
                    Syminfo.spacegroup_name_to_number(pointgroup)
                )
                intgr.set_integrater_reindex_operator(reindex_op)
                sweep_information[
                    "corrected_intensities"
                ] = intgr.get_integrater_corrected_intensities()

                # and copy the reflection file to the local directory

                dname = sweep_information["dname"]
                sname = intgr.get_integrater_sweep_name()
                hklin = sweep_information["corrected_intensities"]
                hklout = os.path.join(
                    self.get_working_directory(), f"{dname}_{sname}.HKL"
                )

                logger.debug("Copying %s to %s", hklin, hklout)
                shutil.copyfile(hklin, hklout)

                # record just the local file name...
                sweep_information["prepared_reflections"] = os.path.split(hklout)[-1]
                return sweep_information

            from libtbx import easy_mp

            params = PhilIndex.get_python_object()
            mp_params = params.xia2.settings.multiprocessing
            njob = mp_params.njob

            if njob > 1:
                # cache drivertype
                drivertype = DriverFactory.get_driver_type()

                args = [
                    (
                        sweep_information,
                        self._pointless_indexer_jiffy,
                        self._factory,
                        mp_params.type,
                    )
                    for sweep_information in self._sweep_information.values()
                ]
                results_list = easy_mp.parallel_map(
                    run_one_sweep,
                    args,
                    params=None,
                    processes=njob,
                    method="threading",
                    asynchronous=True,
                    callback=None,
                    preserve_order=True,
                    preserve_exception_message=True,
                )

                # restore drivertype
                DriverFactory.set_driver_type(drivertype)

                # results should be given back in the same order
                for i, epoch in enumerate(self._sweep_information):
                    self._sweep_information[epoch] = results_list[i]

            else:
                for epoch in self._sweep_information:
                    self._sweep_information[epoch] = run_one_sweep(
                        (
                            self._sweep_information[epoch],
                            self._pointless_indexer_jiffy,
                            self._factory,
                            None,
                        )
                    )

        else:
            # convert the XDS_ASCII for this sweep to mtz

            epoch = self._first_epoch
            intgr = self._sweep_information[epoch]["integrater"]
            refiner = intgr.get_integrater_refiner()
            sname = intgr.get_integrater_sweep_name()

            hklout = os.path.join(
                self.get_working_directory(), "%s-pointless.mtz" % sname
            )
            FileHandler.record_temporary_file(hklout)

            pointless = self._factory.Pointless()
            pointless.set_xdsin(self._sweep_information[epoch]["corrected_intensities"])
            pointless.set_hklout(hklout)
            pointless.xds_to_mtz()

            # run it through pointless interacting with the
            # Indexer which belongs to this sweep

            hklin = hklout

            if self._scalr_input_pointgroup:
                logger.debug("Using input pointgroup: %s", self._scalr_input_pointgroup)
                pointgroup = self._scalr_input_pointgroup
                ntr = False
                reindex_op = "h,k,l"

            else:
                pointgroup, reindex_op, ntr = self._pointless_indexer_jiffy(
                    hklin, refiner
                )

            if ntr:
                # if we need to return, we should logically reset
                # any reindexing operator right? right here all
                # we are talking about is the correctness of
                # individual pointgroups?? Bug # 3373

                reindex_op = "h,k,l"
                intgr.set_integrater_reindex_operator(reindex_op, compose=False)

                need_to_return = True

            self._xds_spacegroup = Syminfo.spacegroup_name_to_number(pointgroup)

            # next pass this reindexing operator back to the source
            # of the reflections

            intgr.set_integrater_reindex_operator(reindex_op)
            intgr.set_integrater_spacegroup_number(
                Syminfo.spacegroup_name_to_number(pointgroup)
            )
            self._sweep_information[epoch][
                "corrected_intensities"
            ] = intgr.get_integrater_corrected_intensities()

            hklin = self._sweep_information[epoch]["corrected_intensities"]
            dname = self._sweep_information[epoch]["dname"]
            hklout = os.path.join(self.get_working_directory(), f"{dname}_{sname}.HKL")

            # and copy the reflection file to the local
            # directory

            logger.debug("Copying %s to %s", hklin, hklout)
            shutil.copyfile(hklin, hklout)

            # record just the local file name...
            self._sweep_information[epoch]["prepared_reflections"] = os.path.split(
                hklout
            )[-1]

        if need_to_return:
            self.set_scaler_done(False)
            self.set_scaler_prepare_done(False)
            return

        unit_cell_list = []

        for sweep_information in self._sweep_information.values():
            integrater = sweep_information["integrater"]
            cell = integrater.get_integrater_cell()
            n_ref = integrater.get_integrater_n_ref()

            logger.debug(
                "Cell for %s: %.2f %.2f %.2f %.2f %.2f %.2f",
                integrater.get_integrater_sweep_name(),
                cell[0],
                cell[1],
                cell[2],
                cell[3],
                cell[4],
                cell[5],
            )
            logger.debug("=> %d reflections", n_ref)

            unit_cell_list.append((cell, n_ref))

        self._scalr_cell = compute_average_unit_cell(unit_cell_list)

        self._scalr_resolution_limits = {}

        logger.debug(
            "Determined unit cell: %.2f %.2f %.2f %.2f %.2f %.2f"
            % tuple(self._scalr_cell)
        )

        if os.path.exists(os.path.join(self.get_working_directory(), "REMOVE.HKL")):
            os.remove(os.path.join(self.get_working_directory(), "REMOVE.HKL"))

            logger.debug("Deleting REMOVE.HKL at end of scale prepare.")

    def _scale(self):
        """Actually scale all of the data together."""

        from xia2.Handlers.Environment import debug_memory_usage

        debug_memory_usage()

        epochs = sorted(self._sweep_information.keys())

        xscale = self.XScale()

        xscale.set_spacegroup_number(self._xds_spacegroup)
        xscale.set_cell(self._scalr_cell)

        logger.debug(
            "Set CELL: %.2f %.2f %.2f %.2f %.2f %.2f" % tuple(self._scalr_cell)
        )
        logger.debug("Set SPACEGROUP_NUMBER: %d", self._xds_spacegroup)

        logger.debug("Gathering measurements for scaling")

        for epoch in epochs:
            # get the prepared reflections
            reflections = self._sweep_information[epoch]["prepared_reflections"]

            # and the get wavelength that this belongs to
            dname = self._sweep_information[epoch]["dname"]
            sname = self._sweep_information[epoch]["sname"]

            # and the resolution range for the reflections
            intgr = self._sweep_information[epoch]["integrater"]
            logger.debug("Epoch: %d", epoch)
            logger.debug("HKL: %s (%s/%s)", reflections, dname, sname)

            resolution_low = intgr.get_integrater_low_resolution()
            resolution_high, _ = self._scalr_resolution_limits.get(
                (dname, sname), (0.0, None)
            )

            resolution = (resolution_high, resolution_low)

            xscale.add_reflection_file(reflections, dname, resolution)

        # set the global properties of the sample
        xscale.set_crystal(self._scalr_xname)
        xscale.set_anomalous(self._scalr_anomalous)

        debug_memory_usage()
        xscale.run()

        scale_factor = xscale.get_scale_factor()

        logger.debug("XSCALE scale factor found to be: %e", scale_factor)

        # record the log file

        pname = self._scalr_pname
        xname = self._scalr_xname

        FileHandler.record_log_file(
            f"{pname} {xname} XSCALE",
            os.path.join(self.get_working_directory(), "XSCALE.LP"),
        )

        # check for outlier reflections and if a number are found
        # then iterate (that is, rerun XSCALE, rejecting these outliers)

        if (
            not PhilIndex.params.dials.fast_mode
            and not PhilIndex.params.xds.keep_outliers
            and self.get_scaler_resolution_limits()
        ):
            xscale_remove = xscale.get_remove()
            if xscale_remove:
                current_remove = set()
                final_remove = []

                # first ensure that there are no duplicate entries...
                if os.path.exists(
                    os.path.join(self.get_working_directory(), "REMOVE.HKL")
                ):
                    for line in open(
                        os.path.join(self.get_working_directory(), "REMOVE.HKL")
                    ).readlines():
                        h, k, l = list(map(int, line.split()[:3]))
                        z = float(line.split()[3])
                        current_remove.add((h, k, l, z))

                    for c in xscale_remove:
                        if c in current_remove:
                            continue
                        final_remove.append(c)

                    logger.debug(
                        "%d alien reflections are already removed",
                        len(xscale_remove) - len(final_remove),
                    )

                else:
                    # we want to remove all of the new dodgy reflections
                    final_remove = xscale_remove

                remove_hkl = open(
                    os.path.join(self.get_working_directory(), "REMOVE.HKL"), "w"
                )

                z_min = PhilIndex.params.xds.z_min
                rejected = 0

                # write in the old reflections
                for remove in current_remove:
                    z = remove[3]
                    if z >= z_min:
                        remove_hkl.write("%d %d %d %f\n" % remove)
                    else:
                        rejected += 1
                logger.debug(
                    "Wrote %d old reflections to REMOVE.HKL",
                    len(current_remove) - rejected,
                )
                logger.debug("Rejected %d as z < %f", rejected, z_min)

                # and the new reflections
                rejected = 0
                used = 0
                for remove in final_remove:
                    z = remove[3]
                    if z >= z_min:
                        used += 1
                        remove_hkl.write("%d %d %d %f\n" % remove)
                    else:
                        rejected += 1
                logger.debug(
                    "Wrote %d new reflections to REMOVE.HKL",
                    len(final_remove) - rejected,
                )
                logger.debug("Rejected %d as z < %f", rejected, z_min)

                remove_hkl.close()

                # we want to rerun the finishing step so...
                # unless we have added no new reflections
                if used:
                    self.set_scaler_done(False)

        if not self.get_scaler_done():
            logger.info(
                "Excluding outlier reflections Z > %.2f", PhilIndex.params.xds.z_min
            )
            return

        debug_memory_usage()

        # now get the reflection files out and merge them with aimless

        output_files = xscale.get_output_reflection_files()

        for epoch, input in self._sweep_information.items():
            intgr = input["integrater"]
            rkey = input["dname"], input["sname"]

            if intgr.get_integrater_user_resolution():
                dmin = intgr.get_integrater_high_resolution()

                if rkey not in self._user_resolution_limits:
                    # self._scalr_resolution_limits[rkey] = (dmin, None)
                    self._user_resolution_limits[rkey] = dmin
                elif dmin < self._user_resolution_limits[rkey]:
                    # self._scalr_resolution_limits[rkey] = (dmin, None)
                    self._user_resolution_limits[rkey] = dmin

        self._scalr_scaled_refl_files = {}
        self._scalr_statistics = {}

        project_info = {}
        for epoch in self._sweep_information:
            pname = self._scalr_pname
            xname = self._scalr_xname
            dname = self._sweep_information[epoch]["dname"]
            reflections = os.path.split(
                self._sweep_information[epoch]["prepared_reflections"]
            )[-1]
            project_info[reflections] = (pname, xname, dname)
            self._sweep_information[epoch]["scaled_reflections"] = None

        debug_memory_usage()

        for wavelength, hklin in output_files.items():
            xsh = XDSScalerHelper()
            xsh.set_working_directory(self.get_working_directory())

            ref = xsh.split_and_convert_xscale_output(
                hklin, "SCALED_", project_info, 1.0 / scale_factor
            )

            for hklout in ref:
                for epoch in self._sweep_information:
                    if (
                        os.path.split(
                            self._sweep_information[epoch]["prepared_reflections"]
                        )[-1]
                        == os.path.split(hklout)[-1]
                    ):
                        if (
                            self._sweep_information[epoch]["scaled_reflections"]
                            is not None
                        ):
                            raise RuntimeError("duplicate entries")
                        self._sweep_information[epoch]["scaled_reflections"] = ref[
                            hklout
                        ]

            del xsh

        debug_memory_usage()

        for epoch in self._sweep_information:
            hklin = self._sweep_information[epoch]["scaled_reflections"]
            dname = self._sweep_information[epoch]["dname"]
            sname = self._sweep_information[epoch]["sname"]

            hkl_copy = os.path.join(
                self.get_working_directory(), "R_%s" % os.path.split(hklin)[-1]
            )

            if not os.path.exists(hkl_copy):
                shutil.copyfile(hklin, hkl_copy)

            if (dname, sname) in self._scalr_resolution_limits:
                continue

            # let's properly listen to the user's resolution limit needs...
            if self._user_resolution_limits.get((dname, sname), False):
                resolution = self._user_resolution_limits[(dname, sname)]
                reasoning = "user provided"

            else:
                if PhilIndex.params.xia2.settings.resolution.keep_all_reflections:
                    try:
                        resolution = intgr.get_detector().get_max_resolution(
                            intgr.get_beam_obj().get_s0()
                        )
                        reasoning = "detector limits"
                        logger.debug("keep_all_reflections set, using detector limits")
                    except Exception:
                        resolution, reasoning = self._estimate_resolution_limit(hklin)
                else:
                    resolution, reasoning = self._estimate_resolution_limit(hklin)

            reasoning_str = ""
            if reasoning:
                reasoning_str = " (%s)" % reasoning
            logger.info(
                "Resolution for sweep %s/%s: %.2f%s",
                dname,
                sname,
                resolution,
                reasoning_str,
            )

            if (dname, sname) not in self._scalr_resolution_limits:
                self._scalr_resolution_limits[(dname, sname)] = (resolution, None)
                self.set_scaler_done(False)
            else:
                if resolution < self._scalr_resolution_limits[(dname, sname)][0]:
                    self._scalr_resolution_limits[(dname, sname)] = (resolution, None)
                    self.set_scaler_done(False)

        debug_memory_usage()

        if not self.get_scaler_done():
            logger.debug("Returning as scaling not finished...")
            return

        self._sort_together_data_xds()

        highest_resolution = min(
            limit for limit, _ in self._scalr_resolution_limits.values()
        )

        self._scalr_highest_resolution = highest_resolution

        logger.debug("Scaler highest resolution set to %5.2f", highest_resolution)

        if not self.get_scaler_done():
            logger.debug("Returning as scaling not finished...")
            return

        sdadd_full = 0.0
        sdb_full = 0.0

        # ---------- FINAL MERGING ----------

        sc = self._factory.Aimless()

        FileHandler.record_log_file(
            f"{self._scalr_pname} {self._scalr_xname} aimless", sc.get_log_file()
        )

        sc.set_resolution(highest_resolution)
        sc.set_hklin(self._prepared_reflections)
        sc.set_new_scales_file("%s_final.scales" % self._scalr_xname)

        if sdadd_full == 0.0 and sdb_full == 0.0:
            pass
        else:
            sc.add_sd_correction("both", 1.0, sdadd_full, sdb_full)

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input["batches"]), max(input["batches"]))

            rkey = input["dname"], input["sname"]
            run_resolution_limit, _ = self._scalr_resolution_limits[rkey]

            sc.add_run(
                start,
                end,
                exclude=False,
                resolution=run_resolution_limit,
                name=input["sname"],
            )

        sc.set_hklout(
            os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_scaled.mtz",
            )
        )

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.multi_merge()

        FileHandler.record_xml_file(
            f"{self._scalr_pname} {self._scalr_xname} aimless", sc.get_xmlout()
        )
        data = sc.get_summary()

        loggraph = sc.parse_ccp4_loggraph()
        standard_deviation_info = {}
        resolution_info = {}
        batch_info = {}

        for key in loggraph:
            if "standard deviation v. Intensity" in key:
                dataset = key.split(",")[-1].strip()
                standard_deviation_info[dataset] = transpose_loggraph(loggraph[key])

            if "Analysis against resolution" in key:
                dataset = key.split(",")[-1].strip()
                resolution_info[dataset] = transpose_loggraph(loggraph[key])

            if "Analysis against Batch" in key:
                dataset = key.split(",")[-1].strip()
                batch_info[dataset] = transpose_loggraph(loggraph[key])

        # finally put all of the results "somewhere useful"

        self._scalr_statistics = data

        self._scalr_scaled_refl_files = copy.deepcopy(sc.get_scaled_reflection_files())

        self._scalr_scaled_reflection_files = {}

        # also output the unmerged scalepack format files...

        sc = self._factory.Aimless()
        sc.set_resolution(highest_resolution)
        sc.set_hklin(self._prepared_reflections)
        sc.set_scalepack()

        for epoch in epochs:
            input = self._sweep_information[epoch]
            start, end = (min(input["batches"]), max(input["batches"]))

            rkey = input["dname"], input["sname"]
            run_resolution_limit, _ = self._scalr_resolution_limits[rkey]

            sc.add_run(
                start,
                end,
                exclude=False,
                resolution=run_resolution_limit,
                name=input["sname"],
            )

        sc.set_hklout(
            os.path.join(
                self.get_working_directory(),
                f"{self._scalr_pname}_{self._scalr_xname}_scaled.mtz",
            )
        )

        if self.get_scaler_anomalous():
            sc.set_anomalous()

        sc.multi_merge()

        self._scalr_scaled_reflection_files["sca_unmerged"] = {}
        self._scalr_scaled_reflection_files["mtz_unmerged"] = {}

        for dataset, hklout in sc.get_scaled_reflection_files().items():
            # then mark the scalepack files for copying...

            scalepack = os.path.join(
                os.path.split(hklout)[0],
                os.path.split(hklout)[1]
                .replace("_scaled", "_scaled_unmerged")
                .replace(".mtz", ".sca"),
            )
            self._scalr_scaled_reflection_files["sca_unmerged"][dataset] = scalepack
            FileHandler.record_data_file(scalepack)
            mtz_unmerged = os.path.splitext(scalepack)[0] + ".mtz"
            self._scalr_scaled_reflection_files["mtz_unmerged"][dataset] = mtz_unmerged
            FileHandler.record_data_file(mtz_unmerged)

        if PhilIndex.params.xia2.settings.merging_statistics.source == "cctbx":
            for key in self._scalr_scaled_refl_files:
                stats = self._compute_scaler_statistics(
                    self._scalr_scaled_reflection_files["mtz_unmerged"][key], wave=key
                )
                self._scalr_statistics[
                    (self._scalr_pname, self._scalr_xname, key)
                ] = stats

        # convert reflection files to .sca format - use mtz2various for this

        self._scalr_scaled_reflection_files["sca"] = {}
        self._scalr_scaled_reflection_files["hkl"] = {}

        for key, f in self._scalr_scaled_refl_files.items():
            scaout = "%s.sca" % f[:-4]

            self._scalr_scaled_reflection_files["sca"][key] = scaout
            FileHandler.record_data_file(scaout)

            if PhilIndex.params.xia2.settings.small_molecule:
                hklout = "%s.hkl" % f[:-4]

                m2v = self._factory.Mtz2various()
                m2v.set_hklin(f)
                m2v.set_hklout(hklout)
                m2v.convert_shelx()

                self._scalr_scaled_reflection_files["hkl"][key] = hklout
                FileHandler.record_data_file(hklout)

    def get_batch_to_dose(self):
        batch_to_dose = {}
        epoch_to_dose = {}
        for xsample in self.get_scaler_xcrystal()._samples.values():
            epoch_to_dose.update(xsample.get_epoch_to_dose())
        for e0, si in self._sweep_information.items():
            batch_offset = si["batch_offset"]
            frame_offset = si["integrater"].get_frame_offset()
            printed = False
            for b in range(si["batches"][0], si["batches"][1] + 1):
                if epoch_to_dose:
                    # see https://github.com/xia2/xia2/issues/90
                    if (
                        si["image_to_epoch"][b + frame_offset - batch_offset]
                        in epoch_to_dose
                    ):
                        if not printed:
                            logger.debug("Epoch found; all good")
                            printed = True
                        batch_to_dose[b] = epoch_to_dose[
                            si["image_to_epoch"][b + frame_offset - batch_offset]
                        ]
                    else:
                        if not printed:
                            logger.debug("Epoch not found; using offset %f", e0)
                            printed = True
                        batch_to_dose[b] = epoch_to_dose[
                            si["image_to_epoch"][b + frame_offset - batch_offset] - e0
                        ]
                else:
                    # backwards compatibility 2015-12-11
                    batch_to_dose[b] = b
        return batch_to_dose
