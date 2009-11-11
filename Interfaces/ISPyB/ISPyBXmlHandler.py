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

    def add_crystal(self, crystal):
        if not crystal in self._crystals:
            self._crystals.append(crystal)

            self._per_crystal_data[crystal] = {
                'stats':{},
                'cell':{},
                'log_files':[],
                'deposition_files':[],
                'reflection_files':[]
                }

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
    
    def add_crystal_deposition_file(self, crystal, deposition_file):
        if not deposition_file in self._per_crystal_data[crystal][
            'deposition_files']:
            self._per_crystal_data[crystal]['deposition_files'].append(
                deposition_file)

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

    def write_xml(self, file):
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
