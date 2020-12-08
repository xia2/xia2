import logging
import os

from xia2.Decorators.DecoratorFactory import DecoratorFactory
from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Phil import PhilIndex
from xia2.Wrappers.CCP4.AimlessHelpers import parse_aimless_xml

logger = logging.getLogger("xia2.Wrappers.CCP4.Aimless")


def Aimless(DriverType=None, absorption_correction=None, decay_correction=None):
    """A factory for AimlessWrapper classes."""

    DriverInstance = DriverFactory.Driver(DriverType)
    CCP4DriverInstance = DecoratorFactory.Decorate(DriverInstance, "ccp4")

    class AimlessWrapper(CCP4DriverInstance.__class__):
        """A wrapper for Aimless, using the CCP4-ified Driver."""

        def __init__(self):
            # generic things
            CCP4DriverInstance.__class__.__init__(self)

            self.set_executable(os.path.join(os.environ.get("CBIN", ""), "aimless"))

            if not os.path.exists(self.get_executable()):
                raise RuntimeError("aimless binary not found")

            self.start()
            self.close_wait()

            version = None

            for record in self.get_all_output():
                if "##" in record and "AIMLESS" in record:
                    version = record.split()[5]

            if not version:
                raise RuntimeError("version not found")

            logger.debug("Using version: %s" % version)

            # clear all the header junk
            self.reset()

            # input and output files
            self._scalepack = False
            self._chef_unmerged = False
            self._unmerged_reflections = None
            self._xmlout = None

            # scaling parameters
            self._resolution = None

            # scales file for recycling
            self._scales_file = None

            # this defaults to SCALES - and is useful for when we
            # want to refine the SD parameters because we can
            # recycle the scale factors through the above interface
            self._new_scales_file = None

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

            self._mode = "rotation"

            # these are only relevant for 'rotation' mode scaling
            self._spacing = 5
            self._cycles = 100
            self._brotation = None
            self._bfactor_tie = None
            self._surface_tie = None
            self._surface_link = True

            self._intensities = "combine"

            self._project_crystal_dataset = {}
            self._runs = []

            # for adding data on merge - one dname
            self._pname = None
            self._xname = None
            self._dname = None

        # getter and setter methods

        def set_project_info(self, pname, xname, dname):
            """Only use this for the merge() method."""
            self._pname = pname
            self._xname = xname
            self._dname = dname

        def add_run(
            self,
            start,
            end,
            pname=None,
            xname=None,
            dname=None,
            exclude=False,
            resolution=0.0,
            name=None,
        ):
            """Add another run to the run table, optionally not including
            it in the scaling - for solution to bug 2229."""

            self._runs.append(
                (start, end, pname, xname, dname, exclude, resolution, name)
            )

        def set_scalepack(self, scalepack=True):
            self._scalepack = scalepack

        def set_chef_unmerged(self, chef_unmerged=True):
            """Output the measurements in the form suitable for
            input to chef, that is with SDCORRECTION 1 0 0 and
            in unmerged MTZ format."""

            self._chef_unmerged = chef_unmerged

        def set_resolution(self, resolution):
            """Set the resolution limit for the scaling -
            default is to include all reflections."""

            self._resolution = resolution

        def get_xmlout(self):
            return self._xmlout

        def set_scales_file(self, scales_file):
            """Set the file containing all of the scales required for
            this run. Used when fiddling the error parameters or
            obtaining stats to different resolutions. See also
            set_new_scales_file(). This will switch on ONLYMERGE RESTORE."""

            # bodge: take this file and make a temporary local copy which will
            # have the Nparameters token spaced from the number which follows
            # it....

            tmp_scales_file = os.path.join(
                self.get_working_directory(), "%s.tmp" % os.path.split(scales_file)[-1]
            )

            open(tmp_scales_file, "w").write(
                open(os.path.join(self.get_working_directory(), scales_file))
                .read()
                .replace("Nparameters", "Nparameters ")
            )

            self._scales_file = tmp_scales_file

        def set_new_scales_file(self, new_scales_file):
            """Set the file to which the scales will be written. This
            will allow reusing through the above interface."""

            self._new_scales_file = new_scales_file

        def get_new_scales_file(self):
            """Get the file to which the scales have been written."""
            if self._new_scales_file:
                if not os.path.isfile(
                    os.path.join(self.get_working_directory(), self._new_scales_file)
                ):
                    logger.info(
                        "Aimless did not scale the data, see log file for more details:\n  %s",
                        self.get_log_file(),
                    )
                    raise RuntimeError("data not scaled")
            return os.path.join(self.get_working_directory(), self._new_scales_file)

        def set_bfactor(self, bfactor=True, brotation=None):
            """Switch on/off bfactor refinement, optionally with the
            spacing for the bfactor refinement (in degrees.)"""

            self._bfactor = bfactor

            if brotation:
                self._brotation = brotation

        def set_surface_tie(self, surface_tie):
            self._surface_tie = surface_tie

        def set_surface_link(self, surface_link):
            self._surface_link = surface_link

        def set_anomalous(self, anomalous=True):
            """Switch on/off separating of anomalous pairs."""

            self._anomalous = anomalous

        def set_secondary(self, mode, lmax):
            assert mode in ("secondary", "absorption")
            self._secondary = mode
            self._secondary_lmax = lmax

        def set_mode(self, mode):
            if mode not in ("rotation", "batch"):
                raise RuntimeError('unknown scaling mode "%s"' % mode)
            self._mode = mode

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

        def identify_negative_scale_run(self):
            """Given the presence of a negative scale factor, try to
            identify it - this is going to be called after a negative scales
            error has been raised."""

            bad_run = 0

            runs_to_batches = {}
            run = 0

            for record in self.get_all_output():

                if "Run number" and "consists of batches" in record:
                    run = int(record.split()[2])
                    runs_to_batches[run] = []
                    continue

                if run and not record.strip():
                    run = 0
                    continue

                if run:
                    runs_to_batches[run].extend(map(int, record.split()))

                if "shifted scale factor" in record and "negative" in record:
                    tokens = record.split()
                    scale = tokens[tokens.index("factor") + 1]
                    bad_run = int(scale.split(".")[0][1:])

            return (
                bad_run,
                (min(runs_to_batches[bad_run]), max(runs_to_batches[bad_run])),
            )

        def identify_no_observations_run(self):
            """Identify the run which was causing problems with "no
            observations" reported."""

            bad_run = 0

            runs_to_batches = {}
            run = 0

            for record in self.get_all_output():

                if "Run number" and "consists of batches" in record:
                    run = int(record.split()[2])
                    runs_to_batches[run] = []
                    continue

                if run and not record.strip():
                    run = 0
                    continue

                if run:
                    runs_to_batches[run].extend(map(int, record.split()))

                if "No observations for parameter" in record:
                    bad_run = int(record.split()[-1])

            return (
                bad_run,
                (min(runs_to_batches[bad_run]), max(runs_to_batches[bad_run])),
            )

        def check_aimless_error_negative_scale_run(self):
            """Check for a bad run giving a negative scale in Aimless - this
            is particularly for the multi-crystal analysis."""

            for record in self.get_all_output():
                if " **** Negative scale factor" in record:
                    raise RuntimeError("bad batch %d" % int(record.split()[-3]))

        def check_aimless_errors(self):
            """Check for Aimless specific errors. Raise RuntimeError if
            error is found."""

            output = self.get_all_output()

            for n, line in enumerate(output):
                if "File must be sorted" in line:
                    raise RuntimeError("hklin not sorted")
                if "Negative scales" in line:
                    run, batches = self.identify_negative_scale_run()
                    raise RuntimeError(
                        "negative scales run %d: %d to %d"
                        % (run, batches[0], batches[1])
                    )
                if "Scaling has failed to converge" in line:
                    raise RuntimeError("scaling not converged")
                if "*** No observations ***" in line:
                    run, batches = self.identify_no_observations_run()
                    raise RuntimeError(
                        "no observations run %d: %d to %d"
                        % (run, batches[0], batches[1])
                    )
                if "FATAL ERROR message:" in line:
                    raise RuntimeError(output[n + 1].strip())

        def sum(self):
            """Sum a set of reflections in a sorted mtz file - this will
            just sum partials to make whole reflections, initially for
            resolution analysis."""

            self.check_hklin()
            self.check_hklout()

            self.start()

            self.input("run 1 all")
            self.input("scales constant")
            self.input("output unmerged")
            self.input("sdcorrection noadjust 1.0 0.0 0.0")

            self.close_wait()

            # check for errors

            self.check_for_errors()
            self.check_ccp4_errors()
            self.check_aimless_error_negative_scale_run()
            self.check_aimless_errors()

            return self.get_ccp4_status()

        def const(self):
            """Const scaling; for cleaner input to pointless"""

            self.check_hklin()
            self.check_hklout()
            self.start()
            self.input("scales constant")
            self.input("output unmerged")
            self.input("sdcorrection norefine 1 0 0")
            self.close_wait()

            # check for errors

            self.check_for_errors()
            self.check_ccp4_errors()
            self.check_aimless_errors()

            return "OK"

        def merge(self):
            """Actually merge the already scaled reflections."""

            self.check_hklin()
            self.check_hklout()

            if not self._onlymerge:
                raise RuntimeError("for scaling use scale()")

            if not self._scalepack:
                self.set_task(
                    "Merging scaled reflections from %s => %s"
                    % (
                        os.path.split(self.get_hklin())[-1],
                        os.path.split(self.get_hklout())[-1],
                    )
                )
            else:
                self.set_task(
                    "Merging reflections from %s => scalepack %s"
                    % (
                        os.path.split(self.get_hklin())[-1],
                        os.path.split(self.get_hklout())[-1],
                    )
                )

            self._xmlout = os.path.join(
                self.get_working_directory(), "%d_aimless.xml" % self.get_xpid()
            )

            self.start()
            self.input("xmlout %d_aimless.xml" % self.get_xpid())
            if not PhilIndex.params.xia2.settings.small_molecule:
                self.input("bins 20")
            self.input("run 1 all")
            self.input("scales constant")
            self.input("initial unity")
            self.input("sdcorrection both noadjust 1.0 0.0 0.0")

            if self._anomalous:
                self.input("anomalous on")
            else:
                self.input("anomalous off")

            if self._scalepack:
                self.input("output polish unmerged")
            self.input("output unmerged")

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_aimless_errors()

                status = self.get_ccp4_status()
                if "Error" in status:
                    raise RuntimeError("[AIMLESS] %s" % status)

            except RuntimeError as e:
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass

                raise e

            return self.get_ccp4_status()

        def scale(self):
            """Actually perform the scaling."""

            self.check_hklin()
            self.check_hklout()

            if self._chef_unmerged and self._scalepack:
                raise RuntimeError("CHEF and scalepack incompatible")

            if self._onlymerge:
                raise RuntimeError("use merge() method")

            if not self._scalepack:
                self.set_task(
                    "Scaling reflections from %s => %s"
                    % (
                        os.path.split(self.get_hklin())[-1],
                        os.path.split(self.get_hklout())[-1],
                    )
                )
            else:
                self.set_task(
                    "Scaling reflections from %s => scalepack %s"
                    % (
                        os.path.split(self.get_hklin())[-1],
                        os.path.split(self.get_hklout())[-1],
                    )
                )

            self._xmlout = os.path.join(
                self.get_working_directory(), "%d_aimless.xml" % self.get_xpid()
            )

            self.start()

            nproc = PhilIndex.params.xia2.settings.multiprocessing.nproc
            if isinstance(nproc, int) and nproc > 1:
                self.set_working_environment("OMP_NUM_THREADS", "%d" % nproc)
                self.input("refine parallel")
            self.input("xmlout %d_aimless.xml" % self.get_xpid())
            if not PhilIndex.params.xia2.settings.small_molecule:
                self.input("bins 20")
            self.input("intensities %s" % self._intensities)

            if self._new_scales_file:
                self.input("dump %s" % self._new_scales_file)

            run_number = 0
            for run in self._runs:
                run_number += 1

                if not run[5]:
                    self.input("run %d batch %d to %d" % (run_number, run[0], run[1]))

                if run[6] != 0.0 and not run[5]:
                    self.input("resolution run %d high %g" % (run_number, run[6]))

            run_number = 0
            for run in self._runs:
                run_number += 1

                if run[7]:
                    logger.debug(
                        "Run %d corresponds to sweep %s" % (run_number, run[7])
                    )

                if run[5]:
                    continue

            self.input("sdcorrection same")

            # FIXME this is a bit of a hack - should be better determined
            # than this...
            if PhilIndex.params.xia2.settings.small_molecule:
                # self.input('sdcorrection tie sdfac 0.707 0.3 tie sdadd 0.01 0.05')
                # self.input('reject all 30')
                self.input("sdcorrection fixsdb")

            if self._secondary_lmax and self._surface_tie:
                self.input("tie surface %.4f" % self._surface_tie)
                if not self._surface_link:
                    self.input("unlink all")

            # assemble the scales command
            if self._mode == "rotation":
                scale_command = "scales rotation spacing %g" % self._spacing

                if self._secondary_lmax is not None:
                    scale_command += " %s %d" % (
                        self._secondary,
                        int(self._secondary_lmax),
                    )
                else:
                    scale_command += " %s" % self._secondary

                if self._bfactor:
                    scale_command += " bfactor on"

                    if self._brotation:
                        scale_command += " brotation %g" % self._brotation

                else:
                    scale_command += " bfactor off"

                self.input(scale_command)

            else:

                scale_command = "scales batch"

                if self._bfactor:
                    scale_command += " bfactor on"

                    if self._brotation:
                        scale_command += " brotation %g" % self._brotation
                    else:
                        scale_command += " brotation %g" % self._spacing

                else:
                    scale_command += " bfactor off"

                self.input(scale_command)

            # logger.debug('Scaling command: "%s"' % scale_command)

            # next any 'generic' parameters

            if self._resolution:
                self.input("resolution %g" % self._resolution)

            self.input("cycles %d" % self._cycles)

            if self._anomalous:
                self.input("anomalous on")
            else:
                self.input("anomalous off")

            if self._scalepack:
                self.input("output polish unmerged")
            elif self._chef_unmerged:
                self.input("output unmerged together")
            else:
                self.input("output unmerged")

            # run using previously determined scales

            if self._scales_file:
                self.input("onlymerge")
                self.input("restore %s" % self._scales_file)

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_aimless_error_negative_scale_run()
                self.check_aimless_errors()
            except Exception:
                logger.warning(
                    "Aimless failed, see log file for more details:\n  %s",
                    self.get_log_file(),
                )
                raise

            logger.debug("Aimless status: OK")

            # here get a list of all output files...
            output = self.get_all_output()

            hklout_files = []
            hklout_dict = {}

            for i, record in enumerate(output):
                # this is a potential source of problems - if the
                # wavelength name has a _ in it then we are here stuffed!

                if "Writing merged data for dataset" in record:

                    if len(record.split()) == 9:
                        hklout = output[i + 1].strip()
                    else:
                        hklout = record.split()[9]

                    dname = record.split()[6].split("/")[-1]
                    hklout_dict[dname] = hklout

                    hklout_files.append(hklout)

                elif "Writing unmerged data for all datasets" in record:
                    if len(record.split()) == 9:
                        hklout = output[i + 1].strip()
                    else:
                        hklout = record.split()[9]

                    self._unmerged_reflections = hklout

            self._scalr_scaled_reflection_files = hklout_dict

            return "OK"

        def multi_merge(self):
            """Merge data from multiple runs - this is very similar to
            the scaling subroutine..."""

            self.check_hklin()
            self.check_hklout()

            if not self._scalepack:
                self.set_task(
                    "Scaling reflections from %s => %s"
                    % (
                        os.path.split(self.get_hklin())[-1],
                        os.path.split(self.get_hklout())[-1],
                    )
                )
            else:
                self.set_task(
                    "Scaling reflections from %s => scalepack %s"
                    % (
                        os.path.split(self.get_hklin())[-1],
                        os.path.split(self.get_hklout())[-1],
                    )
                )

            self.start()

            self._xmlout = os.path.join(
                self.get_working_directory(), "%d_aimless.xml" % self.get_xpid()
            )

            self.input("xmlout %d_aimless.xml" % self.get_xpid())
            if not PhilIndex.params.xia2.settings.small_molecule:
                self.input("bins 20")

            if self._new_scales_file:
                self.input("dump %s" % self._new_scales_file)

            if self._resolution:
                self.input("resolution %g" % self._resolution)

            run_number = 0
            for run in self._runs:
                run_number += 1

                if not run[5]:
                    self.input("run %d batch %d to %d" % (run_number, run[0], run[1]))

                if run[6] != 0.0 and not run[5]:
                    self.input("resolution run %d high %g" % (run_number, run[6]))

            # put in the pname, xname, dname stuff
            run_number = 0
            for run in self._runs:
                run_number += 1

                if run[7]:
                    logger.debug(
                        "Run %d corresponds to sweep %s" % (run_number, run[7])
                    )

                if run[5]:
                    continue

            # we are only merging here so the scales command is
            # dead simple...

            self.input("scales constant")

            if self._anomalous:
                self.input("anomalous on")
            else:
                self.input("anomalous off")

            # FIXME this is probably not ready to be used yet...
            if self._scalepack:
                self.input("output polish unmerged")
            self.input("output unmerged")

            if self._scales_file:
                self.input("onlymerge")
                self.input("restore %s" % self._scales_file)

            self.close_wait()

            # check for errors

            try:
                self.check_for_errors()
                self.check_ccp4_errors()
                self.check_aimless_errors()

                logger.debug("Aimless status: ok")

            except RuntimeError as e:
                try:
                    os.remove(self.get_hklout())
                except Exception:
                    pass

                raise e

            # here get a list of all output files...
            output = self.get_all_output()

            # want to put these into a dictionary at some stage, keyed
            # by the data set id. how this is implemented will depend
            # on the number of datasets...

            # FIXME file names on windows separate out path from
            # drive with ":"... fixed! split on "Filename:"

            # get a list of dataset names...

            datasets = []
            for run in self._runs:
                # cope with case where two runs make one dataset...
                if not run[4] in datasets:
                    if run[5]:
                        pass
                    else:
                        datasets.append(run[4])

            hklout_files = []
            hklout_dict = {}

            for i, record in enumerate(output):
                record = output[i]

                # this is a potential source of problems - if the
                # wavelength name has a _ in it then we are here stuffed!

                if "Writing merged data for dataset" in record:

                    if len(record.split()) == 9:
                        hklout = output[i + 1].strip()
                    else:
                        hklout = record.split()[9]

                    dname = record.split()[6].split("/")[-1]
                    hklout_dict[dname] = hklout

                    hklout_files.append(hklout)

                elif "Writing unmerged data for all datasets" in record:
                    if len(record.split()) == 9:
                        hklout = output[i + 1].strip()
                    else:
                        hklout = record.split()[9]

                    self._unmerged_reflections = hklout

            self._scalr_scaled_reflection_files = hklout_dict

            return "OK"

        def get_scaled_reflection_files(self):
            """Get the names of the actual scaled reflection files - note
            that this is not the same as HKLOUT because Aimless splits them
            up..."""
            return self._scalr_scaled_reflection_files

        def get_unmerged_reflection_file(self):
            return self._unmerged_reflections

        def get_summary(self):
            """Get a summary of the data."""

            xml_file = self.get_xmlout()
            assert os.path.isfile(xml_file)

            return parse_aimless_xml(xml_file)

    return AimlessWrapper()
