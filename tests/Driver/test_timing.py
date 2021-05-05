import re

import xia2.Driver.timing


def test_recording_of_timing_events():
    xia2.Driver.timing.reset()
    assert xia2.Driver.timing.report() == []

    task1 = "sentinel1"
    task2 = "sentinel2"

    def record(name, start):
        return {"command": name, "time_start": start, "time_end": start}

    xia2.Driver.timing.record(record(task1, 1))
    xia2.Driver.timing.record(record(task2, 2))
    report = xia2.Driver.timing.report()
    assert report
    assert task1 in report[0]
    assert "thinking" in report[1]
    assert task2 in report[2]

    xia2.Driver.timing.reset()
    assert xia2.Driver.timing.report() == []


def test_timing_visualisation():
    example = [
        {
            "command": "pointless  '-c' 'hklin' 'DEFAULT/NATIVE/SWEEP1/integrate/dials_integrated_reindex.mtz'",
            "details": {
                "object initialization": 1555579135.274619,
                "process start": 1555579135.275884,
            },
            "time_end": 1555579135.680343,
            "time_start": 1555579135.274619,
        },
        {
            "command": "pointless  'xmlout' '1_pointless.xml' 'hklin' '/dls/tmp/wra62962/directories/98U0mam9/DEFAULT/NATIVE/SWEEP1/integrate/dials_integrated_reindex.mtz'",
            "details": {
                "object initialization": 1555579135.71696,
                "process start": 1555579135.721616,
            },
            # "time_end": 1555579135.904055,
            "time_end": 1555579140.22,
            "time_start": 1555579135.71696,
        },
        {
            "command": "sortmtz  'hklin' 'AUTOMATIC_DEFAULT_NATIVE_SWEEP1_integrated.mtz' 'hklout' 'AUTOMATIC_DEFAULT_sorted.mtz'",
            "details": {
                "object initialization": 1555579135.971231,
                "process start": 1555579135.97447,
            },
            "time_end": 1555579136.080755,
            "time_start": 1555579135.971231,
        },
        {
            "command": "pointless  '-c' 'hklin' 'DEFAULT/scale/AUTOMATIC_DEFAULT_sorted.mtz'",
            "details": {
                "object initialization": 1555579136.087576,
                "process start": 1555579136.088692,
            },
            "time_end": 1555579136.185289,
            "time_start": 1555579136.087576,
        },
        {
            "command": "pointless  'xmlout' '3_pointless.xml' 'hklout' 'pointless.mtz' 'hklin' 'AUTOMATIC_DEFAULT_sorted.mtz'",
            "details": {
                "object initialization": 1555579136.084393,
                "process start": 1555579136.217787,
            },
            "time_end": 1555579136.485051,
            "time_start": 1555579136.084393,
        },
        {
            "command": "pointless  'hklin' 'AUTOMATIC_DEFAULT_sorted.mtz' 'hklout' 'AUTOMATIC_DEFAULT_temp.mtz'",
            "details": {
                "object initialization": 1555579136.496305,
                "process start": 1555579136.499182,
            },
            "time_end": 1555579136.646148,
            "time_start": 1555579136.496305,
        },
        {
            "command": "sortmtz  'hklin' 'AUTOMATIC_DEFAULT_temp.mtz' 'hklout' 'AUTOMATIC_DEFAULT_sorted.mtz'",
            "details": {
                "object initialization": 1555579136.64923,
                "process start": 1555579136.651854,
            },
            # "time_end": 1555579136.730769,
            "time_end": 1555579144.36730769,
            "time_start": 1555579136.64923,
        },
        {
            "command": "aimless",
            "details": {
                "object initialization": 1555579136.769065,
                "process start": 1555579137.85061,
            },
            "time_end": 1555579137.846154,
            "time_start": 1555579136.769065,
        },
        {
            "command": "aimless  'hklin' 'AUTOMATIC_DEFAULT_sorted.mtz' 'hklout' 'AUTOMATIC_DEFAULT_scaled_test.mtz'",
            "details": {
                "object initialization": 1555579136.769065,
                "process start": 1555579137.85061,
            },
            "time_end": 1555579138.55397,
            "time_start": 1555579136.769065,
        },
        {
            "command": "xia2.resolutionizer  'AUTOMATIC_DEFAULT_scaled_test_unmerged.mtz' 'nbins=100' 'rmerge=None' 'completeness=None' 'cc_half=0.3' 'cc_half_fit=tanh' 'cc_half_significance_level=0.1' 'isigma=0.25' 'misigma=1.0' 'batch_range=1,300'",
            "details": {
                "object initialization": 1555579138.586713,
                "process start": 1555579138.589566,
            },
            # "time_end": 1555579139.552127,
            "time_end": 1555579140.19,
            "time_start": 1555579138.586713,
        },
        {
            "command": "aimless",
            "details": {
                "object initialization": 1555579139.555794,
                "process start": 1555579139.591472,
            },
            "time_end": 1555579139.58835,
            "time_start": 1555579139.555794,
        },
        {
            "command": "aimless  'hklin' 'AUTOMATIC_DEFAULT_sorted.mtz' 'hklout' 'AUTOMATIC_DEFAULT_scaled_test.mtz'",
            "details": {
                "object initialization": 1555579139.555794,
                "process start": 1555579139.591472,
            },
            "time_end": 1555579140.176235,
            "time_start": 1555579139.555794,
        },
        {
            "command": "aimless",
            "details": {
                "object initialization": 1555579140.208151,
                "process start": 1555579140.244692,
            },
            "time_end": 1555579140.239683,
            "time_start": 1555579140.208151,
        },
        {
            "command": "aimless  'hklin' 'AUTOMATIC_DEFAULT_sorted.mtz' 'hklout' 'AUTOMATIC_DEFAULT_scaled.mtz'",
            "details": {
                "object initialization": 1555579140.208151,
                "process start": 1555579140.244692,
            },
            "time_end": 1555579140.827103,
            "time_start": 1555579140.208151,
        },
        {
            "command": "aimless",
            "details": {
                "object initialization": 1555579140.858459,
                "process start": 1555579140.89975,
            },
            "time_end": 1555579140.890458,
            "time_start": 1555579140.858459,
        },
        {
            "command": "aimless  'hklin' 'AUTOMATIC_DEFAULT_sorted.mtz' 'hklout' 'AUTOMATIC_DEFAULT_scaled.mtz'",
            "details": {
                "object initialization": 1555579140.858459,
                "process start": 1555579140.89975,
            },
            "time_end": 1555579141.224997,
            "time_start": 1555579140.858459,
        },
        {
            "command": "dials.reindex  '/dls/tmp/wra62962/directories/98U0mam9/DEFAULT/NATIVE/SWEEP1/integrate/13_integrated_experiments.json' 'output.experiments=12_experiments_reindexed.json' '/dls/tmp/wra62962/directories/98U0mam9/DEFAULT/NATIVE/SWEEP1/integrate/13_integrated.pickle' 'output.reflections=12_reflections_reindexed.pickle' 'change_of_basis_op=h,k,l'",
            "details": {
                "object initialization": 1555579141.235312,
                "process start": 1555579141.238581,
            },
            "time_end": 1555579142.181813,
            "time_start": 1555579141.235312,
        },
        {
            "command": "dials.two_theta_refine  '12_experiments_reindexed.json' '12_reflections_reindexed.pickle' 'combine_crystal_models=True' 'output.cif=11_dials.two_theta_refine.cif' 'output.mmcif=11_dials.two_theta_refine.mmcif' 'output.p4p=AUTOMATIC_DEFAULT.p4p' 'output.correlation_plot.filename=11_dials.two_theta_refine.png' 'output.experiments=11_refined_cell.json'",
            "details": {
                "object initialization": 1555579141.233133,
                "process start": 1555579142.185421,
            },
            "time_end": 1555579143.554306,
            "time_start": 1555579141.233133,
        },
        {
            "command": "aimless",
            "details": {
                "object initialization": 1555579144.107419,
                "process start": 1555579144.152825,
            },
            "time_end": 1555579144.145499,
            "time_start": 1555579144.107419,
        },
        {
            "command": "aimless  'hklin' 'AUTOMATIC_DEFAULT_sorted.mtz' 'hklout' 'AUTOMATIC_DEFAULT_chef.mtz'",
            "details": {
                "object initialization": 1555579144.107419,
                "process start": 1555579144.152825,
            },
            "time_end": 1555579144.480268,
            "time_start": 1555579144.107419,
        },
        {
            "command": "ctruncate  '-hklin' 'AUTOMATIC_DEFAULT_scaled.mtz' '-hklout' 'NATIVE_truncated.mtz' '-colin' '/*/*/[IMEAN,SIGIMEAN]' '-xmlout' '14_truncate.xml'",
            "details": {
                "object initialization": 1555579147.519639,
                "process start": 1555579147.52277,
            },
            "time_end": 1555579148.282126,
            "time_start": 1555579147.519639,
        },
        {
            "command": "freerflag  'hklin' 'NATIVE_truncated.mtz' 'hklout' 'AUTOMATIC_DEFAULT_free_temp.mtz'",
            "details": {
                "object initialization": 1555579148.288115,
                "process start": 1555579148.291029,
            },
            # "time_end": 1555579148.367611,
            "time_end": 1555579168.367611,
            "time_start": 1555579158.288115,
        },
        {
            "command": "freerflag  'hklin' 'AUTOMATIC_DEFAULT_free_temp.mtz' 'hklout' 'AUTOMATIC_DEFAULT_free.mtz'",
            "details": {
                "object initialization": 1555579148.370701,
                "process start": 1555579148.381674,
            },
            "time_end": 1555579158.454594,
            "time_start": 1555579158.370701,
        },
    ]

    output = xia2.Driver.timing.visualise_db(example)
    print()
    print("\n".join(output).encode("utf-8"))
    lt = output.index("Longest times:")
    assert lt

    tree = "\n".join(output[:lt])
    top10 = [line.split(".", 2)[2].strip() for line in output[lt + 1 :]]

    seen_in_top10 = 0
    for program in example:
        # every command should appear at least once
        assert program["command"].split(" ")[0] in tree
        if program["command"].strip() in top10:
            seen_in_top10 += 1

    # and 10 or at least n(example) should appear in the top 10
    # may be more due to name overlaps
    assert seen_in_top10 >= min(10, len(example))
    assert len(top10) == min(10, len(example))

    # thinking time should appear in the tree
    assert re.search("^13.* T[0-9] .*xia2 thinking time.*$", tree, re.MULTILINE)
