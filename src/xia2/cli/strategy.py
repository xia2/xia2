import logging
import json
import os
import sys
import traceback

from xia2.Applications.xia2_main import check_environment, get_command_line, help
import xia2.Handlers.Streams
from xia2.lib.bits import auto_logfiler

logger = logging.getLogger("xia2.command_line.strategy")


def run():
    try:
        check_environment()
    except Exception as e:
        with open("xia2-error.txt", "w") as fh:
            traceback.print_exc(file=fh)
        logger.error('Status: error "%s"', str(e))

    if len(sys.argv) < 2 or "-help" in sys.argv:
        help()
        sys.exit()

    cwd = os.getcwd()

    try:
        from xia2.command_line.xia2_main import xia2_main

        xia2_main(stop_after="integrate")
        logger.info("Status: normal termination")

        wd = os.path.join(cwd, "strategy")
        if not os.path.exists(wd):
            os.mkdir(wd)
        os.chdir(wd)

        CommandLine = get_command_line()
        xinfo = CommandLine.get_xinfo()
        crystals = xinfo.get_crystals()

        assert len(crystals) == 1
        crystal = list(crystals.values())[0]
        assert len(crystal.get_wavelength_names()) == 1
        wavelength = crystal.get_xwavelength(crystal.get_wavelength_names()[0])
        sweeps = wavelength.get_sweeps()

        from xia2.Handlers.Phil import PhilIndex

        params = PhilIndex.get_python_object()
        strategy_params = params.strategy
        if not len(strategy_params):
            strategy_params = [PhilIndex.get_scope_by_name("strategy")[0].extract()]

        from dxtbx.model import MultiAxisGoniometer

        gonio = sweeps[0].get_imageset().get_goniometer()
        if (
            isinstance(gonio, MultiAxisGoniometer)
            and len(gonio.get_axes()) == 3
            and gonio.get_scan_axis() == 2
        ):
            from xia2.Wrappers.Dials.AlignCrystal import AlignCrystal

            align_crystal = AlignCrystal()
            align_crystal.set_experiments_filename(
                sweeps[0]._get_integrater().get_integrated_experiments()
            )
            align_crystal.set_working_directory(wd)
            auto_logfiler(align_crystal)
            align_crystal.set_json_filename(
                "%i_align_crystal.json" % align_crystal.get_xpid()
            )
            align_crystal.run()
            logger.info("".join(align_crystal.get_all_output()))

        results_all = {}

        def process_one_strategy(args):
            assert len(args) == 4
            experiments, reflections, strategy, t_ref = args
            from xia2.Wrappers.EMBL import Best

            best = Best.BestStrategy()
            for isweep, (expt, refl) in enumerate(zip(experiments, reflections)):
                from xia2.Wrappers.Dials.ExportBest import ExportBest

                export = ExportBest()
                export.set_experiments_filename(expt)
                export.set_reflections_filename(refl)
                export.set_working_directory(wd)
                auto_logfiler(export)
                prefix = "%i_best" % export.get_xpid()
                export.set_prefix(prefix)
                export.run()
                if isweep == 0:
                    best.set_t_ref(t_ref)
                    best.set_mos_dat("%s.dat" % prefix)
                    best.set_mos_par("%s.par" % prefix)
                best.add_mos_hkl("%s.hkl" % prefix)
            best.set_i2s(strategy.i_over_sigi)
            best.set_T_max(strategy.max_total_exposure)
            best.set_t_min(strategy.min_exposure)
            # best.set_trans_ref(25.0)
            best.set_S_max(strategy.max_rotation_speed)
            best.set_w_min(strategy.min_oscillation_width)
            best.set_M_min(strategy.multiplicity)
            best.set_C_min(strategy.completeness)
            best.set_GpS(strategy.dose_rate)
            best.set_shape(strategy.shape)
            best.set_susceptibility(strategy.susceptibility)
            best.set_anomalous(strategy.anomalous)

            best.set_detector("pilatus6m")
            best.set_working_directory(wd)
            auto_logfiler(best)
            xmlout = os.path.join(
                best.get_working_directory(), "%i_best.xml" % best.get_xpid()
            )
            best.set_xmlout(xmlout)
            best.strategy()

            results = best.get_results_dict()
            results["description"] = strategy.description
            if "phi_end" not in results:
                results["phi_end"] = str(
                    float(results["phi_start"])
                    + float(results["number_of_images"]) * float(results["phi_width"])
                )
            from dxtbx.serialize import load

            expt = load.experiment_list(experiments[0])[0]
            results["spacegroup"] = (
                expt.crystal.get_space_group().type().lookup_symbol()
            )
            return results

        args = []
        for istrategy, strategy in enumerate(strategy_params):
            imageset = sweeps[0].get_imageset()
            scan = imageset.get_scan()
            experiments = [
                sweep._get_integrater().get_integrated_experiments() for sweep in sweeps
            ]
            reflections = [
                sweep._get_integrater().get_integrated_reflections() for sweep in sweeps
            ]
            t_ref = scan.get_exposure_times()[0]
            args.append((experiments, reflections, strategy, t_ref))

        nproc = params.xia2.settings.multiprocessing.nproc
        from libtbx import easy_mp

        results = easy_mp.parallel_map(
            process_one_strategy,
            args,
            processes=nproc,
            method="multiprocessing",
            preserve_order=True,
            preserve_exception_message=True,
        )

        for istrategy, (result, strategy) in enumerate(zip(results, strategy_params)):
            name = strategy.name
            description = strategy.description
            if name is None:
                name = "Strategy%i" % (istrategy + 1)
            results_all[name] = result
            multiplicity = result["redundancy"]
            try:
                multiplicity = "%.2f" % multiplicity
            except TypeError:
                pass
            logger.info("Strategy %i", istrategy)
            if description is not None:
                logger.info(description)
            logger.info(
                "Start / end / width: %.2f/%.2f/%.2f",
                float(result["phi_start"]),
                float(result["phi_end"]),
                float(result["phi_width"]),
            )
            logger.info(
                "Completeness / multiplicity / resolution: %.2f/%s/%.2f",
                float(result["completeness"]),
                multiplicity,
                float(result["resolution"]),
            )
            logger.info(
                "Transmission / exposure %.3f/%.3f",
                float(result["transmission"]),
                float(result["exposure_time"]),
            )

        with open("strategies.json", "wb") as f:
            json.dump(results_all, f, indent=2)

    except Exception as e:
        with open(os.path.join(cwd, "xia2-error.txt"), "w") as fh:
            traceback.print_exc(file=fh)
        logger.error('Status: error "%s"', str(e))
    os.chdir(cwd)


if __name__ == "__main__":
    xia2.Handlers.Streams.setup_logging(
        logfile="xia2.strategy.txt", debugfile="xia2.strategy-debug.txt"
    )
    run()
