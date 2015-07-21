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
import time
import traceback

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'
if not 'XIA2CORE_ROOT' in os.environ:
  os.environ['XIA2CORE_ROOT'] = os.path.join(os.environ['XIA2_ROOT'], 'core')

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Experts.FindImages import image2template_directory
from Handlers.CommandLine import CommandLine
from Handlers.Flags import Flags
from Handlers.Phil import PhilIndex
from Wrappers.CCP4.Chooch import Chooch
from Modules.LabelitBeamCentre import compute_beam_centre
from Handlers.Streams import streams_off

known_image_extensions = ['img', 'mccd', 'mar2300', 'mar1200', 'mar1600',
                          'mar3450', 'osc', 'cbf', 'mar2000']

xds_file_names = ['ABS', 'ABSORP', 'BKGINIT', 'BKGPIX', 'BLANK', 'DECAY',
                  'X-CORRECTIONS', 'Y-CORRECTIONS', 'MODPIX', 'FRAME',
                  'GX-CORRECTIONS', 'GY-CORRECTIONS', 'DX-CORRECTIONS',
                  'DY-CORRECTIONS', 'GAIN']

known_sweeps = { }

known_scan_extensions = ['scan']

known_sequence_extensions = ['seq']

latest_sequence = None

latest_chooch = None

target_template = None

def is_scan_name(file):
  global known_scan_extensions

  if os.path.isfile(file):
    if file.split('.')[-1] in known_scan_extensions:
      return True

  return False

def is_sequence_name(file):
  global known_sequence_extensions

  if os.path.isfile(file):
    if file.split('.')[-1] in known_sequence_extensions:
      return True

  return False

def is_image_name(filename):

  global known_image_extensions
  from Wrappers.XDS.XDSFiles import XDSFiles

  if os.path.isfile(filename):

    if os.path.split(filename)[-1] in XDSFiles:
      return False

    # also XDS scaling files from previous xia2 job - hard coded, messy :o(
    for xds_file in 'ABSORP', 'DECAY', 'MODPIX':
      if os.path.join('scale', xds_file) in filename:
        return False

    exten = filename.split('.')[-1]
    if exten in known_image_extensions:
      return True

    # check for files like foo_bar.0001, through try to avoid filenames
    # like MSCServDetCCD.log.1
    end = filename.split('.')[-1]
    try:
      j = int(end)
      if not '.log.' in filename and len(end) > 1:
        return True
    except:
      pass

  return False

def is_xds_file(f):
  filename = os.path.split(f)[1]

  xds_files = ['ABS', 'ABSORP', 'BKGINIT', 'BKGPIX', 'BLANK', 'DECAY',
               'DX-CORRECTIONS', 'DY-CORRECTIONS', 'FRAME', 'GAIN',
               'GX-CORRECTIONS', 'GY-CORRECTIONS', 'MODPIX',
               'X-CORRECTIONS', 'Y-CORRECTIONS']

  return (filename.split('.')[0].split('_') in xds_files)

def get_template(f):

  global target_template

  if not is_image_name(f):
    return

  if is_xds_file(f):
    return

  # in here, check the permissions on the file...

  template = None
  directory = None

  if not os.access(f, os.R_OK):
    from Handlers.Streams import Debug
    Debug.write('No read permission for %s' % f)

  try:
    template, directory = image2template_directory(f)

    if target_template:
      if template not in target_template:
        return

  except Exception, e:
    from Handlers.Streams import Debug
    Debug.write('Exception: %s (%s)' % (str(e), f))
    Debug.write(traceback.format_exc())

  if template is None or directory is None:
    raise RuntimeError, 'template not recognised for %s' % f

  return os.path.join(directory, template)


def save_datablock(filename):
  from Schema import imageset_cache
  from dxtbx.datablock import DataBlock
  from dxtbx.serialize import dump

  datablock = DataBlock([])
  for imagesets in imageset_cache.values():
    for imageset in imagesets.values():
      datablock.append(imageset)

  dump.datablock(datablock, filename)


def parse_sequence(sequence_file):
  sequence = ''

  for record in open(sequence_file).readlines():
    if record[0].upper() in \
       'ABCDEFGHIJKLMNOPQRSTUVWXYZ ':
      sequence += record.strip().upper()

  global latest_sequence
  latest_sequence = sequence
  return

def visit(root, directory, files):
  files.sort()

  templates = set()

  for f in files:

    full_path = os.path.join(directory, f)
    if is_image_name(full_path):
      try:
        template = get_template(full_path)
      except Exception, e:
        from Handlers.Streams import Debug
        Debug.write('Exception: %s' %str(e))
        Debug.write(traceback.format_exc())
        continue
      if template is not None:
        templates.add(template)

    if is_scan_name(full_path):
      global latest_chooch
      try:
        latest_chooch = Chooch()
        if CommandLine.get_atom_name():
          latest_chooch.set_atom(CommandLine.get_atom_name())
        latest_chooch.set_scan(full_path)
        latest_chooch.scan()
      except:
        latest_chooch = None

    if is_sequence_name(full_path):
      parse_sequence(full_path)

  return templates

def print_sweeps(out = sys.stdout):

  global known_sweeps, latest_sequence

  sweeplists = known_sweeps.keys()
  assert len(sweeplists) > 0, "no sweeps found"
  sweeplists.sort()

  # sort sweeplist based on epoch of first image of each sweep
  import operator
  epochs = [known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()[0]
            for sweep in sweeplists]

  if len(epochs) != len(set(epochs)):
    from Handlers.Streams import Debug
    Debug.write('Duplicate epochs found. Trying to correct epoch information.')
    cumulativedelta = 0.0
    for sweep in sweeplists:
      known_sweeps[sweep][0].get_imageset().get_scan().set_epochs(
        known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()
        + cumulativedelta)
      # could change the image epoch information individually, but only
      # the information from the first image is used at this time.
      cumulativedelta += sum(
        known_sweeps[sweep][0].get_imageset().get_scan().get_exposure_times())
    epochs = [known_sweeps[sweep][0].get_imageset().get_scan().get_epochs()[0]
            for sweep in sweeplists]

    if len(epochs) != len(set(epochs)):
      Debug.write('Duplicate epoch information remains.')
    # This should only happen with incorrect exposure time information.

  sweeplists, epochs = zip(*sorted(zip(sweeplists, epochs),
    key=operator.itemgetter(1)))

  # analysis pass

  wavelengths = []

  params = PhilIndex.get_python_object()
  wavelength_tolerance = params.xia2.settings.wavelength_tolerance
  min_images = params.xia2.settings.input.min_images
  min_oscillation_range = params.xia2.settings.input.min_oscillation_range

  for sweep in sweeplists:
    sweeps = known_sweeps[sweep]
    # this should sort on exposure epoch ...?
    sweeps.sort()
    for s in sweeps:

      if len(s.get_images()) < min_images:
        from Handlers.Streams import Debug
        Debug.write('Rejecting sweep %s:' %s.get_template())
        Debug.write('  Not enough images (found %i, require at least %i)'
                    %(len(s.get_images()), min_images))
        continue

      oscillation_range = s.get_imageset().get_scan().get_oscillation_range()
      width = oscillation_range[1]-oscillation_range[0]
      if width < min_oscillation_range:
        from Handlers.Streams import Debug
        Debug.write('Rejecting sweep %s:' %s.get_template())
        Debug.write('  Too narrow oscillation range (found %i, require at least %i)'
                    %(width, min_oscillation_range))
        continue

      wavelength = s.get_wavelength()

      if not wavelength in wavelengths:
        have_wavelength = False
        for w in wavelengths:
          if abs(w - wavelength) < wavelength_tolerance:
            have_wavelength = True
            s.set_wavelength(w)
        if not have_wavelength:
          wavelengths.append(wavelength)

  assert len(wavelengths), "No sweeps found matching criteria"

  wavelength_map = { }

  project = CommandLine.get_project_name()
  if not project:
    project = 'AUTOMATIC'

  crystal = CommandLine.get_crystal_name()
  if not crystal:
    crystal = 'DEFAULT'

  out.write('BEGIN PROJECT %s\n' % project)
  out.write('BEGIN CRYSTAL %s\n' % crystal)

  out.write('\n')

  # check to see if a user spacegroup has been assigned - if it has,
  # copy it in...

  settings = PhilIndex.params.xia2.settings

  if settings.space_group is not None:
    out.write(
      'USER_SPACEGROUP %s\n' % settings.space_group.type().lookup_symbol())
    out.write('\n')

  if settings.unit_cell is not None:
    out.write('USER_CELL %.2f %.2f %.2f %.2f %.2f %.2f\n' % \
              settings.unit_cell.parameters())
    out.write('\n')

  if Flags.get_freer_file():
    out.write('FREER_FILE %s\n' % Flags.get_freer_file())
    out.write('\n')

  if latest_sequence:
    out.write('BEGIN AA_SEQUENCE\n')
    out.write('\n')
    for sequence_chunk in [latest_sequence[i:i + 60] \
                           for i in range(0, len(latest_sequence), 60)]:
      out.write('%s\n' % sequence_chunk)
    out.write('\n')
    out.write('END AA_SEQUENCE\n')
    out.write('\n')

  if CommandLine.get_atom_name():
    out.write('BEGIN HA_INFO\n')
    out.write('ATOM %s\n' % CommandLine.get_atom_name().lower())
    if CommandLine.get_atom_name().lower() == 'se' and latest_sequence:
      # assume that this is selenomethionine
      out.write('! If this is SeMet uncomment next line...\n')
      out.write('!NUMBER_PER_MONOMER %d\n' % latest_sequence.count('M'))
      out.write('!NUMBER_TOTAL M\n')
    else:
      out.write('!NUMBER_PER_MONOMER N\n')
      out.write('!NUMBER_TOTAL M\n')
    out.write('END HA_INFO\n')
    out.write('\n')

  for j in range(len(wavelengths)):

    global latest_chooch

    if latest_chooch:
      name = latest_chooch.id_wavelength(wavelengths[j])
      first_name = name
      counter = 1

      while name in [wavelength_map[w] for w in wavelength_map]:
        counter += 1
        name = '%s%d' % (first_name, counter)

      fp, fpp = latest_chooch.get_fp_fpp(wavelengths[j])
    else:
      fp, fpp = 0.0, 0.0
      if len(wavelengths) == 1 and CommandLine.get_atom_name():
        name = 'SAD'
      elif len(wavelengths) == 1:
        name = 'NATIVE'
      else:
        name = 'WAVE%d' % (j + 1)

    wavelength_map[wavelengths[j]] = name

    out.write('BEGIN WAVELENGTH %s\n' % name)

    dmin = Flags.get_resolution_high()
    dmax = Flags.get_resolution_low()

    if dmin and dmax:
      out.write('RESOLUTION %f %f\n' % (dmin, dmax))
    elif dmin:
      out.write('RESOLUTION %f\n' % dmin)

    out.write('WAVELENGTH %f\n' % wavelengths[j])
    if fp != 0.0 and fpp != 0.0:
      out.write('F\' %5.2f\n' % fp)
      out.write('F\'\' %5.2f\n' % fpp)

    out.write('END WAVELENGTH %s\n' % name)
    out.write('\n')

  j = 0
  for sweep in sweeplists:
    sweeps = known_sweeps[sweep]
    # this should sort on exposure epoch ...?
    sweeps.sort()
    for s in sweeps:

      # require at least n images to represent a sweep...
      if len(s.get_images()) < min_images:
        from Handlers.Streams import Debug
        Debug.write('Rejecting sweep %s:' %s.get_template())
        Debug.write('  Not enough images (found %i, require at least %i)'
                    %(len(s.get_images()), min_images))
        continue

      oscillation_range = s.get_imageset().get_scan().get_oscillation_range()
      width = oscillation_range[1]-oscillation_range[0]
      if width < min_oscillation_range:
        from Handlers.Streams import Debug
        Debug.write('Rejecting sweep %s:' %s.get_template())
        Debug.write('  Too narrow oscillation range (found %i, require at least %i)'
                    %(width, min_oscillation_range))
        continue

      j += 1
      name = 'SWEEP%d' % j

      out.write('BEGIN SWEEP %s\n' % name)

      if Flags.get_reversephi():
        out.write('REVERSEPHI\n')

      out.write('WAVELENGTH %s\n' % wavelength_map[s.get_wavelength()])

      out.write('DIRECTORY %s\n' % s.get_directory())
      out.write('IMAGE %s\n' % os.path.split(s.imagename(min(
          s.get_images())))[-1])

      if Flags.get_start_end():
        start, end = Flags.get_start_end()

        if start < min(s.get_images()):
          raise RuntimeError, 'requested start %d < %d' % \
                (start, min(s.get_images()))

        if end > max(s.get_images()):
          raise RuntimeError, 'requested end %d > %d' % \
                (end, max(s.get_images()))

        out.write('START_END %d %d\n' % (start, end))
      elif CommandLine.get_start_end(
              os.path.join(s.get_directory(), s.get_template())):
        start_end = CommandLine.get_start_end(
              os.path.join(s.get_directory(), s.get_template()))
        out.write('START_END %d %d\n' % start_end)
      else:
        out.write('START_END %d %d\n' % (min(s.get_images()),
                                         max(s.get_images())))

      # really don't need to store the epoch in the xinfo file
      # out.write('EPOCH %d\n' % int(s.get_collect()[0]))
      user_beam_centre = settings.beam_centre
      if user_beam_centre is not None:
        out.write('BEAM %6.2f %6.2f\n' % tuple(user_beam_centre))
      elif not settings.trust_beam_centre:
        interactive = Flags.get_interactive()
        Flags.set_interactive(False)
        beam_centre = compute_beam_centre(s)
        if beam_centre:
          out.write('BEAM %6.2f %6.2f\n' % tuple(beam_centre))
        Flags.set_interactive(interactive)

      if settings.detector_distance is not None:
        out.write('DISTANCE %.2f\n' % settings.detector_distance)

      out.write('END SWEEP %s\n' % name)

      out.write('\n')

  out.write('END CRYSTAL %s\n' % crystal)
  out.write('END PROJECT %s\n' % project)


def get_sweeps(templates):
  global known_sweeps

  from libtbx import easy_mp
  from Handlers.Phil import PhilIndex
  from xia2setup_helpers import get_sweep
  params = PhilIndex.get_python_object()
  mp_params = params.xia2.settings.multiprocessing
  nproc = mp_params.nproc

  if params.xia2.settings.read_all_image_headers and nproc > 1:
    method = "multiprocessing"

    # If xia2 was a proper cctbx module, then we wouldn't have to do this
    # FIXME xia2 is now a proper cctbx module ;o)

    python_path = 'PYTHONPATH="%s"' %":".join(sys.path)
    qsub_command="qsub -v %s -V" %python_path

    args = [(template,) for template in templates]
    results_list = easy_mp.parallel_map(
      get_sweep, args,
      processes=nproc,
      method=method,
      qsub_command=qsub_command,
      asynchronous=True,
      preserve_order=True,
      preserve_exception_message=True)

  else:
    results_list = [get_sweep((template,)) for template in templates]

  from Schema import imageset_cache
  from libtbx.containers import OrderedDict

  for template, sweeplist in zip(templates, results_list):
    if sweeplist is not None:
      known_sweeps[template] = sweeplist
      for sweep in sweeplist:
        imageset = sweep.get_imageset()
        if template not in imageset_cache:
          imageset_cache[template] = OrderedDict()
        imageset_cache[template][
          imageset.get_scan().get_image_range()[0]] = imageset


def rummage(directories):
  '''Walk through the directories looking for sweeps.'''
  templates = set()
  for path in directories:
    for root, dirs, files in os.walk(path, followlinks=True):
      templates.update(visit(os.getcwd(), root, files))

  get_sweeps(templates)

  return

def write_xinfo(filename, directories, template=None):

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
    templates = set()
    for directory in CommandLine.get_directory():
      templates.update(visit(None, directory, os.listdir(directory)))
    get_sweeps(templates)
  else:
    rummage(directories)

  save_datablock(os.path.join(start, 'xia2-datablock.json'))

  fout = open(filename, 'w')
  print_sweeps(fout)

  # change back directory c/f bug # 2693 - important for error files...
  os.chdir(start)

  return

def run():
  streams_off()

  # test to see if sys.argv[-2] + path is a valid path - to work around
  # spaced command lines

  argv = CommandLine.get_argv()

  if not CommandLine.get_directory():

    directories = []

    for arg in argv:
      if os.path.isdir(arg):
        directories.append(os.path.abspath(arg))

    if len(directories) == 0:
      raise RuntimeError('directory not found in arguments')

  else:
    directories = [CommandLine.get_directory()]

  directories = [os.path.abspath(d) for d in directories]

  # perhaps move to a new directory...

  crystal = CommandLine.get_crystal_name()

  fout = open(os.path.join(os.getcwd(), 'automatic.xinfo'), 'w')

  if not crystal:
    crystal = 'DEFAULT'

  start = os.path.abspath(os.getcwd())

  directory = os.path.join(os.getcwd(), crystal, 'setup')

  try:
    os.makedirs(directory)
  except OSError, e:
    if not 'File exists' in str(e):
      raise e

  os.chdir(directory)

  rummage(directories)
  print_sweeps(fout)

  save_datablock(os.path.join(start, 'xia2-datablock.json'))

if __name__ == '__main__':
  run()
