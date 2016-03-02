#!/usr/bin/env python
# xia2setup.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# xia2setup.py - an application to generate the .xinfo file for data
# reduction from a directory full of images, optionally with scan and
# sequence files which will be used to add matadata.
#
# 18th December 2006
#


import os
import sys
import exceptions
import time
import traceback

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Schema.Sweep import SweepFactory
from Experts.FindImages import image2template_directory
from Handlers.CommandLine import CommandLine
from Handlers.Flags import Flags
from Handlers.Streams import streams_off
from Handlers.Phil import PhilIndex

from Wrappers.Labelit.DistlSweepStrength import DistlSweepStrength

known_sweeps = { }

target_template = None

from xia2setup import is_image_name, is_xds_file

def get_sweep(f):

  global target_template
  global known_sweeps

  if not is_image_name(f):
    return

  if is_xds_file(f):
    return

  # in here, check the permissions on the file...

  if not os.access(f, os.R_OK):
    from Handlers.Streams import Debug
    Debug.write('No read permission for %s' % f)

  try:
    template, directory = image2template_directory(f)

    if target_template:
      if template != target_template:
        return

    key = (directory, template)
    if not known_sweeps.has_key(key):
      sweeplist = SweepFactory(template, directory)
      known_sweeps[key] = sweeplist

  except exceptions.Exception, e:
    from Handlers.Streams import Debug
    Debug.write('Exception: %s (%s)' % (str(e), f))
    # traceback.print_exc(file = sys.stdout)

  return

def visit(root, directory, files):
  files.sort()
  for f in files:
    get_sweep(os.path.join(directory, f))

def print_sweeps(out = sys.stdout):

  global known_sweeps

  sweeplists = known_sweeps.keys()
  sweeplists.sort()

  # analysis pass

  wavelengths = []

  min_images = PhilIndex.params.xia2.settings.input.min_images

  for sweep in sweeplists:
    sweeps = known_sweeps[sweep]
    # this should sort on exposure epoch ...?
    sweeps.sort()
    for s in sweeps:

      if len(s.get_images()) < min_images:
        continue

      wavelength = s.get_wavelength()

      if not wavelength in wavelengths:
        wavelengths.append(wavelength)

  wavelength_map = { }

  project = CommandLine.get_project_name()
  if not project:
    project = 'AUTOMATIC'

  crystal = CommandLine.get_crystal_name()
  if not crystal:
    crystal = 'DEFAULT'

  for j in range(len(wavelengths)):

    if len(wavelengths) == 1 and CommandLine.get_atom_name():
      name = 'SAD'
    elif len(wavelengths) == 1:
      name = 'NATIVE'
    else:
      name = 'WAVE%d' % (j + 1)

    wavelength_map[wavelengths[j]] = name

  j = 0

  out = sys.stdout

  nproc = Flags.get_parallel()

  for sweep in sweeplists:
    sweeps = known_sweeps[sweep]
    # this should sort on exposure epoch ...?
    sweeps.sort()
    for s in sweeps:

      # require at least n images to represent a sweep...

      if len(s.get_images()) < min_images:
        continue

      j += 1
      name = 'SWEEP%d' % j

      out.write('BEGIN SWEEP %s\n' % name)

      out.write('WAVELENGTH %s\n' % wavelength_map[s.get_wavelength()])

      out.write('DIRECTORY %s\n' % s.get_directory())
      out.write('IMAGE %s\n' % os.path.split(s.imagename(min(
          s.get_images())))[-1])

      d = DistlSweepStrength()
      if nproc > 1:
        d.add_command_line("nproc=%i" %nproc)
      #if 1:
        #d.add_command_line("minimum_spot_area=0")
        #d.add_command_line("minimum_signal_height=10")
        #d.add_command_line("minimum_spot_height=15")
      for i in s.get_images():
        d.set_image(s.imagename(i))
      d.run()


def rummage(path):
  '''Walk through the directories looking for sweeps.'''
  os.path.walk(path, visit, os.getcwd())
  return

def write_xinfo(filename, path, template = None):

  global target_template

  target_template = template

  crystal = CommandLine.get_crystal_name()

  if not crystal:
    crystal = 'DEFAULT'

  if not os.path.isabs(filename):
    filename = os.path.abspath(filename)

  directory = os.path.join(os.getcwd(), crystal, 'setup')

  try:
    os.makedirs(directory)
  except OSError, e:
    if not 'File exists' in str(e):
      raise e

  # FIXME should I have some exception handling in here...?

  start = os.getcwd()
  os.chdir(directory)

  # if we have given a template and directory on the command line, just
  # look there (i.e. not in the subdirectories)

  if CommandLine.get_template() and CommandLine.get_directory():
    visit(None, CommandLine.get_directory(),
          os.listdir(CommandLine.get_directory()))
  else:
    rummage(path)

  fout = open(filename, 'w')
  print_sweeps(fout)

  # change back directory c/f bug # 2693 - important for error files...
  os.chdir(start)

if __name__ == '__main__':

  streams_off()

  argv = sys.argv

  # test to see if sys.argv[-2] + path is a valid path - to work around
  # spaced command lines

  path = argv.pop()

  # perhaps move to a new directory...

  crystal = CommandLine.get_crystal_name()

  fout = open(os.path.join(os.getcwd(), 'automatic.xinfo'), 'w')

  if not crystal:
    crystal = 'DEFAULT'

  directory = os.path.join(os.getcwd(), crystal, 'setup')

  try:
    os.makedirs(directory)
  except OSError, e:
    if not 'File exists' in str(e):
      raise e

  os.chdir(directory)

  while not os.path.exists(path):
    path = '%s %s' % (argv.pop(), path)

  if not os.path.isabs(path):
    path = os.path.abspath(path)

  rummage(path)
  print_sweeps(fout)
