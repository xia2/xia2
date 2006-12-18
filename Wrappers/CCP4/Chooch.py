#!/usr/bin/env python
# Chooch.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# A wrapper for Chooch, for use in deciding what has happened during
# collection of experimental phasing data, and also for helping with
# MAD experiments.
#
# 18th December 2006
#
# 

import os
import sys
import math
import string

if not os.environ.has_key('XIA2CORE_ROOT'):
    raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
    sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                                 'Python'))
    
if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Driver.DriverFactory import DriverFactory

# helper functions

def energy_to_wavelength(energy):
    h = 6.6260693e-34
    c = 2.9979246e8
    e = 1.6021765e-19

    return 1.0e10 * (h * c) / (e * energy)

def preprocess_scan(scan_file):
    '''Preprocess the scan file to a form that chooch will accept.'''

    try:
        i = int(open(scan_file, 'r').readlines()[1])
        return scan_file
    except:
        # assume that this is not in the friendly format...
        data = open(scan_file, 'r').readlines()
        count = len(data) - 1
        out = open('xia2-chooch.raw', 'w')
        out.write('Chooch Scan File from xia2\n%d\n' % count)
        for d in data[1:]:
            out.write('%f %f\n' % tuple(map(float, d.split(',')[:2])))
        out.close()
        return 'xia2-chooch.raw'

def Chooch(DriverType = None):
    '''Factory for Chooch wrapper classes, with the specified
    Driver type.'''

    DriverInstance = DriverFactory.Driver(DriverType)

    class ChoochWrapper(DriverInstance.__class__):
        def __init__(self):

            DriverInstance.__class__.__init__(self)
            
            self.set_executable('chooch')
            self._scan = None
            self._edge_table = { }

            self._atom = 'se'

        def set_scan(self, scan):
            '''Set a scan file for chooch to parse.'''

            self._scan = preprocess_scan(scan)
            return

        def set_atom(self, atom):
            '''Set the atom which should be in the scan.'''

            self._atom = atom
            return

        def scan(self):
            '''Run chooch.'''

            self.add_command_line('-e')
            self.add_command_line(self._atom)
            self.add_command_line(self._scan)

            self.start()
            self.close_wait()

            self.check_for_errors()

            output = self.get_all_output()
            collect = False

            for o in output:
                if collect:

                    if '-------' in o:
                        collect = False
                        continue
                    
                    name, energy, fp, fpp = tuple(map(string.strip,
                                                      o.split('|')[1:5]))
                    self._edge_table[name] = {
                        'energy':float(energy),
                        'fp':float(fp),
                        'fpp':float(fpp),
                        'wave':energy_to_wavelength(float(energy))}
                
                if 'energy' in o and 'f\'' in o and 'f\'\'' in o:
                    collect = True

        def get_edges(self):
            return self._edge_table

    return ChoochWrapper()

if __name__ == '__main__':

    if len(sys.argv) < 2:

        c = Chooch()
        c.set_scan(os.path.join(os.environ['XIA2_ROOT'], 'Data',
                                'Test', 'Scans',
                                'TM0486-9172-Se.raw'))
        c.set_atom('se')
        c.scan()
        
        edges = c.get_edges()
        
        for key in edges.keys():
            print '%s %6.2f %6.2f %8.6f' % (key,
                                            edges[key]['fp'],
                                            edges[key]['fpp'],
                                            edges[key]['wave'])

    else:
        for scan in sys.argv[1:]:

            print os.path.split(scan)[-1]

            c = Chooch()
            c.set_scan(scan)
            c.set_atom('se')
            c.scan()
            
            edges = c.get_edges()
            
            for key in edges.keys():
                print '%s %6.2f %6.2f %8.6f' % (key,
                                                edges[key]['fp'],
                                                edges[key]['fpp'],
                                                edges[key]['wave'])

	    print ''
            
