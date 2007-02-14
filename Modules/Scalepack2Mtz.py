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

from lib.Guff import auto_logfiler


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

    def Mtzdump(self):
        '''Create a Mtzdump wrapper from _Mtzdump - set the working directory
        and log file stuff as a part of this...'''
        mtzdump = _Mtzdump()
        mtzdump.set_working_directory(self.get_working_directory())
        auto_logfiler(mtzdump)
        return mtzdump

    def Truncate(self):
        '''Create a Truncate wrapper from _Truncate - set the working directory
        and log file stuff as a part of this...'''
        truncate = _Truncate()
        truncate.set_working_directory(self.get_working_directory())
        auto_logfiler(truncate)
        return truncate

    def Rebatch(self):
        '''Create a Rebatch wrapper from _Rebatch - set the working directory
        and log file stuff as a part of this...'''
        rebatch = _Rebatch()
        rebatch.set_working_directory(self.get_working_directory())
        auto_logfiler(rebatch)
        return rebatch

    def Reindex(self):
        '''Create a Reindex wrapper from _Reindex - set the working directory
        and log file stuff as a part of this...'''
        reindex = _Reindex()
        reindex.set_working_directory(self.get_working_directory())
        auto_logfiler(reindex)
        return reindex

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

    # file inspection methods - check if reflections are merged or
    # unmerged

    # merge method

    # if (unmerged) merge with combat, sortmts, scala
    # else use scalepack2mtz
    # truncate all reflections
    # [do not need this as cell, spacegroup has to be explicitly set]
    # [if (mad) compute cell constants, cad in cell constants, cad together]
    # add FreeR column
    # if (mad) look for inter radiation damage

    
