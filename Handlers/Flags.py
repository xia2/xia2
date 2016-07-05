#/usr/bin/env python
# Flags.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 4th May 2007
#
# A singleton to handle flags, which can be imported more easily
# as it will not suffer the problems with circular references that
# the CommandLine singleton suffers from. FIXME xia2-42 this is due
# for retirement & working into the Phil structure

import os
import sys

from xia2.Handlers.Environment import get_number_cpus
from xia2.Toolkit.BackstopMask import BackstopMask

class _Flags(object):
  '''A singleton to manage boolean flags.'''

  def __init__(self):
    self._quick = False
    self._interactive = False
    self._ice = False
    self._mask = None
    self._reversephi = False
    self._no_lattice_test = False

    # XDS specific things - to help with handling tricky data sets

    self._xparm = None
    self._xparm_beam_vector = None
    self._xparm_rotation_axis = None
    self._xparm_origin = None

    self._xparm_a = None
    self._xparm_b = None
    self._xparm_c = None

    try:
      self._parallel = get_number_cpus()
    except:
      self._parallel = 0

    self._xparallel = 0

    # File from which to copy the FreeR_flag column
    self._freer_file = None

    # or alternatively the fraction, or total number of free
    # reflections
    self._free_fraction = None
    self._free_total = None

    # reference reflection file
    self._reference_reflection_file = None

    # these are development parameters for the XDS implementation
    self._z_min = 0.0
    self._relax = True

    # options to support the -spacegroup flag - the spacegroup is
    # set from this, the lattice and pointgroup derived from such
    self._spacegroup = None
    self._pointgroup = None
    self._lattice = None

    # resolution limit flags
    self._resolution_low = None
    self._resolution_high = None

    # and these are general rejection criteria
    self._rejection_threshold = 1.5
    self._isigma = 1.0
    self._misigma = 2.0
    self._completeness = 0.0
    self._rmerge = 0.0
    self._cc_half = 0.0

    # are we working with small molecule data?
    self._small_molecule = False

    # pickle output
    self._pickle = None

    # serialization of indexer/integrater state to/from json
    self._serialize_state = False

    # starting directory (to allow setting working directory && relative
    # paths on input)
    self._starting_directory = os.getcwd()

    return

  def get_starting_directory(self):
    return self._starting_directory

  def set_serialize_state(self, serialize_state):
    self._serialize_state = serialize_state
    return

  def get_serialize_state(self):
    return self._serialize_state

  ### SETTING OF RESOLUTION LIMITS #### bug # 3183

  def set_resolution_high(self, resolution):
    self._resolution_high = resolution
    return

  def set_resolution_low(self, resolution):
    self._resolution_low = resolution
    return

  def get_resolution_high(self):
    return self._resolution_high

  def get_resolution_low(self):
    return self._resolution_low

  def set_spacegroup(self, spacegroup):
    '''A handler for the command-line option -spacegroup - this will
    set the spacegroup and derive from this the pointgroup and lattice
    appropriate for such...'''

    from xia2.Handlers.Syminfo import Syminfo

    spacegroup = spacegroup.upper()

    # validate by deriving the pointgroup and lattice...

    pointgroup = Syminfo.get_pointgroup(spacegroup)
    lattice = Syminfo.get_lattice(spacegroup)

    # assign

    self._spacegroup = spacegroup
    self._pointgroup = pointgroup
    self._lattice = lattice

    # debug print

    from xia2.Handlers.Streams import Debug

    Debug.write('Derived information from spacegroup flag: %s' % \
                spacegroup)
    Debug.write('Pointgroup: %s  Lattice: %s' % (pointgroup, lattice))

    # indicate that since this has been assigned, we do not wish to
    # test it!

    self.set_no_lattice_test(True)

    return

  def get_spacegroup(self):
    return self._spacegroup

  def get_pointgroup(self):
    return self._pointgroup

  def get_lattice(self):
    return self._lattice

  def set_quick(self, quick):
    self._quick = quick
    return

  def get_quick(self):
    return self._quick

  def set_interactive(self, interactive):
    self._interactive = interactive
    return

  def get_interactive(self):
    return self._interactive

  def set_reversephi(self, reversephi):
    self._reversephi = reversephi
    return

  def get_reversephi(self):
    return self._reversephi

  def set_no_lattice_test(self, no_lattice_test):
    self._no_lattice_test = no_lattice_test
    return

  def get_no_lattice_test(self):
    return self._no_lattice_test

  def set_relax(self, relax):
    self._relax = relax
    return

  def get_relax(self):
    return self._relax

  def set_small_molecule(self, small_molecule):
    self._small_molecule = small_molecule
    return

  def get_small_molecule(self):
    return self._small_molecule

  def set_parallel(self, parallel):
    self._parallel = parallel
    return

  def get_parallel(self):
    return self._parallel

  def set_xparm(self, xparm):

    self._xparm = xparm

    from xia2.Wrappers.XDS.XDS import xds_read_xparm

    xparm_info = xds_read_xparm(xparm)

    self._xparm_origin = xparm_info['ox'], xparm_info['oy']
    self._xparm_beam_vector = tuple(xparm_info['beam'])
    self._xparm_rotation_axis = tuple(xparm_info['axis'])
    self._xparm_distance = xparm_info['distance']

    return

  def get_xparm(self):
    return self._xparm

  def get_xparm_origin(self):
    return self._xparm_origin

  def get_xparm_rotation_axis(self):
    return self._xparm_rotation_axis

  def get_xparm_beam_vector(self):
    return self._xparm_beam_vector

  def get_xparm_distance(self):
    return self._xparm_distance

  def set_xparm_ub(self, xparm):

    self._xparm_ub = xparm

    tokens = map(float, open(xparm, 'r').read().split())

    self._xparm_a = tokens[-9:-6]
    self._xparm_b = tokens[-6:-3]
    self._xparm_c = tokens[-3:]

    return

  def get_xparm_a(self):
    return self._xparm_a

  def get_xparm_b(self):
    return self._xparm_b

  def get_xparm_c(self):
    return self._xparm_c

  def set_xparallel(self, xparallel):
    self._xparallel = xparallel
    return

  def get_xparallel(self):
    return self._xparallel

  def set_z_min(self, z_min):
    self._z_min = z_min
    return

  def get_z_min(self):
    return self._z_min

  def set_freer_file(self, freer_file):

    # mtzdump this file to make sure that there is a FreeR_flag
    # column therein...

    freer_file = os.path.abspath(freer_file)

    if not os.path.exists(freer_file):
      raise RuntimeError, '%s does not exist' % freer_file

    from xia2.Modules.FindFreeFlag import FindFreeFlag
    from xia2.Handlers.Streams import Debug

    column = FindFreeFlag(freer_file)

    Debug.write('FreeR_flag column in %s found: %s' % \
                (freer_file, column))

    self._freer_file = freer_file
    return

  def get_freer_file(self):
    return self._freer_file

  def set_free_fraction(self, free_fraction):
    self._free_fraction = free_fraction
    return

  def get_free_fraction(self):
    return self._free_fraction

  def set_free_total(self, free_total):
    self._free_total = free_total
    return

  def get_free_total(self):
    return self._free_total

  def set_mask(self, mask):
    self._mask = BackstopMask(mask)
    return

  def get_mask(self):
    return self._mask

  def set_pickle(self, pickle):
    self._pickle = pickle
    return

  def get_pickle(self):
    return self._pickle

  def set_reference_reflection_file(self, reference_reflection_file):
    '''Set a new reference reflection file.'''

    reference_reflection_file = os.path.abspath(reference_reflection_file)

    if not os.path.exists(reference_reflection_file):
      raise RuntimeError, '%s does not exist' % reference_reflection_file

    self._reference_reflection_file = reference_reflection_file

    return

  def get_reference_reflection_file(self):
    return self._reference_reflection_file

  def set_rejection_threshold(self, rejection_threshold):
    self._rejection_threshold = rejection_threshold
    return

  def get_rejection_threshold(self):
    return self._rejection_threshold

Flags = _Flags()
