#!/usr/bin/env python
# Autosol.py
#   Copyright (C) 2010 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is 
#   included in the root directory of this package.
#
# The beginnings of a wrapper for the PHENIX AUTOSOL wizard, which may be 
# used for automated experimental phasing. In the first instance this will
# simply write a ${CRYSTALNAME}.eff file, which will contain the information
# needed to run the PHENIX AUTOSOL wizard.
#

class Autosol:
    '''A class to gather and write the information to run the PHENIX
    AUTOSOL wizard.'''

    def __init__(self):

        self._xname = None
        
        self._sites = None
        self._atom_type = None

        self._wavelengths = []

        return

    def set_xname(self, xname):
        self._xname = xname
        return

    def set_sites(self, sites):
        self._sites = sites
        return

    def set_atom_type(self, atom_type):
        self._atom_type = atom_type
        return

    def add_wavelength(self, data, wavelength, f_pr, f_prpr, labels):
        new_labels = '\'%s' % labels[0]
        for l in labels[1:]:
            new_labels += ' %s' % l
        new_labels += '\''
        self._wavelengths.append({'data':data,
                                  'lambda':wavelength,
                                  'f_prime':f_pr,
                                  'f_double_prime':f_prpr,
                                  'labels':new_labels})
        return

    def export(self, path):
        fout = open(os.path.join(path, '%s.eff' % self._xname), 'w')
        fout.write('autosol {\n  sites = %d\n  atom_type = %s\n' % \
                   (self._sites, self._atom_type))
        
        for wavelength in self._wavelengths:
            fout.write('  wavelength {\n')
            for k in wavelength:
                fout.write('    %s = %s\n' % (k, str(wavelength[k])))
            fout.write('  }\n')

        fout.write('}\n')
        
        return

if __name__ == '__main__':

    import os

    autosol = Autosol()

    autosol.set_xname('test')
    autosol.set_atom_type('se')
    autosol.set_sites(8)

    autosol.add_wavelength('TS03_12287_free.mtz', 0.97966, -9.9, 3.9,
                           ['I(+)_INFL', 'SIGI(+)_INFL',
                            'I(-)_INFL', 'SIGI(-)_INFL'])

    autosol.add_wavelength('TS03_12287_free.mtz', 1.00000, -3.3, 0.5,
                           ['I(+)_LREM', 'SIGI(+)_LREM',
                            'I(-)_LREM', 'SIGI(-)_LREM'])

    autosol.export(os.getcwd())
    
