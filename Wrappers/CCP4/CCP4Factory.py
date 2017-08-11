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

from __future__ import absolute_import, division

import os

# the wrappers that this will use - these are renamed so that the internal
# factory version can be used...
from xia2.Wrappers.CCP4.Aimless import Aimless as _Aimless
from xia2.Wrappers.CCP4.Scaleit import Scaleit as _Scaleit
from xia2.Wrappers.CCP4.Sortmtz import Sortmtz as _Sortmtz
from xia2.Wrappers.CCP4.Mtzdump import Mtzdump as _Mtzdump
from xia2.Wrappers.CCP4.Truncate import Truncate as _Truncate
from xia2.Wrappers.CCP4.Rebatch import Rebatch as _Rebatch
from xia2.Wrappers.CCP4.Reindex import Reindex as _Reindex
from xia2.Wrappers.CCP4.Mtz2various import Mtz2various as _Mtz2various
from xia2.Wrappers.CCP4.Cad import Cad as _Cad
from xia2.Wrappers.CCP4.Freerflag import Freerflag as _Freerflag
from xia2.Wrappers.CCP4.Pointless import Pointless as _Pointless
from xia2.Wrappers.CCP4.Matthews_coef import Matthews_coef as _Matthews_coef
from xia2.Wrappers.XIA.Chef import Chef as _Chef

from xia2.lib.bits import auto_logfiler

class CCP4Factory(object):
  '''A class to provide CCP4 program wrappers.'''

  def __init__(self):

    self._working_directory = os.getcwd()

  def set_working_directory(self, working_directory):
    self._working_directory = working_directory

  def get_working_directory(self):
    return self._working_directory

  # factory methods...

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

  def Pointless(self):
    '''Create a Pointless wrapper from _Pointless - set the
    working directory and log file stuff as a part of this...'''
    pointless = _Pointless()
    pointless.set_working_directory(self.get_working_directory())
    auto_logfiler(pointless)
    return pointless

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
