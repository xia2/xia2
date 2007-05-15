#!/usr/bin/env python
# EHTPXXmlHandler.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
# 
# A handler to manage the data which needs to end up in the e-HTPX xml out
# file.
# 
# 15th May 2007

class _EHTPXXmlHandler:

    def __init__(self):
        self._crystals = []
        self._per_crystal_data = {}
        self._project = None

        self._name_map = {
            'High resolution limit':'d-res-high',
            'Low resolution limit':'d-res-low',
            'Completeness':'percent-possible-all',
            'Multiplicity':'multiplicity',
            'Anomalous completeness':'anom-diff-percent-meas',
            'Anomalous multiplicity':'anom-multiplicity',
            'Total observations':'number-measured-all',
            'Total unique':'number-unique-all',
            'Rmerge':'rmerge-i',
            'I/sigma':'meani-over-sd-all',
            'Rmeas(I)':'rmeas-i'
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

            fout.write('<length-a>%f</length-a>' % cell_info['cell'][0])
            fout.write('<length-b>%f</length-b>' % cell_info['cell'][1])
            fout.write('<length-c>%f</length-c>' % cell_info['cell'][2])
            fout.write('<angle-alpha>%f</angle-alpha>' % cell_info['cell'][3])
            fout.write('<angle-beta>%f</angle-beta>' % cell_info['cell'][4])
            fout.write('<angle-gamma>%f</angle-gamma>' % cell_info['cell'][5])
    
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
    
EHTPXXmlHandler = _EHTPXXmlHandler()

if __name__ == '__main__':
    EHTPXXmlHandler.set_project('test')
    EHTPXXmlHandler.write_xml('test.xml')
