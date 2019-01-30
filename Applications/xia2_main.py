#!/usr/bin/env python
# xia2.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 21/SEP/06
#
# A top-level interface to the whole of xia2, for data processing & analysis.

from __future__ import absolute_import, division, print_function

import math
import os
import platform
import sys

from dials.util import Sorry
from xia2.Handlers.Citations import Citations
from xia2.Handlers.Environment import Environment, df
from xia2.Handlers.Streams import Chatter, Debug
from xia2.XIA2Version import Version

def check_environment():
  '''Check the environment we are running in...'''

  if sys.hexversion < 0x02070000:
    raise RuntimeError('Python versions older than 2.7 are not supported')

  import cctbx
  executable = sys.executable
  cctbx_dir = os.sep.join(cctbx.__file__.split(os.sep)[:-3])

  # to help wrapper code - print process id...

  Debug.write('Process ID: %d' % os.getpid())

  Chatter.write('Environment configuration...')
  Chatter.write('Python => %s' % executable)
  Chatter.write('CCTBX => %s' % cctbx_dir)

  ccp4_keys = ['CCP4', 'CLIBD', 'CCP4_SCR']
  for k in ccp4_keys:
    v = Environment.getenv(k)
    if not v:
      raise RuntimeError('%s not defined - is CCP4 set up?' % k)
    if not v == v.strip():
      raise RuntimeError('spaces around "%s"' % v)
    Chatter.write('%s => %s' % (k, v))

  from xia2.Handlers.Flags import Flags
  Chatter.write('Starting directory: %s' % Flags.get_starting_directory())
  Chatter.write('Working directory: %s' % os.getcwd())
  Chatter.write('Free space:        %.2f GB' % (df() / math.pow(2, 30)))

  hostname = platform.node().split('.')[0]
  Chatter.write('Host: %s' % hostname)

  Chatter.write('Contact: xia2.support@gmail.com')

  Chatter.write(Version)

  # temporary workaround to bug in pointless...
  if ' ' in os.getcwd():
    raise RuntimeError('Space in working directory ' \
        '(https://github.com/xia2/xia2/issues/114)')

def get_command_line():
  from xia2.Handlers.CommandLine import CommandLine

  CommandLine.print_command_line()

  if not CommandLine.get_xinfo():
    # write an xinfo file then
    xinfo = os.path.join(os.getcwd(), 'automatic.xinfo')

    argv = CommandLine.get_argv()

    if not CommandLine.get_directory():

      directories = []

      for arg in argv:
        if os.path.isdir(arg):
          directories.append(os.path.abspath(arg))

      if not directories and not CommandLine.get_hdf5_master_files():
        raise Sorry("No image directory found in command line arguments. "
                    "Run xia2 without any options for command line help.")

    else:
      directories = CommandLine.get_directory()

    directories = [os.path.abspath(d) for d in directories]
    from xia2.Applications.xia2setup import write_xinfo

    if CommandLine.get_template() or CommandLine.get_hdf5_master_files():
      write_xinfo(xinfo, directories, template=CommandLine.get_template(),
                  hdf5_master_files=CommandLine.get_hdf5_master_files())
    else:
      write_xinfo(xinfo, directories)

    CommandLine.set_xinfo(xinfo)

  return CommandLine

def write_citations():
  # tell the user which programs were used...
  Chatter.write('XIA2 used... %s' % \
      ', '.join(Citations.get_programs()))
  Chatter.write(
      'Here are the appropriate citations (BIBTeX in xia2-citations.bib.)')

  for citation in Citations.get_citations_acta():
    Chatter.write(citation)

  # and write the bibtex versions
  out = open('xia2-citations.bib', 'w')

  for citation in Citations.get_citations():
    out.write('%s\n' % citation)

  out.close()

def help():
  '''Print out some help for xia2.'''

  sys.stdout.write('%s\n' % Version)

  # FIXME also needs to make reference to Phil input
  # FIXME ideally should move all command-line functionality over to Phil...
  # FIXME these should also be generated in automatic way #42

  sys.stdout.write('An expert system for automated reduction of X-Ray\n')
  sys.stdout.write('diffraction data from macromolecular crystals\n')

  sys.stdout.write('''
Command-line options to xia2:
[pipeline=XXX] select processing pipeline, with XXX one of:
  2d    MOSFLM, LABELIT (if installed), AIMLESS
  3d    XDS, XSCALE, LABELIT
  3dii  XDS, XSCALE, using all images for autoindexing
  dials DIALS, AIMLESS
''')
  sys.stdout.write('[xinfo=foo.xinfo] or [/path/to/images]\n\n')

  sys.stdout.write('[d_min=2.8] (say, applies to all sweeps)\n')
  sys.stdout.write('[nproc=4] run on 4 processors (automatic)\n')
  sys.stdout.write('[space_group=C2] (for example)\n')
  sys.stdout.write('[unit_cell=50,50,50,90,90,90] (for example)\n')
  sys.stdout.write('[reverse_phi=True]\n')
  sys.stdout.write(
    '[mosflm_beam_centre=x,y] (in mm, following the MOSFLM convention, applies to all sweeps)\n')
  sys.stdout.write('[dials.fast_mode=True] for very fast processing\n')
  sys.stdout.write('[atom=se] (say) - this is for xia2setup\n')
  sys.stdout.write('[project=foo] (say) - this is for xia2setup\n')
  sys.stdout.write('[crystal=bar] (say) - this is for xia2setup\n\n')

  sys.stdout.write('Sensible command lines:\n')
  sys.stdout.write('xia2 (pipeline=2d|3d|..) xinfo=foo.xinfo\n')
  sys.stdout.write('xia2 project=foo crystal=bar (pipeline=2d|3d|..) /data/path\n')
  sys.stdout.write('xia2 image=/data/path/segment_1_0001.cbf:1:900\n')
