#!/usr/bin/env python
# CommandLine.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 12th June 2006
#
# A handler for all of the information which may be passed in on the command
# line. This singleton object should be able to handle the input, structure
# it and make it available in a useful fashion.
#
# This is a hook into a global data repository, should mostly be replaced with
# a Phil interface.

import sys
import os
import exceptions
import copy
import traceback

from xia2.Experts.FindImages import image2template_directory
from xia2.Schema.XProject import XProject
from xia2.Handlers.Flags import Flags
from xia2.Handlers.Phil import PhilIndex
from xia2.Handlers.Streams import Chatter, Debug
from xia2.Handlers.PipelineSelection import add_preference, get_preferences

from libtbx.utils import Sorry

def which(pgm):
  # python equivalent to the 'which' command
  # http://stackoverflow.com/questions/9877462/is-there-a-python-equivalent-to-the-which-command
  # FIXME this will not work on Windows as you need to check that there is a
  # .bat or a .exe extension
  # FIXME also this is implemented in Driver/DriverHelper.py:executable_exists
  path = os.getenv('PATH')
  for p in path.split(os.path.pathsep):
    p = os.path.join(p,pgm)
    if os.path.exists(p) and os.access(p, os.X_OK):
      return p


def load_datablock(filename):
  from xia2.Schema import imageset_cache, update_with_reference_geometry
  from dxtbx.serialize import load
  from libtbx.containers import OrderedDict

  datablocks = load.datablock(filename, check_format=False)

  for datablock in datablocks:
    imagesets = datablock.extract_imagesets()
    params = PhilIndex.get_python_object()
    reference_geometry = params.xia2.settings.input.reference_geometry
    if reference_geometry is not None and len(reference_geometry) > 0:
      update_with_reference_geometry(imagesets, reference_geometry)
    for imageset in imagesets:
      template = imageset.get_template()
      if template not in imageset_cache:
        imageset_cache[template] = OrderedDict()
      imageset_cache[template][
        imageset.get_scan().get_image_range()[0]] = imageset


class _CommandLine(object):
  '''A class to represent the command line input.'''

  def __init__(self):
    '''Initialise all of the information from the command line.'''

    self._argv = []
    self._understood = []

    self._default_template = []
    self._default_directory = []
    self._hdf5_master_files = []
    self._default_start_end = { }

    # deprecated options prior to removal
    self._xinfo = None

    return

  def get_argv(self):
    return self._argv

  def print_command_line(self):
    cl = self.get_command_line()
    Chatter.write('Command line: %s' % cl)
    return

  def get_command_line(self):
    import libtbx.load_env
    cl = libtbx.env.dispatcher_name
    if cl:
      if 'xia2' not in cl or 'python' in cl:
        cl = 'xia2'
    else:
      cl = 'xia2'

    for arg in sys.argv[1:]:
      if ' ' in arg:
        arg = '"%s"' %arg
      cl += ' %s' % arg

    return cl

  def setup(self):
    '''Set everything up...'''

    # check arguments are all ascii

    for token in sys.argv:
      try:
        token.encode('ascii')
      except UnicodeDecodeError, e:
        raise RuntimeError, 'non-ascii characters in input'

    self._argv = copy.deepcopy(sys.argv)

    replacements = { '-2d': 'pipeline=2d',
                     '-2di': 'pipeline=2di',
                     '-3d': 'pipeline=3d',
                     '-3di': 'pipeline=3di',
                     '-3dii': 'pipeline=3dii',
                     '-3dd': 'pipeline=3dd',
                     '-dials': 'pipeline=dials' }
    for k, v in replacements.iteritems():
      if k in self._argv:
        print "***\nCommand line option %s is deprecated. Please use %s instead\n***" % (k, v)
        self._argv[self._argv.index(k)] = v

    # first of all try to interpret arguments as phil parameters/files

    from xia2.Handlers.Phil import master_phil
    from libtbx.phil import command_line
    cmd_line = command_line.argument_interpreter(master_phil=master_phil)
    working_phil, self._argv = cmd_line.process_and_fetch(
      args=self._argv, custom_processor="collect_remaining")

    PhilIndex.merge_phil(working_phil)
    try:
      params = PhilIndex.get_python_object()
    except RuntimeError, e:
      raise Sorry(e)

    # things which are single token flags...

    self._read_interactive()
    self._read_ice()
    self._read_trust_timestamps()
    self._read_batch_scale()
    self._read_small_molecule()
    self._read_quick()
    self._read_mask()
    self._read_no_lattice_test()
    self._read_no_relax()

    # pipeline options
    self._read_pipeline()

    Debug.write('Project: %s' % params.xia2.settings.project)
    Debug.write('Crystal: %s' % params.xia2.settings.crystal)

    try:
      self._read_phil()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_phil(), str(e))

    try:
      self._read_pickle()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_pickle(), str(e))

    try:
      self._read_xparallel()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_xparallel(), str(e))

    try:
      self._read_z_min()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_z_min(), str(e))

    try:
      self._read_aimless_secondary()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_aimless_secondary(), str(e))

    try:
      self._read_rejection_threshold()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_rejection_threshold(), str(e))

    try:
      self._read_microcrystal()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_microcrystal(), str(e))

    try:
      self._read_scale_model()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_scale_model(), str(e))

    # FIXME add some consistency checks in here e.g. that there are
    # images assigned, there is a lattice assigned if cell constants
    # are given and so on

    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing
    from libtbx import Auto
    if mp_params.mode == 'parallel':
      if mp_params.type == 'qsub':
        if which('qsub') is None:
          raise Sorry('qsub not available')
      if mp_params.njob is Auto:
        from xia2.Handlers.Environment import get_number_cpus
        mp_params.njob = get_number_cpus()
        if mp_params.nproc is Auto:
          mp_params.nproc = 1
      elif mp_params.nproc is Auto:
        from xia2.Handlers.Environment import get_number_cpus
        mp_params.nproc = get_number_cpus()
        Flags.set_parallel(mp_params.nproc)
      else:
        Flags.set_parallel(mp_params.nproc)
    elif mp_params.mode == 'serial':
      mp_params.njob = 1
      if mp_params.nproc is Auto:
        from xia2.Handlers.Environment import get_number_cpus
        mp_params.nproc = get_number_cpus()
      Flags.set_parallel(mp_params.nproc)

    PhilIndex.update("xia2.settings.multiprocessing.njob=%d" %mp_params.njob)
    PhilIndex.update("xia2.settings.multiprocessing.nproc=%d" %mp_params.nproc)
    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing

    if params.xia2.settings.indexer is not None:
      add_preference("indexer", params.xia2.settings.indexer)
    if params.xia2.settings.multi_sweep_indexing is Auto:
      params.xia2.settings.multi_sweep_indexing = \
        Flags.get_small_molecule() and 'dials' == params.xia2.settings.indexer
    if params.xia2.settings.refiner is not None:
      add_preference("refiner", params.xia2.settings.refiner)
    if params.xia2.settings.integrater is not None:
      add_preference("integrater", params.xia2.settings.integrater)
    if params.xia2.settings.scaler is not None:
      add_preference("scaler", params.xia2.settings.scaler)

    if params.xia2.settings.resolution.d_min is not None:
      Flags.set_resolution_high(params.xia2.settings.resolution.d_min)
    if params.xia2.settings.resolution.d_max is not None:
      Flags.set_resolution_low(params.xia2.settings.resolution.d_max)

    Flags.set_reversephi(params.xia2.settings.input.reverse_phi)

    input_json = params.xia2.settings.input.json
    if (input_json is not None and len(input_json)):
      for json_file in input_json:
        assert os.path.isfile(json_file)
        load_datablock(json_file)

    reference_geometry = params.xia2.settings.input.reference_geometry
    if reference_geometry is not None and len(reference_geometry) > 0:
      reference_geometries = "\n".join(
        ["xia2.settings.input.reference_geometry=%s" % os.path.abspath(g)
          for g in params.xia2.settings.input.reference_geometry])
      Debug.write(reference_geometries)
      PhilIndex.update(reference_geometries)
      Debug.write("xia2.settings.trust_beam_centre=true")
      PhilIndex.update("xia2.settings.trust_beam_centre=true")
      params = PhilIndex.get_python_object()

    params = PhilIndex.get_python_object()
    if params.xia2.settings.input.xinfo is not None:
      xinfo_file = os.path.abspath(params.xia2.settings.input.xinfo)
      PhilIndex.update("xia2.settings.input.xinfo=%s" %xinfo_file)
      params = PhilIndex.get_python_object()
      self.set_xinfo(xinfo_file)

      Debug.write(60 * '-')
      Debug.write('XINFO file: %s' % xinfo_file)
      for record in open(xinfo_file, 'r').readlines():
        # don't want \n on the end...
        Debug.write(record[:-1])
      Debug.write(60 * '-')
    else:
      xinfo_file = '%s/automatic.xinfo' %os.path.abspath(
        os.curdir)
      PhilIndex.update("xia2.settings.input.xinfo=%s" %xinfo_file)
      params = PhilIndex.get_python_object()

    if params.dials.find_spots.phil_file is not None:
      PhilIndex.update("dials.find_spots.phil_file=%s" %os.path.abspath(
        params.dials.find_spots.phil_file))
    if params.dials.index.phil_file is not None:
      PhilIndex.update("dials.index.phil_file=%s" %os.path.abspath(
        params.dials.index.phil_file))
    if params.dials.refine.phil_file is not None:
      PhilIndex.update("dials.refine.phil_file=%s" %os.path.abspath(
        params.dials.refine.phil_file))
    if params.dials.integrate.phil_file is not None:
      PhilIndex.update("dials.integrate.phil_file=%s" %os.path.abspath(
        params.dials.integrate.phil_file))
    if params.xds.index.xparm is not None:
      Flags.set_xparm(params.xds.index.xparm)
    if params.xds.index.xparm_ub is not None:
      Flags.set_xparm_ub(params.xds.index.xparm_ub)
    if params.xia2.settings.scale.freer_file is not None:
      Flags.set_freer_file(params.xia2.settings.scale.freer_file)
      Debug.write('FreeR_flag column taken from %s' %Flags.get_freer_file())
    if params.xia2.settings.scale.free_fraction is not None:
      Flags.set_free_fraction(params.xia2.settings.scale.free_fraction)
      Debug.write('Free fraction set to %f' %Flags.get_free_fraction())
    if params.xia2.settings.scale.free_total is not None:
      Flags.set_free_total(params.xia2.settings.scale.free_total)
      Debug.write('Free total set to %f' %Flags.get_free_total())
    if params.xia2.settings.scale.reference_reflection_file is not None:
      Flags.set_reference_reflection_file(
        params.xia2.settings.scale.reference_reflection_file)
      Debug.write(
        'FreeR_flag column taken from %s' %Flags.get_reference_reflection_file())

    params = PhilIndex.get_python_object()

    datasets = PhilIndex.params.xia2.settings.input.image
    for dataset in datasets:

      start_end = None

      if ':' in dataset:
        tokens = dataset.split(':')
        # cope with windows drives i.e. C:\data\blah\thing_0001.cbf:1:100
        if len(tokens[0]) == 1:
          tokens = ['%s:%s' % (tokens[0], tokens[1])] + tokens[2:]
        if len(tokens) != 3:
          raise RuntimeError, '/path/to/image_0001.cbf:start:end'

        dataset = tokens[0]
        start_end = int(tokens[1]), int(tokens[2])

      from xia2.Applications.xia2setup import is_hd5f_name
      if is_hd5f_name(dataset):
        self._hdf5_master_files.append(os.path.abspath(dataset))
        if start_end:
          Debug.write('Image range: %d %d' % start_end)
          self._default_start_end[dataset] = start_end
        else:
          Debug.write('No image range specified')

      else:
        template, directory = image2template_directory(os.path.abspath(dataset))

        self._default_template.append(template)
        self._default_directory.append(directory)

        Debug.write('Interpreted from image %s:' % dataset)
        Debug.write('Template %s' % template)
        Debug.write('Directory %s' % directory)

        if start_end:
          Debug.write('Image range: %d %d' % start_end)
          self._default_start_end[os.path.join(directory, template)] = start_end
        else:
          Debug.write('No image range specified')

    # finally, check that all arguments were read and raise an exception
    # if any of them were nonsense.

    with open('xia2-working.phil', 'wb') as f:
      print >> f, PhilIndex.working_phil.as_str()
    with open('xia2-diff.phil', 'wb') as f:
      print >> f, PhilIndex.get_diff().as_str()

    Debug.write('\nDifference PHIL:')
    Debug.write(PhilIndex.get_diff().as_str(), strip=False)

    Debug.write('Working PHIL:')
    Debug.write(PhilIndex.working_phil.as_str(), strip=False)

    nonsense = 'Unknown command-line options:'
    was_nonsense = False

    for j, argv in enumerate(self._argv):
      if j == 0:
        continue
      if argv[0] != '-' and '=' not in argv:
        continue
      if not j in self._understood:
        nonsense += ' %s' % argv
        was_nonsense = True

    if was_nonsense:
      raise RuntimeError, nonsense

    return

  # command line parsers, getters and help functions.

  def get_beam(self):
    return self._beam

  def _read_phil(self):
    try:
      index = self._argv.index('-phil')

    except ValueError, e:
      return

    Chatter.bigbanner('-phil option now no longer needed: '
                      'please just place file on command-line', size=80)

    self._understood.append(index)

    if True:
      return

    PhilIndex.merge_param_file(self._argv[index + 1])
    PhilIndex.get_python_object()

    self._understood.append(index + 1)

    Debug.write('Phil file: %s' % self._argv[index + 1])

    return

  def _help_phil(self):
    return '-phil parameters.phil'

  def set_xinfo(self, xinfo):
    with open(xinfo, 'rb') as f:
      Debug.write('\n' + xinfo)
      Debug.write(f.read())
    self._xinfo = XProject(xinfo)

  def get_xinfo(self):
    '''Return the XProject.'''
    return self._xinfo

  def _read_xparallel(self):
    try:
      index = self._argv.index('-xparallel')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_xparallel(int(self._argv[index + 1]))
    Debug.write('XParallel set to %d' % Flags.get_xparallel())

    return

  def _help_xparallel(self):
    return '-xparallel N'

  def _read_z_min(self):
    try:
      index = self._argv.index('-z_min')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_z_min(float(self._argv[index + 1]))
    Debug.write('Z min set to %f' % Flags.get_z_min())

    return

  def _help_z_min(self):
    return '-z_min N'

  def _read_aimless_secondary(self):
    try:
      index = self._argv.index('-aimless_secondary')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_aimless_secondary(float(self._argv[index + 1]))
    Debug.write('Aimless secondary set to %f' % Flags.get_aimless_secondary())

    return

  def _help_aimless_secondary(self):
    return '-aimless_secondary N'

  def _read_rejection_threshold(self):
    try:
      index = self._argv.index('-rejection_threshold')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_rejection_threshold(float(self._argv[index + 1]))
    Debug.write('Rejection threshold set to %f' % \
                Flags.get_rejection_threshold())

    return

  def _help_rejection_threshold(self):
    return '-rejection_threshold N'

  def _read_microcrystal(self):

    if '-microcrystal' in self._argv:
      Flags.set_microcrystal()
      Debug.write('Microcrystal mode on')
      self._understood.append(self._argv.index('-microcrystal'))

  def _read_pickle(self):
    try:
      index = self._argv.index('-pickle')
    except ValueError, e:
      self._pickle = None
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)
    Flags.set_pickle(self._argv[index + 1])

  def _help_pickle(self):
    return '-pickle name.pkl'

  def get_template(self):
    return self._default_template

  def get_start_end(self, full_template):
    return self._default_start_end.get(full_template)

  def get_directory(self):
    return self._default_directory

  def get_hdf5_master_files(self):
    return self._hdf5_master_files

  def _read_trust_timestamps(self):

    if '-trust_timestamps' in self._argv:
      Flags.set_trust_timestamps(True)
      Debug.write('Trust timestamps on')
      self._understood.append(self._argv.index('-trust_timestamps'))

  def _read_batch_scale(self):

    if '-batch_scale' in self._argv:
      Flags.set_batch_scale(True)
      Debug.write('Batch scaling mode on')
      self._understood.append(self._argv.index('-batch_scale'))

    return

  def _read_small_molecule(self):

    if '-small_molecule' in self._argv:
      Flags.set_small_molecule(True)
      Debug.write('Small molecule selected')
      self._understood.append(self._argv.index('-small_molecule'))
      settings = PhilIndex.get_python_object().xia2.settings
      PhilIndex.update("xia2.settings.unify_setting=true")

    return

  def _read_scale_model(self):
    try:
      index = self._argv.index('-scale_model')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_scale_model(self._argv[index + 1])
    Debug.write('Scaling model set to: %s' % Flags.get_scale_model())

  def _read_quick(self):

    if '-quick' in self._argv:
      Flags.set_quick(True)
      Debug.write('Quick mode selected')
      self._understood.append(self._argv.index('-quick'))

  def _read_no_lattice_test(self):

    if '-no_lattice_test' in self._argv:
      Flags.set_no_lattice_test(True)
      self._understood.append(self._argv.index('-no_lattice_test'))
      Debug.write('No lattice test mode selected')

  def _read_no_relax(self):

    if '-no_relax' in self._argv:
      Flags.set_relax(False)
      self._understood.append(self._argv.index('-no_relax'))
      Debug.write('XDS relax about indexing selected')

  def _read_pipeline(settings):
    settings = PhilIndex.get_python_object().xia2.settings
    indexer, refiner, integrater, scaler = None, None, None, None
    if settings.pipeline == '2d':
      Debug.write('2DA pipeline selected')
      indexer, refiner, integrater, scaler = 'mosflm', 'mosflm', 'mosflmr', 'ccp4a'
    elif settings.pipeline == '2di':
      Debug.write('2DA pipeline; mosflm indexing selected')
      indexer, refiner, integrater, scaler = 'mosflm', 'mosflm', 'mosflmr', 'ccp4a'
    elif settings.pipeline == '3d':
      Debug.write('3DR pipeline selected')
      indexer, refiner, integrater, scaler = 'xds', 'xds', 'xdsr', 'xdsa'
    elif settings.pipeline == '3di':
      Debug.write('3DR pipeline; XDS indexing selected')
      indexer, refiner, integrater, scaler = 'xds', 'xds', 'xdsr', 'xdsa'
    elif settings.pipeline == '3dii':
      Debug.write('3D II R pipeline (XDS IDXREF all images) selected')
      indexer, refiner, integrater, scaler = 'xdsii', 'xds', 'xdsr', 'xdsa'
    elif settings.pipeline == '3dd':
      Debug.write('3DD pipeline (DIALS indexing) selected')
      indexer, refiner, integrater, scaler = 'dials', 'xds', 'xdsr', 'xdsa'
    elif settings.pipeline == 'dials':
      Debug.write('DIALS pipeline selected')
      indexer, refiner, integrater, scaler = 'dials', 'dials', 'dials', 'ccp4a'

    if indexer is not None and settings.indexer is None:
      PhilIndex.update("xia2.settings.indexer=%s" % indexer)
    if refiner is not None and settings.refiner is None:
      PhilIndex.update("xia2.settings.refiner=%s" % refiner)
    if integrater is not None and settings.integrater is None:
      PhilIndex.update("xia2.settings.integrater=%s" % integrater)
    if scaler is not None and settings.scaler is None:
      PhilIndex.update("xia2.settings.scaler=%s" % scaler)

  def _read_interactive(self):

    if '-interactive' in self._argv:
      Flags.set_interactive(True)
      self._understood.append(self._argv.index('-interactive'))
      Debug.write('Interactive indexing ON')

  def _read_ice(self):

    if '-ice' in self._argv:
      Flags.set_ice(True)
      self._understood.append(self._argv.index('-ice'))
      Debug.write('Ice ring exclusion ON')

  def _read_mask(self):
    try:
      index = self._argv.index('-mask')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)
    Flags.set_mask(self._argv[index + 1])

  def get_mask(self):
    return self._mask

  def _help_mask(self):
    return '-mask mask.dat'

  def get_mask(self):
    return self._mask

CommandLine = _CommandLine()
CommandLine.setup()

if __name__ == '__main__':
  print CommandLine.get_beam()
  print CommandLine.get_xinfo()
