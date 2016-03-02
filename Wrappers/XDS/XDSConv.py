#!/usr/bin/env python
# XDSConv.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# A wrapper to run xdsconv
#

import os
import sys
import shutil

from xia2.Driver.DriverFactory import DriverFactory
from xia2.Handlers.Streams import Debug

def XDSConv(DriverType = None):

  DriverInstance = DriverFactory.Driver(DriverType)

  class XDSConvWrapper(DriverInstance.__class__):
    '''A wrapper for wrapping XDSCONV.'''

    def __init__(self):
      DriverInstance.__class__.__init__(self)
      self.set_executable('xdsconv')

      self._input_file = None
      self._cell = None
      self._symmetry = None
      self._output_file = None

      return

    def set_input_file(self, input_file):
      self._input_file = input_file
      return

    def set_cell(self, cell):
      self._cell = cell
      return

    def get_cell(self):
      return self._cell

    def get_symmetry(self):
      return self._symmetry

    def set_symmetry(self, symmetry):
      self._symmetry = symmetry
      return

    def set_output_file(self, output_file):
      self._output_file = output_file
      return

    def parse_xds_ascii(self, file):
      '''Parse the XDS ascii file for interesting things.'''

      results = { }

      for line in open(file, 'r').readlines():
        if not line[0] == '!':
          break

        if '!FORMAT' in line:
          tokens = line.split()
          for t in tokens:
            if 'MERGED' in t:
              if t.split('=')[-1].lower() == 'false':
                raise RuntimeError, 'input unmerged'
            if 'FRIEDEL' in t:
              results['friedel'] = t.split('=')[-1].lower()

        if '!UNIT_CELL_CONSTANTS' in line:
          results['cell'] = tuple(map(float,
                                      line.split()[1:]))

        if '!INCLUDE_RESOLUTION' in line:
          results['resolution_range'] = map(float,
                                            line.split()[1:])

        if '!SPACE_GROUP' in line:
          results['spacegroup'] = int(line.split()[-1])

      return results

    def convert(self):
      if not self._input_file:
        raise RuntimeError, 'no input file specified'

      if not self._output_file:
        raise RuntimeError, 'no output file specified'

      # make the output file link a relative rather than
      # absolute path... FIXME this is unix specific!
      if self.get_working_directory() in self._output_file:
        self._output_file = self._output_file.replace(
            self.get_working_directory(), './')

      # perhaps move input file to CWD

      if len(self._input_file) > 49:
        if len(os.path.split(self._input_file)[-1]) > 49:
          raise RuntimeError, 'input file name too long'

        shutil.copyfile(
            self._input_file,
            os.path.join(self.get_working_directory(),
                         os.path.split(self._input_file)[-1]))

        self._input_file = os.path.split(self._input_file)[-1]

      header = self.parse_xds_ascii(self._input_file)

      if not self._cell:
        self._cell = header['cell']

      if not self._symmetry:
        self._symmetry = header['spacegroup']

      if header.has_key('resolution_range'):
        self._resolution = header['resolution_range']
      else:
        self._resolution = [100.0, 0.1]
      self._resolution.sort()
      self._resolution.reverse()

      inp = open(os.path.join(
          self.get_working_directory(), 'XDSCONV.INP'), 'w')

      inp.write('SPACE_GROUP_NUMBER=%d\n' % self._symmetry)

      inp.write(
          'UNIT_CELL_CONSTANTS= %.2f %.2f %.2f %.2f %.2f %.2f\n' % \
          self._cell)

      inp.write('INPUT_FILE=%s XDS_ASCII %.2f %.2f\n' % \
                (self._input_file, self._resolution[0],
                 self._resolution[1]))

      inp.write('OUTPUT_FILE=%s IALL FRIEDEL\'S_LAW=%s\n' % \
                (self._output_file, header['friedel'].upper()))

      inp.close()

      self.start()
      self.close_wait()

      # should really parse the output

      return

  return XDSConvWrapper()

# need to add a test here...
