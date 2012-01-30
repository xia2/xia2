# Scalepack2Mtz.py
# Maintained by G.Winter
# 12th February 2007
#
# A module to carefully convert scalepack reflection files (merged or
# unmerged) into properly structured MTZ files. This is based on the last
# section of CCP4ScalerImplementation, as that does largely the same.
#
# This will:
#
# if (unmerged) combat -> scala for merging (else) convert to mtz
# truncate all wavelengths
# if (mad) compute cell, cad in cell, cad together
# add freeR column
# if (mad) look for inter radiation damage
#
# This assumes:
#
# Reflections are correctly indexed
# One reflection file per wavelength
# All files from same crystal and therefore project
#
# Should produce results similar to CCP4ScalerImplementation.
#
# Example data will come from xia2.
#
# Implementation fill follow line 1469++ of CCP4ScalerImplementation.
#
# Uses:
#
# scalepack2mtz wrapper for merged files
# combat, sortmtz, scala for unmerged files
# mtzdump, cad, freerflag to muddle with files
# truncate to compute F's from I's.
#

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the wrappers that this will use - these are renamed so that the internal
# factory version can be used...
from Wrappers.CCP4.Scala import Scala as _Scala
from Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz
from Wrappers.CCP4.Truncate import Truncate as _Truncate
from Wrappers.CCP4.Cad import Cad as _Cad
from Wrappers.CCP4.Freerflag import Freerflag as _Freerflag
from Wrappers.CCP4.Combat import Combat as _Combat
from Wrappers.CCP4.Scalepack2mtz import Scalepack2mtz as _Scalepack2mtz

from Handlers.Streams import Chatter
from Handlers.Files import FileHandler

from CCP4InterRadiationDamageDetector import CCP4InterRadiationDamageDetector

# jiffys

from lib.bits import auto_logfiler

class Scalepack2Mtz:
    '''A jiffy class to enable transformation between scalepack format
    (merged or unmerged) to a properly structured MTZ file.'''

    def __init__(self):
        # data that this will need to store
        # working directory stuff
        # pname/xname/dname/data file stuff

        self._working_directory = os.getcwd()

        # this will be keyed by dname

        self._hklin_files = { }
        self._pname = None
        self._xname = None
        self._dnames = []

        # cell and spacegroup information

        self._cell = None
        self._spacegroup = None

        return

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory

    # getter and setter methods

    def set_cell(self, cell):
        self._cell = cell
        return

    def set_spacegroup(self, spacegroup):
        self._spacegroup = spacegroup
        return

    def set_project_info(self, pname, xname):
        self._pname = pname
        self._xname = xname
        return

    def add_hklin(self, dname, hklin):
        if self._hklin_files.has_key(dname):
            raise RuntimeError, 'dataset name %s already exists' % dname

        self._hklin_files[dname] = hklin
        self._dnames.append(dname)

        return

    # factory methods...

    def Scala(self):
        '''Create a Scala wrapper from _Scala - set the working directory
        and log file stuff as a part of this...'''
        scala = _Scala()
        scala.set_working_directory(self.get_working_directory())
        auto_logfiler(scala)
        return scala

    def Scalepack2mtz(self):
        '''Create a Scalepack2mtz wrapper from _Scalepack2mtz - set the
        working directory and log file stuff as a part of this...'''
        scalepack2mtz = _Scalepack2mtz()
        scalepack2mtz.set_working_directory(self.get_working_directory())
        auto_logfiler(scalepack2mtz)
        return scalepack2mtz

    def Combat(self):
        '''Create a Combat wrapper from _Combat - set the working directory
        and log file stuff as a part of this...'''
        combat = _Combat()
        combat.set_working_directory(self.get_working_directory())
        auto_logfiler(combat)
        return combat

    def Sortmtz(self):
        '''Create a Sortmtz wrapper from _Sortmtz - set the working directory
        and log file stuff as a part of this...'''
        sortmtz = _Sortmtz()
        sortmtz.set_working_directory(self.get_working_directory())
        auto_logfiler(sortmtz)
        return sortmtz

    def Truncate(self):
        '''Create a Truncate wrapper from _Truncate - set the working directory
        and log file stuff as a part of this...'''
        truncate = _Truncate()
        truncate.set_working_directory(self.get_working_directory())
        auto_logfiler(truncate)
        return truncate

    def Mtz2various(self):
        '''Create a Mtz2various wrapper from _Mtz2various - set the working
        directory and log file stuff as a part of this...'''
        mtz2various = _Mtz2various()
        mtz2various.set_working_directory(self.get_working_directory())
        auto_logfiler(mtz2various)
        return mtz2various

    def Cad(self):
        '''Create a Cad wrapper from _Cad - set the working directory
        and log file stuff as a part of this...'''
        cad = _Cad()
        cad.set_working_directory(self.get_working_directory())
        auto_logfiler(cad)
        return cad

    def Freerflag(self):
        '''Create a Freerflag wrapper from _Freerflag - set the working
        directory and log file stuff as a part of this...'''
        freerflag = _Freerflag()
        freerflag.set_working_directory(self.get_working_directory())
        auto_logfiler(freerflag)
        return freerflag

    # helper functions

    def _merged_scalepack_to_mtz(self, dname):
        '''Convert a merged reflection file for dname from scalepack format
        to PNAME_XNAME_merged_tmp_DNAME.mtz.'''

        scalepack_file = self._hklin_files[dname]

        s2m = self.Scalepack2mtz()
        s2m.set_hklin(scalepack_file)
        s2m.set_hklout(os.path.join(self.get_working_directory(),
                                    '%s_%s_merged_tmp_%s.mtz' % \
                                    (self._pname, self._xname, dname)))
        s2m.set_spacegroup(self._spacegroup)
        s2m.set_cell(self._cell)
        s2m.set_project_info(self._pname, self._xname, dname)
        s2m.convert()

        return

    def _unmerged_scalepack_to_mtz(self, dname):
        '''Convert an unmerged reflection file for dname from scalepack format
        to PNAME_XNAME_merged_tmp_DNAME.mtz.'''

        scalepack_file = self._hklin_files[dname]

        # convert to multirecord MTZ

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_unmerged_tmp_%s.mtz' % \
                              (self._pname, self._xname, dname))

        FileHandler.record_temporary_file(hklout)

        c = self.Combat()
        c.set_hklin(scalepack_file)
        c.set_hklout(hklout)
        c.set_spacegroup(self._spacegroup)
        c.set_cell(self._cell)
        c.set_project_info(self._pname, self._xname, dname)
        c.run()

        # sort

        hklin = hklout
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_sorted_tmp_%s.mtz' % \
                              (self._pname, self._xname, dname))

        FileHandler.record_temporary_file(hklout)

        s = self.Sortmtz()
        s.set_hklin(hklin)
        s.set_hklout(hklout)
        s.sort()

        # merge - FIXME should this presume that the input is anomalous
        # data??

        hklin = hklout
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_merged_tmp_%s.mtz' % \
                              (self._pname, self._xname, dname))

        FileHandler.record_temporary_file(hklout)

        # FIXME in here I need to know if we are wanting anomalous
        # pairs separated or merged, though it probably doesn't
        # matter too much...

        sc = self.Scala()
        sc.set_hklin(hklin)
        sc.set_hklout(hklout)
        sc.set_project_info(self._pname, self._xname, dname)
        sc.set_anomalous()
        sc.set_onlymerge()
        sc.merge()

        FileHandler.record_log_file('%s %s %s merge' % \
                                    (self._pname, self._xname, dname),
                                    sc.get_log_file())

        return

    def _decide_is_merged(self, file):
        '''Decide if the input file is merged, based on first 3 lines.'''

        f = open(file, 'r')
        start = [f.readline() for j in range(3)]
        f.close()

        # merged scalepack looks like number, number, cell

        if len(start[0].split()) == 1 and \
           len(start[1].split()) == 1 and \
           len(start[2].split()) > 6:
            return True

        # unmerged scalepack from scala looks like number spacegroup,
        # symop, symop, symop...

        if len(start[0].split()) > 2 and \
           len(start[1].split()) > 2 and \
           len(start[2].split()) > 2:
            return False

        # get to here is a problem

        raise RuntimeError, 'cannot decide file format'

    # merge method

    def scalepack_to_mtz(self, scalepack, hklout,
                         anomalous, spacegroup, cell, project_info = None):
        '''Convert a scalepack file to MTZ, maybe merging.'''

        # inspect to see if it is merged
        merged = self._decide_is_merged(scalepack)

        if merged:
            s2m = self.Scalepack2mtz()
            s2m.set_hklin(scalepack)
            s2m.set_hklout(hklout)
            s2m.set_spacegroup(spacegroup)
            s2m.set_cell(cell)
            if project_info:
                pname, xname, dname = project_info
                s2m.set_project_info(pname, xname, dname)
            s2m.convert()

            return

        else:

            hklout_c = os.path.join(
                self.get_working_directory(), 'combat-tmp.mtz')

            FileHandler.record_temporary_file(hklout_c)

            c = self.Combat()
            c.set_hklin(scalepack)
            c.set_hklout(hklout_c)
            c.set_spacegroup(spacegroup)
            c.set_cell(cell)
            if project_info:
                pname, xname, dname = project_info
                c.set_project_info(pname, xname, dname)
            c.run()

            hklin = hklout_c
            hklout_s = os.path.join(
                self.get_working_directory(), 'sortmtz-tmp.mtz')

            FileHandler.record_temporary_file(hklout_s)

            s = self.Sortmtz()
            s.set_hklin(hklin)
            s.set_hklout(hklout_s)
            s.sort()

            hklin = hklout_s

            sc = self.Scala()
            sc.set_hklin(hklin)
            sc.set_hklout(hklout)
            if project_info:
                pname, xname, dname = project_info
                sc.set_project_info(pname, xname, dname)
            sc.set_anomalous(anomalous)
            sc.set_onlymerge()
            sc.merge()

            result = {'symmary':sc.get_summary(),
                      'loggraphs':sc.parse_ccp4_loggraph()}

            return result


    def convert(self):
        '''Transmogrify the input scalepack files to mtz.'''

        merged_files = []

        for dname in self._dnames:
            scalepack = self._hklin_files[dname]

            # inspect to see if it is merged
            merged = self._decide_is_merged(scalepack)

            # if (unmerged) merge with combat, sortmts, scala - this is
            # implemented in _unmerged_scalepack_to_mtz - takes dname

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_merged_tmp_%s.mtz' % \
                                  (self._pname, self._xname, dname))

            if merged:
                self._merged_scalepack_to_mtz(dname)
            else:
                self._unmerged_scalepack_to_mtz(dname)

            # truncate the reflections

            hklin = hklout

            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_truncated_tmp_%s.mtz' % \
                                  (self._pname, self._xname, dname))

            FileHandler.record_temporary_file(hklout)

            t = self.Truncate()
            t.set_hklin(hklin)
            t.set_hklout(hklout)
            t.truncate()

            FileHandler.record_log_file('%s %s %s truncate' % \
                                        (self._pname,
                                         self._xname,
                                         dname),
                                        t.get_log_file())

            hklin = hklout
            hklout = os.path.join(self.get_working_directory(),
                                  '%s_%s_truncated_cad_tmp_%s.mtz' % \
                                  (self._pname, self._xname, dname))

            FileHandler.record_temporary_file(hklout)

            # need to assign the column labels here - this will probably
            # have to be a quick CAD run. This prevents duplicate column
            # names later on

            c = self.Cad()
            c.add_hklin(hklin)
            c.set_hklout(hklout)
            c.set_new_suffix(dname)
            c.update()

        # cad together

        c = self.Cad()
        for dname in self._dnames:
            hklin = os.path.join(self.get_working_directory(),
                                 '%s_%s_truncated_cad_tmp_%s.mtz' % \
                                 (self._pname, self._xname, dname))

            c.add_hklin(hklin)

        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_merged.mtz' % (self._pname,
                                                    self._xname))

        Chatter.write('Merging all data sets to %s' % hklout)

        c.set_hklout(hklout)
        c.merge()

        # add FreeR column

        f = self.Freerflag()

        hklin = hklout
        hklout = os.path.join(self.get_working_directory(),
                              '%s_%s_merged_free.mtz' % (self._pname,
                                                         self._xname))

        f.set_hklin(hklin)
        f.set_hklout(hklout)
        f.add_free_flag()

        # if (mad) look for inter radiation damage

        return hklout

# add a unit test

if __name__ == '__main__':
    # UNMERGED

    data_directory = os.path.join(os.environ['X2TD_ROOT'],
                                  'Test', 'UnitTest', 'Interfaces',
                                  'Scaler', 'Unmerged')

    s2m = Scalepack2Mtz()

    s2m.add_hklin('INFL', os.path.join(data_directory,
                                       'TS00_13185_unmerged_INFL.sca'))
    s2m.add_hklin('LREM', os.path.join(data_directory,
                                       'TS00_13185_unmerged_LREM.sca'))
    s2m.add_hklin('PEAK', os.path.join(data_directory,
                                       'TS00_13185_unmerged_PEAK.sca'))

    s2m.set_cell((57.73, 76.93, 86.57, 90.00, 90.00, 90.00))
    s2m.set_spacegroup('P212121')
    s2m.set_project_info('TS00', '13185')

    print s2m.convert()

    # MERGED

    data_directory = os.path.join(os.environ['X2TD_ROOT'],
                                  'Test', 'UnitTest', 'Interfaces',
                                  'Scaler', 'Merged')

    s2m = Scalepack2Mtz()

    s2m.add_hklin('INFL', os.path.join(data_directory,
                                       'TS00_13185_scaled_INFL.sca'))
    s2m.add_hklin('LREM', os.path.join(data_directory,
                                       'TS00_13185_scaled_LREM.sca'))
    s2m.add_hklin('PEAK', os.path.join(data_directory,
                                       'TS00_13185_scaled_PEAK.sca'))

    s2m.set_cell((57.73, 76.93, 86.57, 90.00, 90.00, 90.00))
    s2m.set_spacegroup('P212121')
    s2m.set_project_info('TS00A', '13185')

    print s2m.convert()
