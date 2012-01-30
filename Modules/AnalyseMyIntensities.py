#!/usr/bin/env python
# AnalyseMyIntensities.py
#   Copyright (C) 2007 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 16th June 2007
#
# A tool to use for the analysis and gathering of scaled intensity data
# from a single macromolecular crystal. This will be both a module (for
# use in xia2) and an application in it's own right, AMI.
#
# Example usage:
#
# ami hklin1 PEAK.HKL hklin2 INFL.HKL hklin3 LREM.HKL HKLOUT merged.mtz << eof
# drename file 1 pname demo xname only dname peak
# drename file 2 pname demo xname only dname infl
# drename file 3 pname demo xname only dname lrem
# solvent 0.53
# symm P43212
# reindex h,k,l
# cell 55.67 55.67 108.92 90.0 90.0 90.0
# anomalous on
# eof
#
# should also allow for a HKLREF.

import os
import sys
import math
import copy

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.CCP4Factory import CCP4Factory

from Modules.Scalepack2Mtz import Scalepack2Mtz
from Modules.Mtz2Scalepack import Mtz2Scalepack
from Modules.XDS2Mtz import XDS2Mtz

from lib.bits import is_mtz_file, is_xds_file, is_scalepack_file
from lib.NMolLib import compute_nmol, compute_solvent

from Handlers.Streams import Chatter, Debug
from Handlers.Files import FileHandler

class AnalyseMyIntensities:
    '''A class to use for intensity analysis. This will gather intensities
    (merged or unmerged) from multiple data sets and merge them together
    as well as telling you all about your data.'''

    def __init__(self):
        self._hklin_list = []
        self._project_info = []
        self._hklout = ''
        self._solvent = 0.0
        self._nres = 0
        self._nmol = 0
        self._cell = None
        self._symmetry = None
        self._reindex = None
        self._anomalous = False
        self._rotation_function = False

        self._hklin_stats = { }

        self._working_directory = os.getcwd()

        self._factory = CCP4Factory()

        # working space
        self._resolution = 0.0

        # places to store the merging statistics etc.
        self._merging_statistics = { }
        self._merging_statistics_keys = []

        self._truncate_statistics = { }
        self._truncate_statistics_keys = []
        self._truncate_hklout = []

        self._sfcheck_statistics = { }
        self._sfcheck_statistics_keys = []

        self._huge_log_file = []

        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        return

    def get_working_directory(self):
        return self._working_directory

    def write_log_file(self, filename):
        fout = open(filename, 'w')
        for o in self._huge_log_file:
            fout.write(o)
        fout.close()

    def get_log_file(self):
        return self._huge_log_file

    # input functions

    def add_hklin(self, hklin, project_info = None):
        self._hklin_list.append(hklin)
        if project_info:
            self._project_info.append(project_info)
            pname, xname, dname = project_info
            Chatter.write('Storing %s/%s/%s with %s' % \
                          (pname, xname, dname, hklin))
        else:

            if not is_mtz_file(hklin):
                raise RuntimeError, 'hklin %s not MTZ and no project info' % \
                      hklin

            # try to get this from the reflection file
            mtzdump = self._factory.Mtzdump()
            mtzdump.set_hklin(hklin)
            mtzdump.dump()

            datasets = mtzdump.get_datasets()
            if len(datasets) > 1:
                raise RuntimeError, 'more than one dataset in %s' % hklin
            pname, xname, dname = datasets[0].split('/')
            Chatter.write('Found %s in %s' % \
                          (datasets[0], hklin))
            self._project_info.append((pname, xname, dname))

        return

    def set_hklout(self, hklout):
        self._hklout = hklout
        return

    def set_solvent(self, solvent):
        self._solvent = solvent
        return

    def set_nres(self, nres):
        self._nres = nres
        return

    def set_nmol(self, nmol):
        self._nmol = nmol
        return

    def set_cell(self, cell):
        self._cell = cell
        return

    def set_symmetry(self, symmetry):
        self._symmetry = symmetry
        return

    def set_reindex(self, reindex):
        self._reindex = reindex
        return

    def set_anomalous(self, anomalous):
        self._anomalous = anomalous
        return

    def set_rotation_function(self, rotation_function):
        self._rotation_function = rotation_function
        return

    def compute_average_cell(self, hklin_list):

        if len(hklin_list) == 0:
            raise RuntimeError, \
                  'no input reflection files to compute cell from'

        cell_a = 0.0
        cell_b = 0.0
        cell_c = 0.0
        cell_alpga = 0.0
        cell_beta = 0.0
        cell_gamma = 0.0
        n_input = 0
        sg = None

        for hklin in hklin_list:
            mtzdump = self._factory.Mtzdump()
            mtzdump.set_hklin(hklin)
            mtzdump.dump()

            resolution = min(mtzdump.get_resolution_range())
            if resolution < self._resolution or self._resolution == 0:
                self._resolution = resolution

            datasets = mtzdump.get_datasets()
            reflections = mtzdump.get_reflections()
            if len(datasets) > 1:
                raise RuntimeError, 'more than one dataset in %s' % hklin
            info = mtzdump.get_dataset_info(datasets[0])

            if not sg:
                sg = info['spacegroup']
            else:
                if sg != info['spacegroup']:
                    raise RuntimeError, 'inconsistent spacegroup'

            # check that this u/c is in agreement with the others -
            # allow 10% grace (!)

            if n_input == 0:
                cell_a = info['cell'][0] * reflections
                cell_b = info['cell'][1] * reflections
                cell_c = info['cell'][2] * reflections
                cell_alpha = info['cell'][3] * reflections
                cell_beta = info['cell'][4] * reflections
                cell_gamma = info['cell'][5] * reflections
                n_input += reflections
            else:
                if math.fabs(n_input * info['cell'][0] - cell_a) / \
                       cell_a > 0.1:
                    raise RuntimeError, 'inconsistent unit cell'
                if math.fabs(n_input * info['cell'][1] - cell_b) / \
                       cell_b > 0.1:
                    raise RuntimeError, 'inconsistent unit cell'
                if math.fabs(n_input * info['cell'][2] - cell_c) / \
                       cell_c > 0.1:
                    raise RuntimeError, 'inconsistent unit cell'
                if math.fabs(n_input * info['cell'][3] - cell_alpha) / \
                       cell_alpha > 0.1:
                    raise RuntimeError, 'inconsistent unit cell'
                if math.fabs(n_input * info['cell'][4] - cell_beta) / \
                       cell_beta > 0.1:
                    raise RuntimeError, 'inconsistent unit cell'
                if math.fabs(n_input * info['cell'][5] - cell_gamma) / \
                       cell_gamma > 0.1:
                    raise RuntimeError, 'inconsistent unit cell'

                cell_a += info['cell'][0] * reflections
                cell_b += info['cell'][1] * reflections
                cell_c += info['cell'][2] * reflections
                cell_alpha += info['cell'][3] * reflections
                cell_beta += info['cell'][4] * reflections
                cell_gamma += info['cell'][5] * reflections
                n_input += reflections

        cell_a /= n_input
        cell_b /= n_input
        cell_c /= n_input
        cell_alpha /= n_input
        cell_beta /= n_input
        cell_gamma /= n_input

        average_cell = (cell_a, cell_b, cell_c,
                        cell_alpha, cell_beta, cell_gamma)

        return average_cell, sg

    def _get_solvent(self):
        '''Get the solvent content, either from an mol/asu guess or
        from the solvent content if available.'''

        if self._nmol == 0 and self._nres == 0 and self._solvent == 0:
            raise RuntimeError, 'no solvent content information available'

        if self._solvent:
            return self._solvent

        # else try and compute an estimate

        if self._cell:
            cell = self._cell
        else:
            cell = self._average_cell

        if self._symmetry:
            symmetry = self._symmetry
        else:
            symmetry = self._average_sg

        if not self._nmol:

            self._nmol = compute_nmol(
                cell[0], cell[1], cell[2],
                cell[3], cell[4], cell[3],
                symmetry, self._resolution, self._nres)

            Chatter.write('Estimated %d molecules / ASU' % self._nmol)

        self._solvent = compute_solvent(
            cell[0], cell[1], cell[2],
            cell[3], cell[4], cell[3],
            symmetry, self._nmol, self._nres)

        return self._solvent


    def convert_to_mtz(self):
        '''Convert all HKLIN to MTZ format, storing merging statistics
        if available.'''

        hashes = '################################' + \
                 '###############################'

        Chatter.write(hashes)
        Chatter.write('### Gathering data')
        Chatter.write(hashes)

        mtz_in = []

        for j in range(len(self._hklin_list)):
            hklin = self._hklin_list[j]

            if is_mtz_file(hklin):
                mtz_in.append(hklin)

                Chatter.write('Including MTZ file: %s' % hklin)

            elif is_xds_file(hklin):

                Chatter.write('Converting XDS file: %s' % hklin)

                hklout = os.path.join(
                    self.get_working_directory(),
                    'AMI_HKLIN%d.mtz' % j)

                xds2mtz = XDS2Mtz()
                s = xds2mtz.xds_to_mtz(hklin, hklout, self._anomalous,
                                       spacegroup = self._symmetry,
                                       cell = self._cell,
                                       project_info = self._project_info[j])

                if s:
                    k = (j, self._project_info[j])
                    self._merging_statistics[j] = s
                    self._merging_statistics_keys.append(k)

                mtz_in.append(hklout)

            elif is_scalepack_file(hklin):

                Chatter.write('Converting SCALEPACK file: %s' % hklin)

                hklout = os.path.join(
                    self.get_working_directory(),
                    'AMI_HKLIN%d.mtz' % j)

                scalepack2mtz = Scalepack2Mtz()
                s = scalepack2mtz.scalepack_to_mtz(hklin, hklout,
                                                   self._anomalous,
                                                   self._symmetry, self._cell,
                                                   self._project_info[j])

                if s:
                    k = (j, self._project_info[j])
                    self._merging_statistics[j] = s
                    self._merging_statistics_keys.append(k)

                mtz_in.append(hklout)

            else:
                raise RuntimeError, 'file %s unrecognised' % hklin

        # next work through this list and apply reindexing operators
        # etc if set... also store resolution limits via a quick
        # mtzdump.

        for hklin in mtz_in:
            mtzdump = self._factory.Mtzdump()
            mtzdump.set_hklin(hklin)
            mtzdump.dump()

            resolution = min(mtzdump.get_resolution_range())

            Chatter.write('Resolution for %s: %.2f' % (hklin, resolution))

            self._hklin_stats[os.path.split(hklin)[-1]] = {
                'resolution':resolution}

        if not self._symmetry and not self._reindex:
            Chatter.write('Determining unit cell')

            self._average_cell, self._average_sg = self.compute_average_cell(
                mtz_in)

            Chatter.write(
                'Determined unit cell: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                self._average_cell)

            self._hklin_list = mtz_in
        else:
            hklin_list = []

            for j in range(len(mtz_in)):

                hklin = mtz_in[j]
                hklout = os.path.join(
                    self.get_working_directory(),
                    'AMI_HKLIN%d_reindex.mtz' % j)

                Chatter.write('Reindexing %s' % os.path.split(hklin)[-1])

                reindex = self._factory.Reindex()
                reindex.set_hklin(hklin)
                reindex.set_hklout(hklout)
                if self._symmetry:
                    reindex.set_spacegroup(self._symmetry)
                if self._reindex:
                    reindex.set_operator(self._reindex)
                reindex.reindex()

                hklin_list.append(hklout)

                resolution = self._hklin_stats[os.path.split(hklin)[-1]]
                del(self._hklin_stats[os.path.split(hklin)[-1]])
                self._hklin_stats[os.path.split(hklout)[-1]] = resolution

            # build up the average unit cell here

            Chatter.write('Determining unit cell')

            self._average_cell, self._average_sg = self.compute_average_cell(
                hklin_list)

            Chatter.write(
                'Determined unit cell: %.2f %.2f %.2f %.2f %.2f %.2f' % \
                self._average_cell)
            self._hklin_list = hklin_list

        return

    def analyse_input_hklin(self):
        '''Analyse all converted input reflection files.'''

        hashes = '################################' + \
                 '###############################'

        Chatter.write(hashes)
        Chatter.write('### Individual analysis')
        Chatter.write(hashes)

        j = 0
        for hklin in self._hklin_list:

            hklout = os.path.join(
                self.get_working_directory(),
                    'TRUNCATE%d.mtz' % j)

            # run truncate

            if not self._project_info[j]:
                Chatter.write('Truncating %s' % os.path.split(hklin)[-1])
            else:
                pname, xname, dname = self._project_info[j]
                Chatter.write('Truncating %s/%s/%s' % (pname, xname, dname))

            resolution = self._hklin_stats[os.path.split(hklin)[-1]][
                'resolution']

            truncate = self._factory.Truncate()
            truncate.set_hklin(hklin)
            truncate.set_hklout(hklout)
            if self._anomalous:
                truncate.set_anomalous(True)
            if resolution > 3.4:
                Chatter.write(
                    'Switching off Wilson scaling as data low resolution')
                truncate.set_wilson(False)
            truncate.truncate()

            FileHandler.record_log_file('%s %s %s truncate' % \
                                        self._project_info[j],
                                        truncate.get_log_file())

            # look at the wilson plot fit stats -
            # y = A e ^ - m x
            m, dm, A, da = truncate.get_wilson_fit()
            dmax, dmin = truncate.get_wilson_fit_range()

            # in here I also need to get and store the truncate B
            # factor etc. so that they can be recovered by the calling
            # program

            if dm / m < 0.1:
                Chatter.write(
                    'Over range %.2f %.2f get dm / m = %.3f: Wilson OK!' % \
                    (dmax, dmin, math.fabs(dm / m)))
            else:
                Chatter.write(
                    'Over range %.2f %.2f get dm / m = %.3f: Wilson BAD!' % \
                    (dmax, dmin, math.fabs(dm / m)))


            for o in truncate.get_all_output():
                self._huge_log_file.append(o)

            s = truncate.parse_ccp4_loggraph()

            k = (j, self._project_info[j])
            self._truncate_statistics[k] = s
            self._truncate_statistics[k][
                'Wilson B factor'] = truncate.get_b_factor()
            self._truncate_statistics_keys.append(k)

            self._truncate_hklout.append(hklout)

            j += 1

        j = 0

        for hklin in self._truncate_hklout:

            # run sfcheck

            if not self._project_info[j]:
                Chatter.write('Sfchecking %s' % os.path.split(hklin)[-1])
            else:
                pname, xname, dname = self._project_info[j]
                Chatter.write('Sfchecking %s/%s/%s' % (pname, xname, dname))

            sfcheck = self._factory.Sfcheck()
            sfcheck.set_hklin(hklin)
            sfcheck.analyse()

            twinning_score = sfcheck.get_twinning()
            optical_resolution = sfcheck.get_optical_resolution()
            eigenvalues = sfcheck.get_anisotropic_eigenvalues()
            eigenvalues_reliable = \
                                 sfcheck.get_anisotropic_eigenvalues_reliable()

            Chatter.write('Optical resolution: %.2f' % optical_resolution)

            if eigenvalues_reliable:
                Chatter.write('Eigenvalue ratios:  %.3f %.3f %.3f' % \
                              eigenvalues)
            else:
                Chatter.write(
                    'Eigenvalue ratios:  %.3f %.3f %.3f (unreliable)' % \
                    eigenvalues)

            if math.fabs(twinning_score - 1.5) < 0.2:
                Chatter.write('<I^2>/<I>^2 score:  %.2f (twinned)' % \
                              twinning_score)
            elif twinning_score > 2.5:
                Chatter.write('<I^2>/<I>^2 score:  %.2f (nasty)' % \
                              twinning_score)
            else:
                Chatter.write('<I^2>/<I>^2 score:  %.2f (ok)' % \
                              twinning_score)


            for o in sfcheck.get_all_output():
                self._huge_log_file.append(o)

            # then whatever else for the analysis

            if not self._rotation_function:
                j += 1
                continue

            Chatter.write('Analysing self-rotation function')

            hklout = os.path.join(
                self.get_working_directory(),
                'ECALC%d.mtz' % j)

            ecalc = self._factory.Ecalc()
            ecalc.set_hklin(hklin)
            ecalc.set_hklout(hklout)
            ecalc.ecalc()

            for o in ecalc.get_all_output():
                self._huge_log_file.append(o)

            hklin = hklout

            polarrfn = self._factory.Polarrfn()
            polarrfn.set_hklin(hklin)
            polarrfn.set_labin('E', 'SIGE')
            polarrfn.polarrfn()

            for o in polarrfn.get_all_output():
                self._huge_log_file.append(o)

            j += 1

        return

    def merge_analyse(self):
        '''Merge and analyse all of the data sets together, now.'''

        cad_hklin = []

        hashes = '################################' + \
                 '###############################'

        Chatter.write(hashes)
        Chatter.write('### Combined analysis')
        Chatter.write(hashes)


        Chatter.write('Merging all reflection files together')

        for j in range(len(self._truncate_hklout)):
            hklin = self._truncate_hklout[j]
            hklout = os.path.join(
                self.get_working_directory(),
                'CAD%d.mtz' % j)

            cad_hklin.append(hklout)

            cad = self._factory.Cad()
            cad.add_hklin(hklin)
            cad.set_hklout(hklout)
            if self._project_info[j]:
                pname, xname, dname = self._project_info[j]
                cad.set_project_info(pname, xname, dname)
                cad.set_new_suffix(dname)

            if self._cell:
                cad.set_new_cell(self._cell)
            else:
                cad.set_new_cell(self._average_cell)

            cad.update()

        # now merge them together...

        cad = self._factory.Cad()
        for hklin in cad_hklin:
            cad.add_hklin(hklin)
        cad.set_hklout(self._hklout)

        cad.merge()

        # then run scaleit to look at the scaling statistics

        Chatter.write('Running scaleit analysis')

        hklout = os.path.join(
            self.get_working_directory(), 'SCALEIT.mtz')

        scaleit = self._factory.Scaleit()

        scaleit.set_hklin(self._hklout)
        scaleit.set_hklout(hklout)
        scaleit.set_anomalous(self._anomalous)

        scaleit.scaleit()

        statistics = scaleit.get_statistics()

        wavelengths = statistics['mapping']
        b_factors = statistics['b_factor']

        derivatives = wavelengths.keys()
        derivatives.sort()

        for j in derivatives[:1]:
            name = b_factors[j]['dname']
            b = b_factors[j]['b']
            r = b_factors[j]['r']

            Chatter.write('%s %5.2f %4.2f (reference)' % (name, b, r))

        for j in derivatives[1:]:
            name = b_factors[j]['dname']
            b = b_factors[j]['b']
            r = b_factors[j]['r']

            Chatter.write('%s %5.2f %4.2f' % (name, b, r))

        for o in scaleit.get_all_output():
            self._huge_log_file.append(o)

        return

    def get_truncate_statistics(self):
        return copy.deepcopy(self._truncate_statistics)


if __name__ == '__main__':
    infl = os.path.join(os.environ['XIA2_ROOT'],
                        'Data', 'Test', 'AMI', 'xds_unmerged',
                        'TS03_INFL_ANOM.hkl')
    lrem = os.path.join(os.environ['XIA2_ROOT'],
                        'Data', 'Test', 'AMI', 'xds_unmerged',
                        'TS03_LREM_ANOM.hkl')

    ami = AnalyseMyIntensities()

    ami.add_hklin(infl, project_info = ('AMI', 'TEST', 'INFL'))
    ami.add_hklin(lrem, project_info = ('AMI', 'TEST', 'LREM'))

    ami.set_anomalous(True)
    ami.set_hklout('out.mtz')

    ami.set_nres(180)

    ami.convert_to_mtz()
    ami.analyse_input_hklin()
    ami.merge_analyse()
    ami._get_solvent()

    ami.write_log_file('ami.log')
