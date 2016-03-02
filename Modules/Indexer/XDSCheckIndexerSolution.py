#!/usr/bin/env cctbx.python
# XDSCheckIndexerSolution.py
#
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 11th May 2009
#
# Code to check the XDS solution from IDXREF for being pseudo-centred (i.e.
# comes out as centered when it should not be)
#

import os
import math
import sys

# xia2 stuff...

from xia2.Handlers.Streams import Debug
from xia2.Handlers.Flags import Flags
from xia2.lib.bits import nint

# cctbx stuff

from cctbx import sgtbx
from cctbx import crystal
from scitbx import matrix


def s2l(spacegroup):
  lattice_to_spacegroup = {'aP':1, 'mP':3, 'mC':5,
                           'oP':16, 'oC':20, 'oF':22,
                           'oI':23, 'tP':75, 'tI':79,
                           'hP':143, 'hR':146, 'cP':195,
                           'cF':196, 'cI':197}

  spacegroup_to_lattice = { }
  for k in lattice_to_spacegroup.keys():
    spacegroup_to_lattice[lattice_to_spacegroup[k]] = k
  return spacegroup_to_lattice[spacegroup]

def xds_check_indexer_solution(xparm_file,
                               spot_file):
  '''Read XPARM file from XDS IDXREF (assumes that this is in the putative
  correct symmetry, not P1! and test centring operations if present. Note
  that a future version will boost to the putative correct symmetry (or
  an estimate of it) and try this if it is centred. Returns tuple
  (space_group_number, cell).'''

  from dxtbx.serialize.xds import to_crystal as xparm_to_crystal
  cm = xparm_to_crystal(xparm_file)
  sg = cm.get_space_group()
  spacegroup = sg.type().hall_symbol()
  space_group_number = sg.type().number()
  A_inv = cm.get_A().inverse()
  cell = cm.get_unit_cell().parameters()

  import dxtbx
  models = dxtbx.load(xparm_file)
  detector = models.get_detector()
  beam = models.get_beam()
  goniometer = models.get_goniometer()
  scan = models.get_scan()

  from iotbx.xds import spot_xds
  spot_xds_handle = spot_xds.reader()
  spot_xds_handle.read_file(spot_file)

  from cctbx.array_family import flex
  centroids_px = flex.vec3_double(spot_xds_handle.centroid)
  miller_indices = flex.miller_index(spot_xds_handle.miller_index)

  # Convert Pixel coordinate into mm/rad
  x, y, z = centroids_px.parts()
  x_mm, y_mm = detector[0].pixel_to_millimeter(flex.vec2_double(x, y)).parts()
  z_rad = scan.get_angle_from_array_index(z, deg=False)
  centroids_mm = flex.vec3_double(x_mm, y_mm, z_rad)

  # then convert detector position to reciprocal space position

  # based on code in dials/algorithms/indexing/indexer2.py
  s1 = detector[0].get_lab_coord(flex.vec2_double(x_mm, y_mm))
  s1 = s1/s1.norms() * (1/beam.get_wavelength())
  S = s1 - beam.get_s0()
  # XXX what about if goniometer fixed rotation is not identity?
  reciprocal_space_points = S.rotate_around_origin(
    goniometer.get_rotation_axis(),
    -z_rad)

  # now index the reflections
  hkl_float = tuple(A_inv) * reciprocal_space_points
  hkl_int = hkl_float.iround()

  # check if we are within 0.1 lattice spacings of the closest
  # lattice point - a for a random point this will be about 0.8% of
  # the time...
  differences = hkl_float - hkl_int.as_vec3_double()
  dh, dk, dl = [flex.abs(d) for d in differences.parts()]
  tolerance = 0.1
  sel = (dh < tolerance) and (dk < tolerance) and (dl < tolerance)

  is_sys_absent = sg.is_sys_absent(
    flex.miller_index(list(hkl_int.select(sel))))

  total = is_sys_absent.size()
  absent = is_sys_absent.count(True)
  present = total - absent

  # now, if the number of absences is substantial, need to consider
  # transforming this to a primitive basis

  Debug.write('Absent: %d  vs.  Present: %d Total: %d' % \
              (absent, present, total))

  # now see if this is compatible with a centred lattice or suggests
  # a primitive basis is correct

  sd = math.sqrt(absent)

  if (absent - 3 * sd) / total < 0.008:
    # everything is peachy

    return s2l(space_group_number), tuple(cell)

  # ok if we are here things are not peachy, so need to calculate the
  # spacegroup number without the translation operators

  sg_new = sg.build_derived_group(True, False)
  space_group_number_primitive = sg_new.type().number()

  # also determine the best setting for the new cell ...

  symm = crystal.symmetry(unit_cell = cell,
                          space_group = sg_new)

  rdx = symm.change_of_basis_op_to_best_cell()
  symm_new = symm.change_basis(rdx)
  cell_new = symm_new.unit_cell().parameters()

  return s2l(space_group_number_primitive), tuple(cell_new)

def is_centred(space_group_number):
  '''Test if space group # corresponds to a centred space group.'''

  sg_hall = sgtbx.space_group_symbols(space_group_number).hall()
  sg = sgtbx.space_group(sg_hall)

  if (sg.n_ltr() - 1):
    return True

  return False


if __name__ == '__main__':

  source = os.getcwd()

  if len(sys.argv) > 1:
    source = sys.argv[1]

  xparm = os.path.join(source, 'XPARM.XDS')
  spot = os.path.join(source, 'SPOT.XDS')

  xds_check_indexer_solution(xparm, spot)
