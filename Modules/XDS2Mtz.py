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

        for token in file_record:
            if 'MERGED' in token:
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
                xdsconv.set_symmetry(spacegroup)
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
            cad.set_hklin(hklout_f)
            cad.set_hklout(hklout)
            cad.update()
            
            return hklout

        else:

            hklout_c = os.path.join(
                self.get_working_directory(), 'combat-tmp.mtz')
            
            FileHandler.record_temporary_file(hklout_c)
            
            c = self.Combat()
            c.set_hklin(xds)
            c.set_hklout(hklout_c)
            if spacegroup:
                c.set_spacegroup(spacegroup)
            if cell:
                c.set_cell(cell)
            if project_info:
                c.set_project_info(project_info)
            c.run()
        
            hklin = hklout_c
            hklout_s = os.path.join(
                self.get_working_directory(), 'sortmtz-tmp.mtz')
                                  
            FileHandler.record_temporary_file(hklout_s)

            s = self.Sortmtz()
            s.set_hklin(hklin)
            s.set_hklout(hklout)
            s.sort()
            
            hklin = hklout_s

            sc = self.Scala()
            sc.set_hklin(hklin)
            sc.set_hklout(hklout)
            if project_info:
                sc.set_project_info(project_info)
            sc.set_anomalous(anomalous)
            sc.set_onlymerge()
            sc.merge()

            # gather and make available for return the merging statistics...

            return hklout
            

# ned to add some tests here....        
                
        
        
