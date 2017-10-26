#!/usr/bin/env python
# MosflmCheckIndexerSolution.py
#   Copyright (C) 2009 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
# 12th May 2009
#
# Code to check the autoindex solution from mosflm for being
# pseudo-centred (i.e. comes out as centered when it should not be)
#

from __future__ import absolute_import, division

import math
import sys

from cctbx import crystal, sgtbx, uctbx
from scitbx import matrix
from xia2.Experts.LatticeExpert import l2s, s2l
from xia2.Experts.MatrixExpert import format_matrix
from xia2.Handlers.Streams import Debug
from xia2.lib.bits import nint
from xia2.Wrappers.Labelit.DistlSignalStrength import DistlSignalStrength
from xia2.Wrappers.XIA.Diffdump import Diffdump
from xia2.Wrappers.XIA.Printpeaks import Printpeaks

# xia2 stuff...


# optional labelit stuff


# things we can work on...

use_distl = False

# cctbx stuff


# check for deprecation, add workaround (thanks to RWGK 21/APR/10)

if (hasattr(matrix.rec, "rotate_around_origin")):
  matrix.rec.rotate = matrix.rec.rotate_around_origin

# end workaround

# failover on spot picking...

def locate_maxima(image):

  global use_distl

  if use_distl:
    try:
      dss = DistlSignalStrength()
      dss.set_image(image)
      peaks = dss.find_peaks()

      if not peaks:
        raise RuntimeError('no peaks found')

    except Exception:
      use_distl = False

  if not use_distl:

    pp = Printpeaks()
    pp.set_image(image)
    peaks = pp.get_maxima()

  return peaks

def mosflm_check_indexer_solution(indexer):

  distance = indexer.get_indexer_distance()
  axis = matrix.col([0, 0, 1])
  beam = indexer.get_indexer_beam_centre()
  cell = indexer.get_indexer_cell()
  wavelength = indexer.get_wavelength()

  space_group_number = l2s(indexer.get_indexer_lattice())
  spacegroup = sgtbx.space_group_symbols(space_group_number).hall()
  phi = indexer.get_header()['phi_width']

  sg = sgtbx.space_group(spacegroup)

  if not (sg.n_ltr() - 1):
    # primitive solution - just return ... something
    return None, None, None, None

  # FIXME need to raise an exception if this is not available!
  m_matrix = indexer.get_indexer_payload('mosflm_orientation_matrix')

  # N.B. in the calculation below I am using the Cambridge frame
  # and Mosflm definitions of X & Y...

  m_elems = []

  for record in m_matrix[:3]:
    record = record.replace('-', ' -')
    for e in map(float, record.split()):
      m_elems.append(e / wavelength)

  mi = matrix.sqr(m_elems)
  m = mi.inverse()

  A = matrix.col(m.elems[0:3])
  B = matrix.col(m.elems[3:6])
  C = matrix.col(m.elems[6:9])

  # now select the images - start with the images that the indexer
  # used for indexing, though can interrogate the FrameProcessor
  # interface of the indexer to put together a completely different
  # list if I like...

  images = []

  for i in indexer.get_indexer_images():
    for j in i:
      if not j in images:
        images.append(j)

  images.sort()

  # now construct the reciprocal-space peak list n.b. should
  # really run this in parallel...

  spots_r = []

  spots_r_j =  { }

  for i in images:
    image = indexer.get_image_name(i)
    dd = Diffdump()
    dd.set_image(image)
    header = dd.readheader()
    phi = header['phi_start'] + 0.5 * header['phi_width']
    pixel = header['pixel']
    wavelength = header['wavelength']
    peaks = locate_maxima(image)

    spots_r_j[i] = []

    for p in peaks:
      x, y, isigma = p

      if isigma < 5.0:
        continue

      xp = pixel[0] * y - beam[0]
      yp = pixel[1] * x - beam[1]

      scale = wavelength * math.sqrt(
          xp * xp + yp * yp + distance * distance)

      X = distance / scale
      X -= 1.0 / wavelength
      Y = - xp / scale
      Z = yp / scale

      S = matrix.col([X, Y, Z])

      rtod = 180.0 / math.pi

      spots_r.append(S.rotate(axis, - phi / rtod))
      spots_r_j[i].append(S.rotate(axis, - phi / rtod))

  # now reindex the reciprocal space spot list and count - n.b. need
  # to transform the Bravais lattice to an assumed spacegroup and hence
  # to a cctbx spacegroup!

  # lists = [spots_r_j[j] for j in spots_r_j]
  lists = []
  lists.append(spots_r)

  for l in lists:

    absent = 0
    present = 0
    total = 0

    for spot in l:
      hkl = (m * spot).elems

      total += 1

      ihkl = map(nint, hkl)

      if math.fabs(hkl[0] - ihkl[0]) > 0.1:
        continue

      if math.fabs(hkl[1] - ihkl[1]) > 0.1:
        continue

      if math.fabs(hkl[2] - ihkl[2]) > 0.1:
        continue

      # now determine if it is absent

      if sg.is_sys_absent(ihkl):
        absent += 1
      else:
        present += 1

    # now perform the analysis on these numbers...

    sd = math.sqrt(absent)

    if total:

      Debug.write('Counts: %d %d %d %.3f' % \
                  (total, present, absent, (absent - 3 * sd) / total))

    else:

      Debug.write('Not enough spots found for analysis')
      return False, None, None, None

    if (absent - 3 * sd) / total < 0.008:
      return False, None, None, None

  # in here need to calculate the new orientation matrix for the
  # primitive basis and reconfigure the indexer - somehow...

  # ok, so the bases are fine, but what I will want to do is reorder them
  # to give the best primitive choice of unit cell...

  sgp = sg.build_derived_group(True, False)
  lattice_p = s2l(sgp.type().number())
  symm = crystal.symmetry(unit_cell = cell,
                          space_group = sgp)

  rdx = symm.change_of_basis_op_to_best_cell()
  symm_new = symm.change_basis(rdx)

  # now apply this to the reciprocal-space orientation matrix mi

  # cb_op = sgtbx.change_of_basis_op(rdx)
  cb_op = rdx
  R = cb_op.c_inv().r().as_rational().as_float().transpose().inverse()
  mi_r = mi * R

  # now re-derive the cell constants, just to be sure

  m_r = mi_r.inverse()
  Ar = matrix.col(m_r.elems[0:3])
  Br = matrix.col(m_r.elems[3:6])
  Cr = matrix.col(m_r.elems[6:9])

  a = math.sqrt(Ar.dot())
  b = math.sqrt(Br.dot())
  c = math.sqrt(Cr.dot())

  rtod = 180.0 / math.pi

  alpha = rtod * Br.angle(Cr)
  beta = rtod * Cr.angle(Ar)
  gamma = rtod * Ar.angle(Br)

  # print '%6.3f %6.3f %6.3f %6.3f %6.3f %6.3f' % \
  # (a, b, c, alpha, beta, gamma)

  cell = uctbx.unit_cell((a, b, c, alpha, beta, gamma))

  amat = [wavelength * e for e in mi_r.elems]
  bmat = matrix.sqr(cell.fractionalization_matrix())
  umat = mi_r * bmat.inverse()

  # yuk! surely I don't need to do this...

  # I do need to do this, and don't call me shirley!

  new_matrix = ['%s\n' % r for r in \
                format_matrix((a, b, c, alpha, beta, gamma),
                              amat, umat.elems).split('\n')]

  # ok - this gives back the right matrix in the right setting - excellent!
  # now need to apply this back at base to the results of the indexer.

  # N.B. same should be applied to the same calculations for the XDS
  # version of this.

  return True, lattice_p, new_matrix, (a, b, c, alpha, beta, gamma)

if __name__ == '__main__':

  # run a test!

  from xia2.Modules.Indexer.IndexerFactory import Indexer

  i = Indexer()

  i.setup_from_image(sys.argv[1])

  print 'Refined beam is: %6.2f %6.2f' % i.get_indexer_beam_centre()
  print 'Distance:        %6.2f' % i.get_indexer_distance()
  print 'Cell: %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % i.get_indexer_cell()
  print 'Lattice: %s' % i.get_indexer_lattice()
  print 'Mosaic: %6.2f' % i.get_indexer_mosaic()

  status = mosflm_check_indexer_solution(i)

  if status is True:
    print 'putative centred solution came out as wrong'

  elif status is False:
    print 'putative centred solution came out as right'

  elif status is None:
    print 'putative solution not centred'
