# A handler to manage the data which needs to end up in the ISPyB database

from __future__ import absolute_import, division, print_function

_name_map = {
    'High resolution limit': 'resolutionLimitHigh',
    'Low resolution limit': 'resolutionLimitLow',
    'Completeness': 'completeness',
    'Multiplicity': 'multiplicity',
    'CC half': 'ccHalf',
    'Anomalous completeness': 'anomalousCompleteness',
    'Anomalous correlation': 'ccAnomalous',
    'Anomalous multiplicity': 'anomalousMultiplicity',
    'Total observations': 'nTotalObservations',
    'Total unique': 'nTotalUniqueObservations',
    'Rmerge(I+/-)': 'rMerge',
    'Rmeas(I)': 'rMeasAllIPlusIMinus',
    'Rmeas(I+/-)': 'rMeasWithinIPlusIMinus',
    'Rpim(I)': 'rPimAllIPlusIMinus',
    'Rpim(I+/-)': 'rPimWithinIPlusIMinus',
    'Partial Bias': 'fractionalPartialBias',
    'I/sigma': 'meanIOverSigI',
}

def xia2_to_json_object(xcrystals):
  result = {}

  for xcrystal in xcrystals:
    cell = xcrystal.get_cell()
    spacegroup = xcrystal.get_likely_spacegroups()[0]

    result['refined_results'] = {
        'space_group': spacegroup,
        'unit_cell': cell,
    }

#     result['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    statistics_all = xcrystal.get_statistics()
    # wavelength_names = xcrystal.get_wavelength_names()

    for key in statistics_all.keys():
      pname, xname, dname = key

      # FIXME should assert that the dname is a
      # valid wavelength name

      available = statistics_all[key].keys()
      stats = filter(lambda k: k in available, _name_map)

      result['scaling_statistics'] = {}
      for j, name in enumerate(['overall', 'innerShell', 'outerShell']):
        result['scaling_statistics'][name] = {
          _name_map[s]: statistics_all[key][s][j]
          for s in stats
        }

      result['integrations'] = []
      xwavelength = xcrystal.get_xwavelength(dname)
      sweeps = xwavelength.get_sweeps()
      for sweep in sweeps:
        cell = sweep.get_integrater_cell()
        integration = {}
        for name, value in zip(['a', 'b', 'c', 'alpha', 'beta', 'gamma'],
                               cell):
          integration['cell_%s' % name] = value

        # FIXME this is naughty
        indxr = sweep._get_indexer()
        intgr = sweep._get_integrater()

        start, end = intgr.get_integrater_wedge()

        integration['startImageNumber'] = start
        integration['endImageNumber'] = end

        integration['refinedDetectorDistance'] = indxr.get_indexer_distance()

        beam = indxr.get_indexer_beam_centre()

        integration['refinedXBeam'] = beam[0]
        integration['refinedYBeam'] = beam[1]

        result['integrations'].append(integration)

  return result
