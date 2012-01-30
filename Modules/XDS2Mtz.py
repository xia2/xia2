# Scalepack2Mtz.py
# Maintained by G.Winter
# 18th June 2007
#
# A module to carefully convert XDS reflection files (merged or
# unmerged) into properly structured MTZ files. This is based on
# Scalepack2Mtz
#
# This will:
#
# if (unmerged) combat -> scala for merging (else) convert to mtz
#

import os
import sys
import math

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

from Wrappers.CCP4.CCP4Factory import CCP4Factory
from Wrappers.XDS.XDSConv import XDSConv

from Handlers.Files import FileHandler
from Handlers.Syminfo import Syminfo

class XDS2Mtz:
    '''A class to convert XDS reflection files to MTZ format, merging
    if required.'''

    def __init__(self):

        self._working_directory = os.getcwd()
        self._factory = CCP4Factory()
        return

    # admin functions

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        self._factory.set_working_directory(working_directory)
        return

    def get_working_directory(self):
        return self._working_directory

    def _decide_is_merged(self, file):
        '''Take a look at file and see if it looks like an XDS merged
        or unmerged intensity file.'''

        first_record = open(file, 'r').readline().split()

        if not '!FORMAT=XDS_ASCII' in first_record[0]:
            raise RuntimeError, 'file "%s" not XDS_ASCII' % file

        for token in first_record:
            if 'MERGE' in token:
                is_merged = token.split('=')[-1].lower()
                if is_merged == 'false':
                    return False
                elif is_merged == 'true':
                    return True
                else:
                    raise RuntimeError, 'unrecognised MERGE token  "%s"' % \
                          token

        raise RuntimeError, 'cannot find MERGE token'

    def xds_to_mtz(self, xds, hklout,
                   anomalous,
                   spacegroup = None,
                   cell = None,
                   project_info = None):
        '''Convert an XDS_ASCII file to MTZ, maybe merging.'''

        merged = self._decide_is_merged(xds)

        if merged:
            # run xdsconv, then f2mtz, then cad

            hklout_x = os.path.join(
                self.get_working_directory(), 'xdsconv-tmp.mtz')
            FileHandler.record_temporary_file(hklout_x)

            xdsconv = XDSConv()
            xdsconv.set_working_directory(self.get_working_directory())
            xdsconv.set_input_file(xds)
            xdsconv.set_output_file(hklout_x)
            if spacegroup:
                xdsconv.set_symmetry(
                    Syminfo.spacegroup_name_to_number(spacegroup))
            if cell:
                xdsconv.set_cell(cell)

            xdsconv.convert()

            # get cell etc from xds conv (which read them from the
            # reflection file...)

            if not cell:
                cell = xdsconv.get_cell()

            if not spacegroup:
                spacegroup = xdsconv.get_symmetry()

            hklout_f = os.path.join(
                self.get_working_directory(), 'f2mtz-tmp.mtz')
            FileHandler.record_temporary_file(hklout_f)

            f2mtz = self._factory.F2mtz()

            f2mtz.set_hklin(hklout_x)
            f2mtz.set_hklout(hklout_f)

            if project_info:
                pname, xname, dname = project_info
                f2mtz.set_project_info(pname, xname, dname)

            f2mtz.set_cell(cell)
            f2mtz.set_symmetry(spacegroup)

            if anomalous:
                f2mtz.xdsconv_anom2mtz()
            else:
                f2mtz.xdsconv_nat2mtz()

            cad = self._factory.Cad()
            cad.add_hklin(hklout_f)
            cad.set_hklout(hklout)
            cad.update()

            return

        else:

            hklout_c = os.path.join(
                self.get_working_directory(), 'combat-tmp.mtz')

            FileHandler.record_temporary_file(hklout_c)

            c = self._factory.Combat()
            c.set_hklin(xds)
            c.set_hklout(hklout_c)
            if spacegroup:
                c.set_spacegroup(spacegroup)
            if cell:
                c.set_cell(cell)
            if project_info:
                pname, xname, dname = project_info
                c.set_project_info(pname, xname, dname)
            c.run()

            hklin = hklout_c
            hklout_s = os.path.join(
                self.get_working_directory(), 'sortmtz-tmp.mtz')

            FileHandler.record_temporary_file(hklout_s)

            s = self._factory.Sortmtz()
            s.set_hklin(hklin)
            s.set_hklout(hklout_s)
            s.sort()

            hklin = hklout_s

            sc = self._factory.Scala()
            sc.set_hklin(hklin)
            sc.set_hklout(hklout)
            if project_info:
                pname, xname, dnme = project_info
                sc.set_project_info(pname, xname, dname)
            sc.set_anomalous(anomalous)
            sc.set_onlymerge()
            sc.merge()

            result = {'symmary':sc.get_summary(),
                      'loggraphs':sc.parse_ccp4_loggraph()}

            return result


if __name__ == '__main__':

    unmerged_data = os.path.join(os.environ['XIA2_ROOT'],
                                 'Data', 'Test', 'AMI', 'xds_unmerged')

    merged_data = os.path.join(os.environ['XIA2_ROOT'],
                               'Data', 'Test', 'AMI', 'xds_merged')

    xds2mtz = XDS2Mtz()

    xds2mtz.xds_to_mtz(os.path.join(unmerged_data, 'TS03_INFL_ANOM.hkl'),
                       'unmerged_anom.mtz', True)
    xds2mtz.xds_to_mtz(os.path.join(merged_data, 'TS03_INFL_ANOM.hkl'),
                       'merged_anom.mtz', True)
    xds2mtz.xds_to_mtz(os.path.join(merged_data, 'TS03_INFL_NAT.hkl'),
                       'merged_.nat.mtz', True)
