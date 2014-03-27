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

import sys
import os
import math
import time
import exceptions
import traceback

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

sys.path.insert(0, os.environ['XIA2_ROOT'])

if not 'XIA2CORE_ROOT' in os.environ:
  os.environ['XIA2CORE_ROOT'] = os.path.join(os.environ['XIA2_ROOT'], 'core')

from Handlers.Streams import Chatter
from Handlers.Files import cleanup
from Handlers.Citations import Citations
from Handlers.Environment import Environment, df

from XIA2Version import Version

# XML Marked up output for e-HTPX
if not os.path.join(os.environ['XIA2_ROOT'], 'Interfaces') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT'], 'Interfaces'))

from xia2setup import write_xinfo

# CCTBX bits I want

import libtbx.load_env

def check_cctbx_version():
  '''Check that we have the an acceptable CCTBX version.'''

  version = None
  for tag_file in ["TAG", "cctbx_bundle_TAG"]:
    tag_path = libtbx.env.under_dist("libtbx",
                                     os.path.join("..", tag_file))
    if (os.path.isfile(tag_path)):
      try:
        version = open(tag_path).read().strip()
      except KeyboardInterrupt:
        raise
      except:
        pass
    else:
      break

  if version is None:
    version = libtbx.env.command_version_suffix

  if version is None:
    # just assume that this is from subversion => probably up-to-date!
    return

  # should find a good way to run a test herein!

def check_environment():
  '''Check the environment we are running in...'''

  version = sys.version_info

  if version[0] < 2:
    raise RuntimeError, 'Python 1.x not supported'

  if version[0] == 2 and version[1] < 4:
    raise RuntimeError, 'Python 2.x before 2.4 not supported'

  # now check that the CCTBX routines are available

  check_cctbx_version()

  xia2_keys = ['XIA2_ROOT', 'XIA2CORE_ROOT']
  ccp4_keys = ['CCP4', 'CLIBD', 'CCP4_SCR']

  Chatter.write('Environment configuration...')
  for k in xia2_keys:
    v = Environment.getenv(k)
    if not v:
      raise RuntimeError, '%s not defined - is xia2 set up?'
    if not v == v.strip():
      raise RuntimeError, 'spaces around "%s"' % v
    Chatter.write('%s => %s' % (k, v))

  for k in ccp4_keys:
    v = Environment.getenv(k)
    if not v:
      raise RuntimeError, '%s not defined - is CCP4 set up?'
    if not v == v.strip():
      raise RuntimeError, 'spaces around "%s"' % v
    Chatter.write('%s => %s' % (k, v))

  Chatter.write('Working directory: %s' % os.getcwd())
  Chatter.write('Free space:        %.2f GB' % (df() / math.pow(2, 30)))

  try:
    if os.name == 'nt':
      hostname = os.environ['COMPUTERNAME'].split('.')[0]
    else:
      hostname = os.environ['HOSTNAME'].split('.')[0]

    Chatter.write('Host: %s' % hostname)
  except KeyError, e:
    pass

  revision = '$Revision$'
  if len(revision.split()) > 1:
    revision = revision.split()[1]
  else:
    revision = 'not set'

  Chatter.write('Build: %s' % revision)
  Chatter.write('Contact: xia2.support@gmail.com')

  return

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

def check():
  '''Check that the set-up is ok...'''

  sys.path.append(os.path.join((os.environ['XIA2CORE_ROOT']),
                               'Python'))

  from TestPython import test_python_setup

  test_python_setup()

  return

def xia2():
  '''Actually process something...'''

  # print the version
  Chatter.write(Version)
  Citations.cite('xia2')

  start_time = time.time()

  from Handlers.CommandLine import CommandLine

  CommandLine.print_command_line()

  if not CommandLine.get_xinfo():
    # write an xinfo file then
    xinfo = os.path.join(os.getcwd(), 'automatic.xinfo')

    argv = CommandLine.get_argv()

    if not CommandLine.get_directory():

      path = argv.pop()

      while not os.path.exists(path):
        try:
          path = '%s %s' % (argv.pop(), path)
        except IndexError, e:
          raise RuntimeError, \
                'directory not found in arguments: %s' % path

    else:
      path = CommandLine.get_directory()
      if not os.path.exists(path):
        raise RuntimeError, 'provided path %s does not exist' % path

    if not os.path.isabs(path):
      path = os.path.abspath(path)

    # in here check that this is a directory

    if not os.path.isdir(path):
      raise RuntimeError, '%s must be a directory' % path

    if CommandLine.get_template():
      write_xinfo(xinfo, path, template = CommandLine.get_template())
    else:
      write_xinfo(xinfo, path)

    CommandLine.set_xinfo(xinfo)

  # check that something useful has been assigned for processing...
  xtals = CommandLine.get_xinfo().get_crystals()

  no_images = True

  for name in xtals.keys():
    xtal = xtals[name]

    if not xtal.get_all_image_names():

      Chatter.write('-----------------------------------' + \
                    '-' * len(name))
      Chatter.write('| No images assigned for crystal %s |' % name)
      Chatter.write('-----------------------------------' + '-' \
                    * len(name))
    else:
      no_images = False

  # this actually gets the processing started...
  Chatter.write(str(CommandLine.get_xinfo()))

  duration = time.time() - start_time

  # write out the time taken in a human readable way
  Chatter.write('Processing took %s' % \
                time.strftime("%Hh %Mm %Ss", time.gmtime(duration)))

  from Handlers.Flags import Flags
  if Flags.get_pickle():
    import cPickle as pickle
    try:
      pickle.dump(CommandLine.get_xinfo(),
                  open(Flags.get_pickle(), 'w'))
    except exceptions.Exception, e:
      traceback.print_exc(file = open('xia2.pkl.error', 'w'))

  # delete all of the temporary mtz files...
  cleanup()

  # maybe write out the headers
  from Handlers.Flags import Flags
  if Flags.get_hdr_out():
    from Wrappers.XIA.Diffdump import HeaderCache
    HeaderCache.write(Flags.get_hdr_out())

  # and the summary file
  summary_records = CommandLine.get_xinfo().summarise()

  fout = open('xia2-summary.dat', 'w')
  for record in summary_records:
    fout.write('%s\n' % record)
  fout.close()

  # tell the user which programs were used...
  used = ''
  for program in Citations.get_programs():
    used += ' %s' % program

  Chatter.write('XIA2 used... %s' % used)
  Chatter.write(
      'Here are the appropriate citations (BIBTeX in xia-citations.bib.)')

  for citation in Citations.get_citations_acta():
    Chatter.write(citation)

  # and write the bibtex versions
  out = open('xia-citations.bib', 'w')

  for citation in Citations.get_citations():
    out.write('%s\n' % citation)

  out.close()

  Environment.cleanup()

  return

def help():
  '''Print out some help for xia2.'''

  sys.stdout.write('\nCommand-line options to xia2:\n')
  sys.stdout.write('[-parallel 4] (automatic)\n')
  sys.stdout.write('[-resolution 2.8] (say, applies to all sweeps)\n')
  sys.stdout.write('[-freer_file free.mtz]\n')
  sys.stdout.write('[-reference_reflection_file free.mtz]\n')
  sys.stdout.write('[-spacegroup C2] (for example)\n')
  sys.stdout.write('[-quick]\n')
  sys.stdout.write('[-reversephi]\n')
  sys.stdout.write('[-migrate_data]\n')
  sys.stdout.write('[-2d] or [-3d] or [-3dii]\n')
  sys.stdout.write('[-xinfo foo.xinfo] or [/path/to/images]\n\n')
  sys.stdout.write('[-atom se] (say) - this is for xia2setup\n')
  sys.stdout.write('[-project foo] (say) - this is for xia2setup\n')
  sys.stdout.write('[-crystal bar] (say) - this is for xia2setup\n\n')

  sys.stdout.write('Command-lines for testing\n')
  sys.stdout.write('[-smart_scaling] figure out the "best" scaling model\n')

  sys.stdout.write('Develper options - do not use these ...\n')
  sys.stdout.write(
      '[-z_min 50] (minimum Z value for rejecting reflections)\n')
  sys.stdout.write('[-trust_timestamps]\n')
  sys.stdout.write('[-debug]\n')
  sys.stdout.write('[-relax]\n')
  sys.stdout.write('[-zero_dose]\n')
  sys.stdout.write('[-norefine]\n\n')

  sys.stdout.write('Sensible command lines:\n')
  sys.stdout.write('xia2 (-2d|-3d) -xinfo foo.xinfo\n')
  sys.stdout.write('xia2 -project foo -crystal bar (-2d|-3d) /data/path\n')

if __name__ == '__main__':

  try:
    check_environment()
    check()
  except exceptions.Exception, e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))

  if len(sys.argv) < 2 or '-help' in sys.argv:
    help()
    sys.exit()

  try:
    xia2()
    Chatter.write('Status: normal termination')

  except exceptions.Exception, e:
    traceback.print_exc(file = open('xia2.error', 'w'))
    Chatter.write('Status: error "%s"' % str(e))
