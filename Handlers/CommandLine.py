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

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'
if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT']))

from Experts.FindImages import image2template_directory
from Schema.XProject import XProject
from Handlers.Flags import Flags
from Handlers.Phil import PhilIndex
from Handlers.Streams import Chatter, Debug
from Handlers.PipelineSelection import add_preference, get_preferences
from Handlers.Executables import Executables

from libtbx.utils import Sorry

def which(pgm):
  # python equivalent to the 'which' command
  # http://stackoverflow.com/questions/9877462/is-there-a-python-equivalent-to-the-which-command
  path = os.getenv('PATH')
  for p in path.split(os.path.pathsep):
    p = os.path.join(p,pgm)
    if os.path.exists(p) and os.access(p,os.X_OK):
      return p


def load_datablock(filename):
  from Schema import imageset_cache, update_with_reference_geometry
  from dxtbx.serialize import load
  from libtbx.containers import OrderedDict

  datablocks = load.datablock(filename, check_format=False)

  for datablock in datablocks:
    imagesets = datablock.extract_imagesets()
    params = PhilIndex.get_python_object()
    reference_geometry = params.xia2.settings.input.reference_geometry
    if reference_geometry is not None:
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

    # first of all try to interpret arguments as phil parameters/files

    from Handlers.Phil import master_phil
    from libtbx.phil import command_line
    cmd_line = command_line.argument_interpreter(master_phil=master_phil)
    working_phil, self._argv = cmd_line.process_and_fetch(
      args=self._argv, custom_processor="collect_remaining")

    PhilIndex.merge_phil(working_phil)
    try:
      PhilIndex.get_python_object()
    except RuntimeError, e:
      raise Sorry(e)
    #PhilIndex.get_diff().show()

    # things which are single token flags...


    self._read_debug()
    self._read_interactive()
    self._read_ice()
    self._read_egg()
    self._read_uniform_sd()
    self._read_trust_timestamps()
    self._read_batch_scale()
    self._read_small_molecule()
    self._read_quick()
    self._read_chef()
    self._read_mask()
    self._read_reversephi()
    self._read_no_lattice_test()
    self._read_no_relax()
    self._read_no_profile()
    self._read_norefine()
    self._read_noremove()

    # pipeline options

    self._read_2d()
    self._read_2di()
    self._read_dials()
    self._read_3d()
    self._read_3di()
    self._read_3dii()
    self._read_3dd()

    self._read_migrate_data()
    self._read_zero_dose()
    self._read_free_fraction()
    self._read_free_total()

    # finer grained control over the selection of indexer, integrater
    # and scaler to use.

    self._read_indexer()
    self._read_integrater()
    self._read_scaler()
    self._read_executables()

    # flags relating to unfixed bugs...
    self._read_fixed_628()

    try:
      self._read_beam()
    except:
      raise RuntimeError, self._help_beam()

    try:
      self._read_cell()
    except:
      raise RuntimeError, self._help_cell()

    try:
      self._read_image()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_image(), str(e))

    try:
      self._read_project_name()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_project_name(), str(e))

    try:
      self._read_atom_name()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_atom_name(), str(e))

    try:
      self._read_phil()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_phil(), str(e))

    try:
      self._read_crystal_name()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_crystal_name(), str(e))

    try:
      self._read_ispyb_xml_out()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_ispyb_xml_out(), str(e))

    try:
      self._read_hdr_in()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_hdr_in(), str(e))

    try:
      self._read_hdr_out()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_hdr_out(), str(e))

    try:
      self._read_pickle()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_pickle(), str(e))

    try:
      self._read_parallel()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_parallel(), str(e))

    try:
      self._read_serial()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_serial(), str(e))

    try:
      self._read_xparm()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_xparm(), str(e))

    try:
      self._read_xparm_ub()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_xparm_ub(), str(e))

    try:
      self._read_min_images()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_min_images(), str(e))

    try:
      self._read_start_end()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_start_end(), str(e))

    try:
      self._read_xparallel()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_xparallel(), str(e))

    try:
      self._read_spacegroup()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_spacegroup(), str(e))

    try:
      self._read_resolution()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_resolution(), str(e))

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
      self._read_freer_file()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_freer_file(), str(e))

    try:
      self._read_reference_reflection_file()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_reference_reflection_file(), str(e))

    try:
      self._read_rejection_threshold()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_rejection_threshold(), str(e))

    try:
      self._read_isigma()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_isigma(), str(e))

    try:
      self._read_misigma()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_misigma(), str(e))

    try:
      self._read_rmerge()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_rmerge(), str(e))

    try:
      self._read_cc_half()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_cc_half(), str(e))

    try:
      self._read_microcrystal()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_microcrystal(), str(e))

    try:
      self._read_failover()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_failover(), str(e))

    try:
      self._read_blend()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_blend(), str(e))

    try:
      self._read_completeness()
    except exceptions.Exception, e:
      raise RuntimeError, '%s (%s)' % \
            (self._help_completeness(), str(e))

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
        from Handlers.Environment import get_number_cpus
        mp_params.njob = get_number_cpus()
        if mp_params.nproc is Auto:
          mp_params.nproc = 1
      elif mp_params.nproc is Auto:
        from Handlers.Environment import get_number_cpus
        mp_params.nproc = get_number_cpus()
        Flags.set_parallel(mp_params.nproc)
      else:
        Flags.set_parallel(mp_params.nproc)
    elif mp_params.mode == 'serial':
      mp_params.njob = 1
      if mp_params.nproc is Auto:
        from Handlers.Environment import get_number_cpus
        mp_params.nproc = get_number_cpus()
      Flags.set_parallel(mp_params.nproc)

    PhilIndex.update("xia2.settings.multiprocessing.njob=%d" %mp_params.njob)
    PhilIndex.update("xia2.settings.multiprocessing.nproc=%d" %mp_params.nproc)
    params = PhilIndex.get_python_object()
    mp_params = params.xia2.settings.multiprocessing

    if params.xia2.settings.indexer is not None:
      add_preference("indexer", params.xia2.settings.indexer)
    if params.xia2.settings.refiner is not None:
      add_preference("refiner", params.xia2.settings.refiner)
    if params.xia2.settings.integrater is not None:
      add_preference("integrater", params.xia2.settings.integrater)
    if params.xia2.settings.scaler is not None:
      add_preference("scaler", params.xia2.settings.scaler)

    if params.xia2.settings.d_min is not None:
      Flags.set_resolution_high(params.xia2.settings.d_min)
    if params.xia2.settings.d_max is not None:
      Flags.set_resolution_low(params.xia2.settings.d_max)

    if params.xia2.settings.input.json is not None:
      assert os.path.isfile(params.xia2.settings.input.json)
      load_datablock(params.xia2.settings.input.json)

    if params.xia2.settings.input.reference_geometry is not None:
      PhilIndex.update(
        "xia2.settings.input.reference_geometry=%s" %os.path.abspath(
          params.xia2.settings.input.reference_geometry))
      Debug.write("xia2.settings.trust_beam_centre=true")
      PhilIndex.update("xia2.settings.trust_beam_centre=true")
      params = PhilIndex.get_python_object()

    try:
      self._read_xinfo()
    except exceptions.Exception, e:
      traceback.print_exc(file = open('xia2-xinfo.error', 'w'))
      raise RuntimeError, '%s (%s)' % \
            (self._help_xinfo(), str(e))

    params = PhilIndex.get_python_object()
    if params.xia2.settings.input.xinfo is not None:
      xinfo_file = os.path.abspath(params.xia2.settings.input.xinfo)
      PhilIndex.update("xia2.settings.input.xinfo=%s" %xinfo_file)
      params = PhilIndex.get_python_object()
      self._xinfo = XProject(xinfo_file)

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
    params = PhilIndex.get_python_object()

    images = PhilIndex.params.xia2.settings.input.image
    for image in images:
      template, directory = image2template_directory(os.path.abspath(image))
      self._default_template.append(template)
      self._default_directory.append(directory)

      Debug.write('Interpreted from image %s:' % image)
      Debug.write('Template %s' % template)
      Debug.write('Directory %s' % directory)

    # finally, check that all arguments were read and raise an exception
    # if any of them were nonsense.

    with open('xia2-working.phil', 'wb') as f:
      print >> f, PhilIndex.working_phil.as_str()
    with open('xia2-diff.phil', 'wb') as f:
      print >> f, PhilIndex.get_diff().as_str()

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

  def _read_beam(self):
    '''Read the beam centre from the command line.'''

    index = -1

    try:
      index = self._argv.index('-beam')
    except ValueError, e:
      self._beam = None
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    #try:
      #beam = self._argv[index + 1].split(',')
    #except IndexError, e:
      #raise RuntimeError, '-beam correct use "-beam x,y"'

    #if len(beam) != 2:
      #raise RuntimeError, '-beam correct use "-beam x,y"'

    #self._beam = (float(beam[0]), float(beam[1]))

    self._understood.append(index)
    self._understood.append(index + 1)

    # XXX Warning added 2014-11-10
    Chatter.write(
      "Warning: -beam option deprecated: please use beam_centre='%s' instead" %(
        self._argv[index + 1]))

    PhilIndex.update("xia2.settings.beam_centre=%s" %self._argv[index +1 ])
    PhilIndex.get_python_object()
    Debug.write('Beam read from command line as %f %f' % tuple(
      PhilIndex.params.xia2.settings.beam_centre))
    self._beam = tuple(PhilIndex.params.xia2.settings.beam_centre)

    return

  def _help_beam(self):
    '''Return a help string for the read beam method.'''
    return '-beam x,y'

  def get_beam(self):
    return self._beam

  def _help_image(self):
    '''Return a string for explaining the -image method.'''
    return '-image /path/to/an/image_001.img'

  def _read_image(self):
    '''Read image information from the command line.'''

    index = -1

    try:
      index = self._argv.index('-image')
    except ValueError, e:
      # the token is not on the command line
      self._default_template = []
      self._default_directory = []
      return

    image = self._argv[index + 1]

    # check if there is a space in the image name - this happens and it
    # looks like the python input parser will split it even if the
    # space is escaped or it is quoted

    if image[-1] == '\\':
      try:
        image = '%s %s' % (self._argv[index + 1][:-1],
                           self._argv[index + 2])
      except:
        raise RuntimeError, 'image name ends in \\'

    # XXX Warning added 2015-04-23
    Chatter.write(
      "Warning: -image option deprecated: please use image='%s' instead" %(
        image))

    PhilIndex.update("xia2.settings.input.image=%s" %image)
    PhilIndex.get_python_object()

    image = PhilIndex.params.xia2.settings.input.image[-1]

    self._understood.append(index)
    self._understood.append(index + 1)

    return

  def _read_atom_name(self):
    try:
      index = self._argv.index('-atom')

    except ValueError, e:
      self._default_atom_name = None
      return

    self._default_atom_name = self._argv[index + 1]

    self._understood.append(index)
    self._understood.append(index + 1)

    Debug.write('Heavy atom: %s' % \
                self._default_atom_name)

    return

  def _help_atom_name(self):
    return '-atom se'

  def get_atom_name(self):
    return self._default_atom_name

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

  def _read_project_name(self):
    try:
      index = self._argv.index('-project')

    except ValueError, e:
      self._default_project_name = None
      return

    self._default_project_name = self._argv[index + 1]

    self._understood.append(index)
    self._understood.append(index + 1)
    Debug.write('Project: %s' % self._default_project_name)

    return

  def _help_project_name(self):
    return '-project foo'

  def get_project_name(self):
    return self._default_project_name

  def _read_crystal_name(self):
    try:
      index = self._argv.index('-crystal')

    except ValueError, e:
      self._default_crystal_name = None
      return

    self._default_crystal_name = self._argv[index + 1]

    self._understood.append(index)
    self._understood.append(index + 1)
    Debug.write('Crystal: %s' % self._default_crystal_name)

    return

  def _help_crystal_name(self):
    return '-crystal foo'

  def get_crystal_name(self):
    return self._default_crystal_name

  def _read_xinfo(self):
    try:
      index = self._argv.index('-xinfo')
    except ValueError, e:
      self._xinfo = None
      return

    if index < 0:
      raise RuntimeError, 'negative index (no xinfo file name given)'

    self._understood.append(index)
    self._understood.append(index + 1)

    # XXX Warning added 2015-03-02
    Chatter.write(
      "Warning: -xinfo option deprecated: please use xinfo='%s' instead" %(
        self._argv[index + 1]))

    PhilIndex.update("xia2.settings.input.xinfo=%s" %self._argv[index + 1])
    PhilIndex.get_python_object()

    return

  def _help_xinfo(self):
    return '-xinfo example.xinfo'

  def set_xinfo(self, xinfo):
    self._xinfo = XProject(xinfo)

  def get_xinfo(self):
    '''Return the XProject.'''
    return self._xinfo

  def _read_xparm(self):
    try:
      index = self._argv.index('-xparm')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    Flags.set_xparm(self._argv[index + 1])

    self._understood.append(index)
    self._understood.append(index + 1)

    Debug.write('Rotation axis: %.6f %.6f %.6f' % \
        Flags.get_xparm_rotation_axis())
    Debug.write('Beam vector: %.6f %.6f %.6f' % \
        Flags.get_xparm_beam_vector())
    Debug.write('Origin: %.2f %.2f' % \
        Flags.get_xparm_origin())

    return

  def _help_xparm(self):
    return '-xparm GXPARM.XDS'

  def _read_xparm_ub(self):
    try:
      index = self._argv.index('-xparm_ub')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    Flags.set_xparm_ub(self._argv[index + 1])

    self._understood.append(index)
    self._understood.append(index + 1)

    Debug.write('Real Space A: %.2f %.2f %.2f' % \
                tuple(Flags.get_xparm_a()))
    Debug.write('Real Space B: %.2f %.2f %.2f' % \
                tuple(Flags.get_xparm_b()))
    Debug.write('Real Space C: %.2f %.2f %.2f' % \
                tuple(Flags.get_xparm_c()))

    return

  def _help_xparm_ub(self):
    return '-xparm_ub GXPARM.XDS'

  def _read_parallel(self):
    try:
      index = self._argv.index('-parallel')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    if int(self._argv[index + 1]) < 0:
      raise RuntimeError, 'negative number of processors: %s' % \
            self._argv[index + 1]

    self._understood.append(index)
    self._understood.append(index + 1)

    # XXX Warning added 2014-11-10
    Chatter.write(
      "Warning: -parallel option deprecated: please use nproc=%s instead" %(
        self._argv[index + 1]))

    PhilIndex.update("xia2.settings.multiprocessing.nproc=%s" %(
      self._argv[index + 1]))
    PhilIndex.get_python_object()
    return

  def _help_parallel(self):
    return '-parallel N'

  def _read_serial(self):
    try:
      index = self._argv.index('-serial')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)

    Flags.set_parallel(1)
    PhilIndex.update("xia2.settings.multiprocessing.nproc=1")
    PhilIndex.get_python_object()
    Debug.write('Serial set (i.e. 1 CPU)')

    return

  def _help_serial(self):
    return '-serial'

  def _read_min_images(self):
    try:
      index = self._argv.index('-min_images')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    # XXX Warning added 2015-05-01
    Chatter.write(
      "Warning: -min_images option deprecated: please use min_images=%s instead" %(
        self._argv[index + 1]))

    PhilIndex.update("xia2.settings.input.min_images=%i" %(
      int(self._argv[index + 1])))
    PhilIndex.get_python_object()

    return

  def _help_min_images(self):
    return '-min_images N'

  def _read_start_end(self):
    try:
      index = self._argv.index('-start_end')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    if not '-image' in self._argv:
      raise RuntimeError, 'do not use start_end without -image'

    self._understood.append(index)
    self._understood.append(index + 1)

    start, end = tuple(map(int, self._argv[index + 1].split(',')))

    Flags.set_start_end(start, end)
    Debug.write('Start, end set to %d %d' % Flags.get_start_end())

    return

  def _help_start_end(self):
    return '-start_end start,end'

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

  def _read_spacegroup(self):
    try:
      index = self._argv.index('-spacegroup')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    # XXX Warning added 2014-11-10
    Chatter.write(
      "Warning: -spacegroup option deprecated: please use space_group='%s' instead" %(
        self._argv[index + 1]))

    Flags.set_spacegroup(self._argv[index + 1]) # XXX this line should go
    PhilIndex.update("xia2.settings.space_group=%s" %self._argv[index + 1])
    PhilIndex.get_python_object()
    Debug.write('Spacegroup set to %s' % self._argv[index + 1])

    return

  def _help_spacegroup(self):
    return '-spacegroup P43212'

  def _read_resolution(self):
    try:
      index = self._argv.index('-resolution')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    resolution = self._argv[index + 1]
    if ',' in resolution:
      a, b = map(float, resolution.split(','))
      dmin = min(a, b)
      dmax = max(a, b)
    else:
      dmin = float(resolution)
      dmax = None

    self._understood.append(index)
    self._understood.append(index + 1)

    PhilIndex.update("xia2.settings.d_min=%s" %dmin)
    if dmax is not None:
      PhilIndex.update("xia2.settings.d_max=%s" %dmax)
      # XXX Warning added 2014-11-10
      Chatter.write(
        "Warning: -resolution option deprecated: please use d_min=%s and d_max=%s instead" %(
          dmin, dmax))
    else:
      # XXX Warning added 2014-11-10
      Chatter.write(
        "Warning: -resolution option deprecated: please use d_min=%s instead" %(
          dmin))
    PhilIndex.get_python_object()

    if dmax:
      Debug.write('Resolution set to %.3f %.3f' % (dmin, dmax))
    else:
      Debug.write('Resolution set to %.3f' % dmin)

    return

  def _help_resolution(self):
    return '-resolution high[,low]'

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

  def _read_freer_file(self):
    try:
      index = self._argv.index('-freer_file')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    Flags.set_freer_file(self._argv[index + 1])

    self._understood.append(index)
    self._understood.append(index + 1)

    Debug.write('FreeR_flag column taken from %s' %
                Flags.get_freer_file())

    # this should also be used as an indexing reference to make
    # sense...

    Flags.set_reference_reflection_file(self._argv[index + 1])
    Debug.write('Reference reflection file: %s' %
                Flags.get_reference_reflection_file())

    # and also the spacegroup copied out?! ok - this is done
    # "by magic" in the scaler.

    return

  def _help_freer_file(self):
    return '-freer_file my_freer_file.mtz'

  def _read_reference_reflection_file(self):
    try:
      index = self._argv.index('-reference_reflection_file')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    Flags.set_reference_reflection_file(self._argv[index + 1])

    self._understood.append(index)
    self._understood.append(index + 1)

    Debug.write('Reference reflection file: %s' %
                Flags.get_reference_reflection_file())

    return

  def _help_reference_reflection_file(self):
    return '-reference_reflection_file my_reference_reflection_file.mtz'

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

  def _read_isigma(self):
    try:
      index = self._argv.index('-isigma')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_isigma(float(self._argv[index + 1]))
    Debug.write('I/sigma limit set to %f' % \
                Flags.get_isigma())

    return

  def _help_isigma(self):
    return '-isigma N'

  def _read_misigma(self):
    try:
      index = self._argv.index('-misigma')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_misigma(float(self._argv[index + 1]))
    Debug.write('Merged I/sigma limit set to %f' % \
                Flags.get_misigma())

    return

  def _help_misigma(self):
    return '-misigma N'

  def _read_completeness(self):
    try:
      index = self._argv.index('-completeness')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_completeness(float(self._argv[index + 1]))
    Debug.write('Completeness limit set to %f' % \
                Flags.get_completeness())

    return

  def _help_completeness(self):
    return '-completeness N'

  def _read_rmerge(self):
    try:
      index = self._argv.index('-rmerge')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_rmerge(float(self._argv[index + 1]))
    Debug.write('Rmerge limit set to %f' % \
                Flags.get_rmerge())

    return

  def _help_rmerge(self):
    return '-rmerge N'

  def _read_cc_half(self):
    try:
      index = self._argv.index('-cc_half')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_cc_half(float(self._argv[index + 1]))
    Debug.write('CC half limit set to %f' % \
                Flags.get_cc_half())

    return

  def _help_cc_half(self):
    return '-cc_half N'

  def _read_microcrystal(self):

    if '-microcrystal' in self._argv:
      Flags.set_microcrystal()
      Debug.write('Microcrystal mode on')
      self._understood.append(self._argv.index('-microcrystal'))

    return

  def _read_failover(self):

    if '-failover' in self._argv:
      Flags.set_failover()
      Debug.write('Failover mode on')
      self._understood.append(self._argv.index('-failover'))

    return

  def _read_blend(self):

    if '-blend' in self._argv:
      Flags.set_blend()
      Debug.write('Blend mode on')
      self._understood.append(self._argv.index('-blend'))

    return

  def _read_ispyb_xml_out(self):
    try:
      index = self._argv.index('-ispyb_xml_out')
    except ValueError, e:
      self._ispyb_xml_out = None
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)
    Flags.set_ispyb_xml_out(self._argv[index + 1])
    Debug.write('ISPyB XML output set to %s' % self._argv[index + 1])

    return

  def _help_ispyb_xml_out(self):
    return '-ispyb_xml_out project.xml'

  def _read_hdr_in(self):
    try:
      index = self._argv.index('-hdr_in')
    except ValueError, e:
      self._hdr_in = None
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)
    Flags.set_hdr_in(self._argv[index + 1])

    return

  def _help_hdr_in(self):
    return '-hdr_in project.hdr'

  def _read_hdr_out(self):
    try:
      index = self._argv.index('-hdr_out')
    except ValueError, e:
      self._hdr_out = None
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)
    Flags.set_hdr_out(self._argv[index + 1])
    Debug.write('Output header file set to %s' % self._argv[index + 1])

    return

  def _help_hdr_out(self):
    return '-hdr_out project.hdr'

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

    return

  def _help_pickle(self):
    return '-pickle name.pkl'

  def get_template(self):
    return self._default_template

  def get_directory(self):
    return self._default_directory

  def _read_trust_timestamps(self):

    if '-trust_timestamps' in self._argv:
      Flags.set_trust_timestamps(True)
      Debug.write('Trust timestamps on')
      self._understood.append(self._argv.index('-trust_timestamps'))

    return

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

    return

  def _read_quick(self):

    if '-quick' in self._argv:
      Flags.set_quick(True)
      Debug.write('Quick mode selected')
      self._understood.append(self._argv.index('-quick'))
    return

  def _read_chef(self):

    if '-chef' in self._argv:
      Flags.set_chef(True)
      self._understood.append(self._argv.index('-chef'))
      Debug.write('Chef mode selected')

    if '-nochef' in self._argv:
      Flags.set_chef(False)
      self._understood.append(self._argv.index('-nochef'))
      Debug.write('Chef mode deselected')

    return

  def _read_reversephi(self):

    if '-reversephi' in self._argv:
      Flags.set_reversephi(True)
      self._understood.append(self._argv.index('-reversephi'))
      Debug.write('Reversephi mode selected')
    return

  def _read_no_lattice_test(self):

    if '-no_lattice_test' in self._argv:
      Flags.set_no_lattice_test(True)
      self._understood.append(self._argv.index('-no_lattice_test'))
      Debug.write('No lattice test mode selected')
    return

  def _read_no_relax(self):

    if '-no_relax' in self._argv:
      Flags.set_relax(False)
      self._understood.append(self._argv.index('-no_relax'))
      Debug.write('XDS relax about indexing selected')
    return

  def _read_no_profile(self):

    if '-no_profile' in self._argv:
      Flags.set_profile(False)
      self._understood.append(self._argv.index('-no_profile'))
      Debug.write('XDS profile fitting OFF')
    return

  def _read_zero_dose(self):

    if '-zero_dose' in self._argv:
      Flags.set_zero_dose(True)
      self._understood.append(self._argv.index('-zero_dose'))
      Debug.write('Zero-dose mode (XDS/XSCALE) selected')
    return

  def _read_norefine(self):

    if '-norefine' in self._argv:
      Flags.set_refine(False)
      self._understood.append(self._argv.index('-norefine'))
      # FIXME what does this do??? - switch off orientation refinement
      # in integration
    return

  def _read_noremove(self):

    if '-noremove' in self._argv:
      self._understood.append(self._argv.index('-noremove'))
      Flags.set_remove(False)
    return

  def _read_2d(self):

    if '-2d' in self._argv:
      settings = PhilIndex.get_python_object().xia2.settings
      if settings.refiner is None:
        PhilIndex.update("xia2.settings.refiner=mosflm")
      if settings.integrater is None:
        PhilIndex.update("xia2.settings.integrater=mosflmr")
      if settings.scaler is None:
        PhilIndex.update("xia2.settings.scaler=ccp4a")
      PhilIndex.get_python_object()
      self._understood.append(self._argv.index('-2d'))
      Debug.write('2DA pipeline selected')
    return

  def _read_2di(self):

    if '-2di' in self._argv:
      settings = PhilIndex.get_python_object().xia2.settings
      if settings.indexer is None:
        PhilIndex.update("xia2.settings.indexer=mosflm")
      if settings.refiner is None:
        PhilIndex.update("xia2.settings.refiner=mosflm")
      if settings.integrater is None:
        PhilIndex.update("xia2.settings.integrater=mosflmr")
      if settings.scaler is None:
        PhilIndex.update("xia2.settings.scaler=ccp4a")
      PhilIndex.get_python_object()
      self._understood.append(self._argv.index('-2di'))
      Debug.write('2DA pipeline; mosflm indexing selected')
    return

  def _read_dials(self):
    if '-dials' in self._argv:
      settings = PhilIndex.get_python_object().xia2.settings
      if settings.indexer is None:
        PhilIndex.update("xia2.settings.indexer=dials")
      if settings.refiner is None:
        PhilIndex.update("xia2.settings.refiner=dials")
      if settings.integrater is None:
        PhilIndex.update("xia2.settings.integrater=dials")
      if settings.scaler is None:
        PhilIndex.update("xia2.settings.scaler=ccp4a")
      PhilIndex.get_python_object()
      self._understood.append(self._argv.index('-dials'))
      Debug.write('DIALS pipeline selected')
    return

  def _read_3d(self):

    if '-3d' in self._argv:
      settings = PhilIndex.get_python_object().xia2.settings
      if settings.refiner is None:
        PhilIndex.update("xia2.settings.refiner=xds")
      if settings.integrater is None:
        PhilIndex.update("xia2.settings.integrater=xdsr")
      if settings.scaler is None:
        PhilIndex.update("xia2.settings.scaler=xdsa")
      PhilIndex.get_python_object()
      self._understood.append(self._argv.index('-3d'))
      Debug.write('3DR pipeline selected')
    return

  def _read_3di(self):

    if '-3di' in self._argv:
      settings = PhilIndex.get_python_object().xia2.settings
      if settings.indexer is None:
        PhilIndex.update("xia2.settings.indexer=xds")
      if settings.refiner is None:
        PhilIndex.update("xia2.settings.refiner=xds")
      if settings.integrater is None:
        PhilIndex.update("xia2.settings.integrater=xdsr")
      if settings.scaler is None:
        PhilIndex.update("xia2.settings.scaler=xdsa")
      PhilIndex.get_python_object()
      self._understood.append(self._argv.index('-3di'))
      Debug.write('3DR pipeline; XDS indexing selected')
    return

  def _read_3dii(self):

    if '-3dii' in self._argv:
      settings = PhilIndex.get_python_object().xia2.settings
      if settings.indexer is None:
        PhilIndex.update("xia2.settings.indexer=xdsii")
      if settings.refiner is None:
        PhilIndex.update("xia2.settings.refiner=xds")
      if settings.integrater is None:
        PhilIndex.update("xia2.settings.integrater=xdsr")
      if settings.scaler is None:
        PhilIndex.update("xia2.settings.scaler=xdsa")
      PhilIndex.get_python_object()
      self._understood.append(self._argv.index('-3dii'))
      Debug.write('3D II R pipeline (XDS IDXREF all images) selected')
    return

  def _read_3dd(self):

    if '-3dd' in self._argv:
      settings = PhilIndex.get_python_object().xia2.settings
      if settings.indexer is None:
        PhilIndex.update("xia2.settings.indexer=dials")
      if settings.refiner is None:
        PhilIndex.update("xia2.settings.refiner=xds")
      if settings.integrater is None:
        PhilIndex.update("xia2.settings.integrater=xdsr")
      if settings.scaler is None:
        PhilIndex.update("xia2.settings.scaler=xdsa")
      PhilIndex.get_python_object()
      self._understood.append(self._argv.index('-3dd'))
      Debug.write('3DD pipeline (DIALS indexing) selected')
    return

  def _read_debug(self):

    if '-debug' in self._argv:
      # join the debug stream to the main output
      Debug.join(Chatter)
      self._understood.append(self._argv.index('-debug'))
      Debug.write('Debugging output switched on')
    return

  def _read_interactive(self):

    if '-interactive' in self._argv:
      Flags.set_interactive(True)
      self._understood.append(self._argv.index('-interactive'))
      Debug.write('Interactive indexing ON')

    return

  def _read_ice(self):

    if '-ice' in self._argv:
      Flags.set_ice(True)
      self._understood.append(self._argv.index('-ice'))
      Debug.write('Ice ring exclusion ON')

    return

  def _read_egg(self):

    if '-egg' in self._argv:
      self._understood.append(self._argv.index('-egg'))
      Flags.set_egg(True)

    return

  def _read_uniform_sd(self):

    if '-no_uniform_sd' in self._argv:
      Flags.set_uniform_sd(False)
      self._understood.append(self._argv.index('-no_uniform_sd'))
      Debug.write('Uniform SD OFF')

    return

  def _read_migrate_data(self):

    if '-migrate_data' in self._argv:
      Flags.set_migrate_data(True)
      self._understood.append(self._argv.index('-migrate_data'))
      Debug.write('Data migration switched on')
    return

  def _read_cell(self):
    '''Read the cell constants from the command line.'''

    index = -1

    try:
      index = self._argv.index('-cell')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    try:
      cell = self._argv[index + 1].split(',')
    except IndexError, e:
      raise RuntimeError, \
            '-cell correct use "-cell a,b,c,alpha,beta,gamma"'

    if len(cell) != 6:
      raise RuntimeError, \
            '-cell correct use "-cell a,b,c,alpha,beta,gamma"'

    _cell = tuple(map(float, cell))

    # XXX Warning added 2014-11-10
    Chatter.write(
      "Warning: -cell option deprecated: please use unit_cell='%s' instead" %(
        self._argv[index + 1]))

    PhilIndex.update("xia2.settings.unit_cell=%s,%s,%s,%s,%s,%s" %_cell)
    PhilIndex.get_python_object()

    format = 6 * ' %7.2f'

    self._understood.append(index)
    self._understood.append(index + 1)

    Debug.write('Cell read from command line:' + \
                format % _cell)

    return

  def _help_cell(self):
    '''Return a help string for the read cell method.'''
    return '-cell a,b,c,alpha,beta,gamma'

  def _read_free_fraction(self):
    try:
      index = self._argv.index('-free_fraction')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_free_fraction(float(self._argv[index + 1]))
    Debug.write('Free fraction set to %f' % Flags.get_free_fraction())

    return

  def _help_free_fraction(self):
    return '-free_fraction N'

  def _read_free_total(self):
    try:
      index = self._argv.index('-free_total')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    self._understood.append(index + 1)

    Flags.set_free_total(int(self._argv[index + 1]))
    Debug.write('Free total set to %f' % Flags.get_free_total())

    return

  def _help_free_total(self):
    return '-free_total N'

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

    return

  def get_mask(self):
    return self._mask

  def _help_mask(self):
    return '-mask mask.dat'

  def get_mask(self):
    return self._mask

  def _read_fixed_628(self):
    try:
      index = self._argv.index('-fixed_628')
    except ValueError, e:
      return

    if index < 0:
      raise RuntimeError, 'negative index'

    self._understood.append(index)
    Flags.set_fixed_628()

    return

  def _help_fixed_628(self):
    return '-fixed_628'

  def _read_indexer(self):

    try:
      index = self._argv.index('-indexer')
    except ValueError, e:
      return

    indexer = self._argv[index + 1]

    # XXX Warning added 2014-11-10
    Chatter.write(
      "Warning: -indexer option deprecated: please use indexer='%s' instead" %(
        indexer))

    PhilIndex.update("xia2.settings.indexer=%s" %indexer)
    PhilIndex.get_python_object()

    self._understood.append(index)
    self._understood.append(index + 1)
    return

  def _read_integrater(self):

    try:
      index = self._argv.index('-integrater')
    except ValueError, e:
      return

    integrater = self._argv[index + 1]

    # XXX Warning added 2014-11-10
    Chatter.write(
      "Warning: -integrater option deprecated: please use integrater='%s' instead" %(
        integrater))

    PhilIndex.update("xia2.settings.integrater=%s" %integrater)
    PhilIndex.get_python_object()

    self._understood.append(index)
    self._understood.append(index + 1)
    return

  def _read_scaler(self):

    try:
      index = self._argv.index('-scaler')
    except ValueError, e:
      return

    scaler = self._argv[index + 1]

    # XXX Warning added 2014-11-10
    Chatter.write(
      "Warning: -scaler option deprecated: please use scaler='%s' instead" %(
        scaler))

    PhilIndex.update("xia2.settings.scaler=%s" %scaler)
    PhilIndex.get_python_object()

    self._understood.append(index)
    self._understood.append(index + 1)
    return

  def _read_executables(self):
    try:
      index = self._argv.index('-executable')
    except ValueError, e:
      return
    executable_string = self._argv[index + 1]
    assert('=' in executable_string)
    executable, path = executable_string.split('=')
    Executables.add(executable, path)
    self._understood.append(index)
    self._understood.append(index + 1)
    return

CommandLine = _CommandLine()
CommandLine.setup()

if __name__ == '__main__':
  print CommandLine.get_beam()
  print CommandLine.get_xinfo()
