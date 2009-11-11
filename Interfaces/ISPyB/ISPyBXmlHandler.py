#!/usr/bin/env python
# ISPyBXmlHandler.py
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A handler to manage the data which needs to end up in the ISPyB xml out
# file.
# 
# 11th November 2009

import time

class _ISPyBXmlHandler:

    def __init__(self):
        self._crystals = []
        self._per_crystal_data = {}
        self._project = None

        self._name_map = {
            'High resolution limit':'resolutionLimitHigh',
            'Low resolution limit':'resolutionLimitLow',
            'Completeness':'completeness',
            'Multiplicity':'multiplicity',
            'Anomalous completeness':'anomalousCompleteness',
            'Anomalous multiplicity':'anomalousMultiplicity',
            'Total observations':'nTotalObservations',
            'Rmerge':'rMerge',
            'I/sigma':'meanIOverSigI',
            }
                    
        return

    def set_project(self, project):
        self._project = project
        return

    def add_xcrystal(self, xcrystal):
        if not xcrystal.get_name() in self._crystals:
            self._crystals[xcrystal.get_name()] = xcrystal

        # should ideally drill down and get the refined cell constants for
        # each sweep and the scaling statistics for low resolution, high
        # resolution and overall...

        return

    def set_crystal_statistics(self, crystal, key, stats):
        self._per_crystal_data[crystal]['stats'][key] = stats
        return

    def set_crystal_cell(self, crystal, cell, spacegroup_list):
        self._per_crystal_data[crystal]['cell']['cell'] = cell
        self._per_crystal_data[crystal]['cell'][
            'spacegroup_list'] = spacegroup_list
        return        

    def add_crystal_reflection_file(self, crystal, reflection_file):
        if not reflection_file in self._per_crystal_data[crystal][
            'reflection_files']:
            self._per_crystal_data[crystal]['reflection_files'].append(
                reflection_file)

        return
    
    def add_crystal_log_file(self, crystal, log_file):
        if not log_file in self._per_crystal_data[crystal][
            'log_files']:
            self._per_crystal_data[crystal]['log_files'].append(
                log_file)

        return

    def write_date(self, fout):
        '''Write the current date and time out as XML.'''

        fout.write('<recordTimeStamp>%s</recordTimeStamp>\n' % \
                   time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

        return
        
    def write_cell(self, fout, cell):
        '''Write out a UNIT CELL as XML...'''

        fout.write('<cell_a>%f</cell_a>' % cell_info['cell'][0])
        fout.write('<cell_b>%f</cell_b>' % cell_info['cell'][1])
        fout.write('<cell_c>%f</cell_c>' % cell_info['cell'][2])
        fout.write('<cell_alpha>%f</cell_alpha>' % cell_info['cell'][3])
        fout.write('<cell_beta>%f</cell_beta>' % cell_info['cell'][4])
        fout.write('<cell_gamma>%f</cell_gamma>' % cell_info['cell'][5])

        return

    def write_refined_cell(self, fout, cell):
        '''Write out a REFINED UNIT CELL as XML...'''

        fout.write('<refinedCell_a>%f</refinedCell_a>' % \
                   cell_info['cell'][0])
        fout.write('<refinedCell_b>%f</refinedCell_b>' % \
                   cell_info['cell'][1])
        fout.write('<refinedCell_c>%f</refinedCell_c>' % \
                   cell_info['cell'][2])
        fout.write('<refinedCell_alpha>%f</refinedCell_alpha>' % \
                   cell_info['cell'][3])
        fout.write('<refinedCell_beta>%f</refinedCell_beta>' % \
                   cell_info['cell'][4])
        fout.write('<refinedCell_gamma>%f</refinedCell_gamma>' % \
                   cell_info['cell'][5])

        return    

    def write_scaling_statistics(self, fout, scaling_stats_type, stats_dict):
        '''Write out the SCALING STATISTICS block...'''

        fout.write('<AutoProcScalingStatistics>\n')

        fout.write('<scalingStatisticsType>%s</scalingStatisticsType>\n' % \
                   scaing_stats_type)

        for name in stats_dict:
            if not name in self._name_map:
                continue

            out_name = self._name_map[name]
            fout.write('<%s>%s</%s>' % (out_name, stats_dict[name], out_name))

        fout.write('</AutoProcScalingStatistics>\n')

        return

    def write_xml(self, file):

        for crystal in self._per_crsytal_data:
            xcrystal = self._per_crystal-data[crystal]

            cell = xcrystal.get_cell()
            spacegroup = xcrystal.get_likely_spacegroups()[0]
            statistics_all = xcrystal.get_statistics()
                        
            for key in statistics_all.keys():
                pname, xname, dname = key

                available = statistics_all[key].keys()

                stats = []
                keys = [
                    'High resolution limit',
                    'Low resolution limit',
                    'Completeness',
                    'Multiplicity',
                    'I/sigma',
                    'Rmerge',
                    'Rmeas(I)',
                    'Rmeas(I+/-)',
                    'Rpim(I)',
                    'Rpim(I+/-)',
                    'Wilson B factor',
                    'Partial bias',
                    'Anomalous completeness',
                    'Anomalous multiplicity',
                    'Anomalous correlation',
                    'Anomalous slope',
                    'Total observations',
                    'Total unique']

                for k in keys:
                    if k in available:
                        stats.append(k)

                save_stats_overall = { }
                save_stats_high = { }

                for s in stats:
                    if type(statistics_all[key][s]) == type(0.0):

                    elif type(statistics_all[key][s]) == type(""):
                        result += '%s: %s\n' % (s.ljust(40),
                                                statistics_all[key][s])
                    elif type(statistics_all[key][s]) == type([]):

                    save_stats_overall[s] = statistics_all[key][s][0]
                    save_stats_high[s] = statistics_all[key][s][-1]
            
        fout = open(file, 'w')

        fout.write('<?xml version="1.0"?>')

        fout.write('<DiffractionDataReduction><project>%s</project>' % \
                   self._project)

        for crystal in self._crystals:
            fout.write('<per-crystal-results><crystal>%s</crystal>' % \
                       crystal)
            fout.write('<unit-cell-information>')

            cell_info = self._per_crystal_data[crystal]['cell']

            for s in cell_info['spacegroup_list']:
                fout.write(
                    '<space-group-name-H-M>%s</space-group-name-H-M>' % \
                    s)

            fout.write('<cell_a>%f</cell_a>' % cell_info['cell'][0])
            fout.write('<cell_b>%f</cell_b>' % cell_info['cell'][1])
            fout.write('<cell_c>%f</cell_c>' % cell_info['cell'][2])
            fout.write('<cell_alpha>%f</cell_alpha>' % cell_info['cell'][3])
            fout.write('<cell_beta>%f</cell_beta>' % cell_info['cell'][4])
            fout.write('<cell_gamma>%f</cell_gamma>' % cell_info['cell'][5])
    
            fout.write('</unit-cell-information>')

            for f in self._per_crystal_data[crystal]['reflection_files']:
                fout.write('<reflection-file>%s</reflection-file>' % f)
            for f in self._per_crystal_data[crystal]['log_files']:
                fout.write('<log-file>%s</log-file>' % f)
            for f in self._per_crystal_data[crystal]['deposition_files']:
                fout.write('<deposition-file>%s</deposition-file>' % f)


            for k in self._per_crystal_data[crystal]['stats'].keys():
                fout.write('<diffraction-statistics>')
                dataset, resolution_bin = k.split(':')

                fout.write('<dataset>%s</dataset>' % dataset)
                fout.write('<resolution-bin>%s</resolution-bin>' % \
                           resolution_bin)

                for stat in self._per_crystal_data[crystal][
                    'stats'][k].keys():
                    
                    if not self._name_map.has_key(stat):
                        continue
                    
                    name = self._name_map[stat]
                    datum = self._per_crystal_data[crystal][
                        'stats'][k][stat]
                    fout.write('<%s>%s</%s>' % (name, str(datum), name))
            
                fout.write('</diffraction-statistics>')
            
            fout.write('</per-crystal-results>')

        fout.write('</DiffractionDataReduction>')

        fout.close()

        return
    
ISPyBXmlHandler = _ISPyBXmlHandler()

if __name__ == '__main__':
    ISPyBXmlHandler.set_project('test')
    ISPyBXmlHandler.write_xml('test.xml')
