#!/usr/bin/env python
# CCP4Factory.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 12/APR/07
#
# A factory for CCP4 program wrappers.
#

import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
    raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
    sys.path.append(os.environ['XIA2_ROOT'])

# the wrappers that this will use - these are renamed so that the internal
# factory version can be used...
from Wrappers.CCP4.Scala import Scala as _Scala
from Wrappers.CCP4.Aimless import Aimless as _Aimless
from Wrappers.CCP4.Scaleit import Scaleit as _Scaleit
from Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz
from Wrappers.CCP4.Mtzdump import Mtzdump as _Mtzdump
from Wrappers.CCP4.Truncate import Truncate as _Truncate
from Wrappers.CCP4.Rebatch import Rebatch as _Rebatch
from Wrappers.CCP4.Reindex import Reindex as _Reindex
from Wrappers.CCP4.Mtz2various import Mtz2various as _Mtz2various
from Wrappers.CCP4.Cad import Cad as _Cad
from Wrappers.CCP4.Ecalc import Ecalc as _Ecalc
from Wrappers.CCP4.Polarrfn import Polarrfn as _Polarrfn
from Wrappers.CCP4.Combat import Combat as _Combat
from Wrappers.CCP4.F2mtz import F2mtz as _F2mtz
from Wrappers.CCP4.Freerflag import Freerflag as _Freerflag
from Wrappers.CCP4.Pointless import Pointless as _Pointless
from Wrappers.CCP4.Sfcheck import Sfcheck as _Sfcheck
from Wrappers.CCP4.Matthews_coef import Matthews_coef as _Matthews_coef
from Wrappers.XIA.Chef import Chef as _Chef

from lib.bits import auto_logfiler

class CCP4Factory:
    '''A class to provide CCP4 program wrappers.'''

    def __init__(self):

        self._working_directory = os.getcwd()

    def set_working_directory(self, working_directory):
        self._working_directory = working_directory
        return

    def get_working_directory(self):
        return self._working_directory

    # factory methods...

    def Scala(self,
              partiality_correction = None,
              absorption_correction = None,
              decay_correction = None):
        '''Create a Scala wrapper from _Scala - set the working directory
        and log file stuff as a part of this...'''
        scala = _Scala(partiality_correction = partiality_correction,
                       absorption_correction = absorption_correction,
                       decay_correction = decay_correction)
        scala.set_working_directory(self.get_working_directory())
        auto_logfiler(scala)
        return scala

    def Aimless(self,
                partiality_correction = None,
                absorption_correction = None,
                decay_correction = None):
        '''Create a Aimless wrapper from _Aimless - set the working directory
        and log file stuff as a part of this...'''
        aimless = _Aimless(partiality_correction = partiality_correction,
                           absorption_correction = absorption_correction,
                           decay_correction = decay_correction)
        aimless.set_working_directory(self.get_working_directory())
        auto_logfiler(aimless)
        return aimless

    def Scaleit(self):
        '''Create a Scaleit wrapper from _Scaleit - set the working directory
        and log file stuff as a part of this...'''
        scaleit = _Scaleit()
        scaleit.set_working_directory(self.get_working_directory())
        auto_logfiler(scaleit)
        return scaleit

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

    def Ecalc(self):
        '''Create a Ecalc wrapper from _Ecalc - set the working directory
        and log file stuff as a part of this...'''
        ecalc = _Ecalc()
        ecalc.set_working_directory(self.get_working_directory())
        auto_logfiler(ecalc)
        return ecalc

    def Polarrfn(self):
        '''Create a Polarrfn wrapper from _Polarrfn - set the working directory
        and log file stuff as a part of this...'''
        polarrfn = _Polarrfn()
        polarrfn.set_working_directory(self.get_working_directory())
        auto_logfiler(polarrfn)
        return polarrfn

    def Combat(self):
        '''Create a Combat wrapper from _Combat - set the working directory
        and log file stuff as a part of this...'''
        combat = _Combat()
        combat.set_working_directory(self.get_working_directory())
        auto_logfiler(combat)
        return combat

    def F2mtz(self):
        '''Create a F2mtz wrapper from _F2mtz - set the working directory
        and log file stuff as a part of this...'''
        f2mtz = _F2mtz()
        f2mtz.set_working_directory(self.get_working_directory())
        auto_logfiler(f2mtz)
        return f2mtz

    def Freerflag(self):
        '''Create a Freerflag wrapper from _Freerflag - set the working
        directory and log file stuff as a part of this...'''
        freerflag = _Freerflag()
        freerflag.set_working_directory(self.get_working_directory())
        auto_logfiler(freerflag)
        return freerflag

    def Pointless(self):
        '''Create a Pointless wrapper from _Pointless - set the
        working directory and log file stuff as a part of this...'''
        pointless = _Pointless()
        pointless.set_working_directory(self.get_working_directory())
        auto_logfiler(pointless)
        return pointless

    def Sfcheck(self):
        '''Create a Sfcheck wrapper from _Sfcheck - set the
        working directory and log file stuff as a part of this...'''
        sfcheck = _Sfcheck()
        sfcheck.set_working_directory(self.get_working_directory())
        auto_logfiler(sfcheck)
        return sfcheck

    def Matthews_coef(self):
        '''Create a Matthews_coef wrapper from _Matthews_coef - set the
        working directory and log file stuff as a part of this...'''
        matthews_coef = _Matthews_coef()
        matthews_coef.set_working_directory(self.get_working_directory())
        auto_logfiler(matthews_coef)
        return matthews_coef

    def Chef(self):
        '''Create a Chef wrapper from _Chef - set the
        working directory and log file stuff as a part of this...'''
        chef = _Chef()
        chef.set_working_directory(self.get_working_directory())
        auto_logfiler(chef)
        return chef
