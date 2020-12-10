# A handler to manage the data which needs to end up in the ISPyB database


# mapping xia2 verbose names to ISPyB API field names
# https://github.com/DiamondLightSource/ispyb-api/blob/
#     41bf10db91ab0f0bea91f77a5f37f087c28218ca/ispyb/sp/mxprocessing.py#L28-L32
_name_map = {
    "High resolution limit": "res_lim_high",
    "Low resolution limit": "res_lim_low",
    "Completeness": "completeness",
    "Multiplicity": "multiplicity",
    "CC half": "cc_half",
    "Anomalous completeness": "anom_completeness",
    "Anomalous correlation": "cc_anom",
    "Anomalous multiplicity": "anom_multiplicity",
    "Total observations": "n_tot_obs",
    "Total unique": "n_tot_unique_obs",
    "Rmerge(I+/-)": "r_merge",
    "Rmeas(I)": "r_meas_all_iplusi_minus",
    "Rmeas(I+/-)": "r_meas_within_iplusi_minus",
    "Rpim(I)": "r_pim_all_iplusi_minus",
    "Rpim(I+/-)": "r_pim_within_iplusi_minus",
    "Partial Bias": "fract_partial_bias",
    "I/sigma": "mean_i_sig_i",
}


def xia2_to_json_object(xcrystals):
    result = {}

    for xcrystal in xcrystals:
        cell = xcrystal.get_cell()
        spacegroup = xcrystal.get_likely_spacegroups()[0]

        # Stick closely to ISPyB field names
        # https://github.com/DiamondLightSource/ispyb-api/blob/
        #   41bf10db91ab0f0bea91f77a5f37f087c28218ca/ispyb/sp/mxprocessing.py#L24-L26
        result["refined_results"] = {
            "spacegroup": spacegroup,
            "refinedcell_a": cell[0],
            "refinedcell_b": cell[1],
            "refinedcell_c": cell[2],
            "refinedcell_alpha": cell[3],
            "refinedcell_beta": cell[4],
            "refinedcell_gamma": cell[5],
        }

        statistics_all = xcrystal.get_statistics()
        # wavelength_names = xcrystal.get_wavelength_names()

        for key, statistic in statistics_all.items():
            pname, xname, dname = key

            # FIXME should assert that the dname is a
            # valid wavelength name

            result["scaling_statistics"] = {}
            for j, name in enumerate(("overall", "innerShell", "outerShell")):
                result["scaling_statistics"][name] = {
                    _name_map[stat_name]: stat_value[j]
                    for stat_name, stat_value in statistic.items()
                    if stat_name in _name_map
                }

            result["integrations"] = []
            xwavelength = xcrystal.get_xwavelength(dname)
            sweeps = xwavelength.get_sweeps()
            for sweep in sweeps:
                # Stick closely to ISPyB field names
                # https://github.com/DiamondLightSource/ispyb-api/blob/
                #   41bf10db91ab0f0bea91f77a5f37f087c28218ca/ispyb/sp/
                #   mxprocessing.py#L34-L39
                integration = {}

                cell = sweep.get_integrater_cell()
                for name, value in zip(["a", "b", "c", "alpha", "beta", "gamma"], cell):
                    integration["cell_%s" % name] = value

                # FIXME this is naughty
                indxr = sweep._get_indexer()
                intgr = sweep._get_integrater()

                start, end = intgr.get_integrater_wedge()
                integration["start_image_no"] = start
                integration["end_image_no"] = end

                integration["refined_detector_dist"] = indxr.get_indexer_distance()

                beam = indxr.get_indexer_beam_centre_raw_image()
                integration["refined_xbeam"] = beam[0]
                integration["refined_ybeam"] = beam[1]

                result["integrations"].append(integration)

    return result
