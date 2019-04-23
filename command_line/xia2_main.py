# LIBTBX_SET_DISPATCHER_NAME xia2
#
# see https://github.com/xia2/xia2/issues/172
# LIBTBX_PRE_DISPATCHER_INCLUDE_SH ulimit -n `ulimit -Hn 2>&1 |sed 's/unlimited/4096/'`

from __future__ import absolute_import, division, print_function

import os
import sys
import time
import traceback

from dials.util import Sorry
from dials.util.version import dials_version
import xia2.Driver.timing
import xia2.XIA2Version
from xia2.Applications.xia2_helpers import process_one_sweep
from xia2.Applications.xia2_main import (
    check_environment,
    get_command_line,
    help,
    write_citations,
)
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Environment import Environment
from xia2.Handlers.Files import cleanup
from xia2.Handlers.Flags import Flags
from xia2.Handlers.Streams import Chatter, Debug


def get_ccp4_version():
    CCP4 = os.environ.get("CCP4")
    if CCP4 is not None:
        version_file = os.path.join(CCP4, "lib", "ccp4", "MAJOR_MINOR")
        if os.path.exists(version_file):
            with open(version_file, "rb") as f:
                version = f.read().strip()
                return version


def xia2_main(stop_after=None):
    """Actually process something..."""
    Citations.cite("xia2")

    # print versions of related software
    Chatter.write(dials_version())

    ccp4_version = get_ccp4_version()
    if ccp4_version is not None:
        Chatter.write("CCP4 %s" % ccp4_version)

    start_time = time.time()

    CommandLine = get_command_line()
    start_dir = Flags.get_starting_directory()

    # check that something useful has been assigned for processing...
    xtals = CommandLine.get_xinfo().get_crystals()

    no_images = True

    for name in xtals.keys():
        xtal = xtals[name]

        if not xtal.get_all_image_names():

            Chatter.write("-----------------------------------" + "-" * len(name))
            Chatter.write("| No images assigned for crystal %s |" % name)
            Chatter.write("-----------------------------------" + "-" * len(name))
        else:
            no_images = False

    args = []

    from xia2.Handlers.Phil import PhilIndex

    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing
    njob = mp_params.njob

    from libtbx import group_args

    xinfo = CommandLine.get_xinfo()

    if params.xia2.settings.developmental.continue_from_previous_job and os.path.exists("xia2.json"):
        Debug.write("==== Starting from existing xia2.json ====")
        from xia2.Schema.XProject import XProject

        xinfo_new = xinfo
        xinfo = XProject.from_json(filename="xia2.json")

        crystals = xinfo.get_crystals()
        crystals_new = xinfo_new.get_crystals()
        for crystal_id in crystals_new.keys():
            if crystal_id not in crystals:
                crystals[crystal_id] = crystals_new[crystal_id]
                continue
            crystals[crystal_id]._scaler = None  # reset scaler
            for wavelength_id in crystals_new[crystal_id].get_wavelength_names():
                wavelength_new = crystals_new[crystal_id].get_xwavelength(wavelength_id)
                if wavelength_id not in crystals[crystal_id].get_wavelength_names():
                    crystals[crystal_id].add_wavelength(
                        crystals_new[crystal_id].get_xwavelength(wavelength_new)
                    )
                    continue
                wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
                sweeps_new = wavelength_new.get_sweeps()
                sweeps = wavelength.get_sweeps()
                sweep_names = [s.get_name() for s in sweeps]
                sweep_keys = [
                    (s.get_directory(), s.get_template(), s.get_image_range())
                    for s in sweeps
                ]
                for sweep in sweeps_new:
                    if (
                        sweep.get_directory(),
                        sweep.get_template(),
                        sweep.get_image_range(),
                    ) not in sweep_keys:
                        if sweep.get_name() in sweep_names:
                            i = 1
                            while "SWEEEP%i" % i in sweep_names:
                                i += 1
                            sweep._name = "SWEEP%i" % i
                            break
                        wavelength.add_sweep(
                            name=sweep.get_name(),
                            sample=sweep.get_xsample(),
                            directory=sweep.get_directory(),
                            image=sweep.get_image(),
                            beam=sweep.get_beam_centre(),
                            reversephi=sweep.get_reversephi(),
                            distance=sweep.get_distance(),
                            gain=sweep.get_gain(),
                            dmin=sweep.get_resolution_high(),
                            dmax=sweep.get_resolution_low(),
                            polarization=sweep.get_polarization(),
                            frames_to_process=sweep.get_frames_to_process(),
                            user_lattice=sweep.get_user_lattice(),
                            user_cell=sweep.get_user_cell(),
                            epoch=sweep._epoch,
                            ice=sweep._ice,
                            excluded_regions=sweep._excluded_regions,
                        )
                        sweep_names.append(sweep.get_name())

    crystals = xinfo.get_crystals()

    failover = params.xia2.settings.failover

    if mp_params.mode == "parallel" and njob > 1:
        driver_type = mp_params.type
        command_line_args = CommandLine.get_argv()[1:]
        for crystal_id in crystals.keys():
            for wavelength_id in crystals[crystal_id].get_wavelength_names():
                wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
                sweeps = wavelength.get_sweeps()
                for sweep in sweeps:
                    sweep._get_indexer()
                    sweep._get_refiner()
                    sweep._get_integrater()
                    args.append(
                        (
                            group_args(
                                driver_type=driver_type,
                                stop_after=stop_after,
                                failover=failover,
                                command_line_args=command_line_args,
                                nproc=mp_params.nproc,
                                crystal_id=crystal_id,
                                wavelength_id=wavelength_id,
                                sweep_id=sweep.get_name(),
                            ),
                        )
                    )

        from xia2.Driver.DriverFactory import DriverFactory

        default_driver_type = DriverFactory.get_driver_type()

        # run every nth job on the current computer (no need to submit to qsub)
        for i_job, arg in enumerate(args):
            if (i_job % njob) == 0:
                arg[0].driver_type = default_driver_type

        if mp_params.type == "qsub":
            method = "sge"
        else:
            method = "multiprocessing"
        nproc = mp_params.nproc
        qsub_command = mp_params.qsub_command
        if not qsub_command:
            qsub_command = "qsub"
        qsub_command = "%s -V -cwd -pe smp %d" % (qsub_command, nproc)

        from libtbx import easy_mp

        results = easy_mp.parallel_map(
            process_one_sweep,
            args,
            processes=njob,
            # method=method,
            method="multiprocessing",
            qsub_command=qsub_command,
            preserve_order=True,
            preserve_exception_message=True,
        )

        # Hack to update sweep with the serialized indexers/refiners/integraters
        i_sweep = 0
        for crystal_id in crystals.keys():
            for wavelength_id in crystals[crystal_id].get_wavelength_names():
                wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
                remove_sweeps = []
                sweeps = wavelength.get_sweeps()
                for sweep in sweeps:
                    success, output, xsweep_dict = results[i_sweep]
                    if output is not None:
                        Chatter.write(output)
                    if not success:
                        Chatter.write("Sweep failed: removing %s" % sweep.get_name())
                        remove_sweeps.append(sweep)
                    else:
                        assert xsweep_dict is not None
                        Chatter.write("Loading sweep: %s" % sweep.get_name())
                        from xia2.Schema.XSweep import XSweep

                        new_sweep = XSweep.from_dict(xsweep_dict)
                        sweep._indexer = new_sweep._indexer
                        sweep._refiner = new_sweep._refiner
                        sweep._integrater = new_sweep._integrater
                    i_sweep += 1
                for sweep in remove_sweeps:
                    wavelength.remove_sweep(sweep)
                    sample = sweep.get_xsample()
                    sample.remove_sweep(sweep)

    else:
        for crystal_id in crystals.keys():
            for wavelength_id in crystals[crystal_id].get_wavelength_names():
                wavelength = crystals[crystal_id].get_xwavelength(wavelength_id)
                remove_sweeps = []
                sweeps = wavelength.get_sweeps()
                for sweep in sweeps:
                    from dials.command_line.show import show_experiments
                    from dxtbx.model.experiment_list import ExperimentListFactory

                    Debug.write(sweep.get_name())
                    Debug.write(
                        show_experiments(
                            ExperimentListFactory.from_imageset_and_crystal(
                                sweep.get_imageset(), None
                            )
                        )
                    )
                    Citations.cite("dials")
                    try:
                        if stop_after == "index":
                            sweep.get_indexer_cell()
                        else:
                            sweep.get_integrater_intensities()
                        sweep.serialize()
                    except Exception as e:
                        if failover:
                            Chatter.write(
                                "Processing sweep %s failed: %s"
                                % (sweep.get_name(), str(e))
                            )
                            remove_sweeps.append(sweep)
                        else:
                            raise
                for sweep in remove_sweeps:
                    wavelength.remove_sweep(sweep)
                    sample = sweep.get_xsample()
                    sample.remove_sweep(sweep)

    # save intermediate xia2.json file in case scaling step fails
    xinfo.as_json(filename="xia2.json")

    if stop_after not in ("index", "integrate"):
        Chatter.write(xinfo.get_output(), strip=False)

    for crystal in crystals.values():
        crystal.serialize()

    # save final xia2.json file in case report generation fails
    xinfo.as_json(filename="xia2.json")

    if stop_after not in ("index", "integrate"):
        # and the summary file
        with open("xia2-summary.dat", "w") as fh:
            for record in xinfo.summarise():
                fh.write("%s\n" % record)

        # looks like this import overwrites the initial command line
        # Phil overrides so... for https://github.com/xia2/xia2/issues/150
        from xia2.command_line.html import generate_xia2_html

        if params.xia2.settings.small_molecule == True:
            params.xia2.settings.report.xtriage_analysis = False
            params.xia2.settings.report.include_radiation_damage = False

        with xia2.Driver.timing.record_step("xia2.report"):
            generate_xia2_html(
                xinfo, filename="xia2.html", params=params.xia2.settings.report
            )

    duration = time.time() - start_time

    # write out the time taken in a human readable way
    Chatter.write(
        "Processing took %s" % time.strftime("%Hh %Mm %Ss", time.gmtime(duration))
    )

    write_citations()

    # delete all of the temporary mtz files...
    cleanup()
    Environment.cleanup()


def run():
    if len(sys.argv) < 2 or "-help" in sys.argv or "--help" in sys.argv:
        help()
        sys.exit()

    if "-version" in sys.argv or "--version" in sys.argv:
        print(xia2.XIA2Version.Version)
        print(dials_version())
        ccp4_version = get_ccp4_version()
        if ccp4_version is not None:
            print("CCP4 %s" % ccp4_version)
        sys.exit()

    try:
        check_environment()
    except Exception as e:
        traceback.print_exc(file=open("xia2.error", "w"))
        Debug.write(traceback.format_exc(), strip=False)
        Chatter.write("Error setting up xia2 environment: %s" % str(e))
        Chatter.write(
            "Please send the contents of xia2.txt, xia2.error and xia2-debug.txt to:"
        )
        Chatter.write("xia2.support@gmail.com")
        sys.exit(1)

    wd = os.getcwd()

    # Temporarily patch os.chdir() to help identify source of #214
    origpid = os.getpid()
    origchdir = os.chdir

    def chdir_override(arg):
        if os.getpid() != origpid:
            return origchdir(arg)
        # Try to determine the name of the calling module.
        # Use exception trick to pick up the current frame.
        try:
            raise Exception()
        except Exception:
            f = sys.exc_info()[2].tb_frame.f_back

        Debug.write(
            "Directory change to %r in %s:%d" % (arg, f.f_code.co_filename, f.f_lineno)
        )
        return origchdir(arg)

    os.chdir = chdir_override

    try:
        xinfo = xia2_main()
        Debug.write("\nTiming report:")
        for line in xia2.Driver.timing.report():
            Debug.write(line, strip=False)

        Chatter.write("Status: normal termination")
        return xinfo
    except Sorry as s:
        Chatter.write("Error: %s" % str(s))
        sys.exit(1)
    except Exception as e:
        traceback.print_exc(file=open(os.path.join(wd, "xia2.error"), "w"))
        Debug.write(traceback.format_exc(), strip=False)
        Chatter.write("Error: %s" % str(e))
        Chatter.write(
            "Please send the contents of xia2.txt, xia2.error and xia2-debug.txt to:"
        )
        Chatter.write("xia2.support@gmail.com")
        sys.exit(1)


if __name__ == "__main__":
    run()
