from __future__ import division

def index_solution(tokens):
  from collections import namedtuple
  IndexSolution = namedtuple('IndexSolution',
                             'penalty sdcell fracn latt cell')

  cell = tuple(map(float, tokens[5:11]))
  return IndexSolution(int(tokens[1]), float(tokens[2]), float(tokens[3]),
                       tokens[4], cell)

def parse_index_log(mosflm_output):
  n_solutions = 0
  solutions = [ ]

  for record in mosflm_output:
    if 'DIRECT SPACE VECTORS DID NOT RESULT INTO A ORIENTATION' in record:
      from Exceptions import AutoindexError
      raise AutoindexError, 'indexing failed'

  for j, record in enumerate(mosflm_output):
    if ' No PENALTY SDCELL FRACN LATT      a        b        c' in record:
      k = j
      while n_solutions < 44:
        try:
          lattice_character = int(mosflm_output[k].split()[0])
          if not 'unrefined' in mosflm_output[k]:
            solutions.append(index_solution(
                mosflm_output[k].split()))

          n_solutions += 1
          k += 1
        except ValueError, e:
          k += 1
          continue
        except IndexError, e:
          k += 1
          continue

  return solutions

def set_mosflm_beam_centre(detector, beam, mosflm_beam_centre):
  """ detector and beam are dxtbx objects,
      mosflm_beam_centre is a tuple of mm coordinates.
  """
  from scitbx import matrix
  panel_id, old_beam_centre = detector.get_ray_intersection(beam.get_s0())
  # XXX maybe not the safest way to do this?
  new_beam_centre = matrix.col(tuple(reversed(mosflm_beam_centre)))
  origin_shift = matrix.col(old_beam_centre) - new_beam_centre
  for panel in detector:
    old_origin = panel.get_origin()
    new_origin = (old_origin[0] + origin_shift[0],
                  old_origin[1] - origin_shift[1],
                  old_origin[2])
    panel.set_local_frame(fast_axis=panel.get_fast_axis(),
                          slow_axis=panel.get_slow_axis(),
                          origin=new_origin)
  # sanity check to make sure we have got the new beam centre correct
  panel_id, new_beam_centre = detector.get_ray_intersection(beam.get_s0())
  #assert (matrix.col(new_beam_centre) -
  #        matrix.col(tuple(reversed(mosflm_beam_centre)))).length() < 1e-4
  if (matrix.col(new_beam_centre) -
          matrix.col(tuple(reversed(mosflm_beam_centre)))).length() > 1e-4:
    print "Beam centre moved by %f" % (matrix.col(new_beam_centre) -
          matrix.col(tuple(reversed(mosflm_beam_centre)))).length()
  # FIXME this assertion breaks the beam_centre command line parameter

def set_distance(detector, distance):
  from scitbx import matrix
  import math
  assert len(detector) == 1
  panel = detector[0]
  d_normal = matrix.col(panel.get_normal())
  d_origin = matrix.col(panel.get_origin())
  assert d_origin.dot(d_normal) == panel.get_distance()
  translation = d_normal * (distance - panel.get_distance())
  new_origin = d_origin + translation
  assert math.fabs(new_origin.dot(d_normal) - distance) < 0.001
  fast = panel.get_fast_axis()
  slow = panel.get_slow_axis()
  panel.set_frame(panel.get_fast_axis(), panel.get_slow_axis(), new_origin.elems)
  assert matrix.col(panel.get_fast_axis()).angle(
    matrix.col(fast), deg=True) < 1e-6
  assert matrix.col(panel.get_slow_axis()).angle(
    matrix.col(slow), deg=True) < 1e-6
  assert math.fabs(panel.get_distance() - distance) < 0.001

def crystal_model_from_mosflm_mat(mosflm_mat_lines, unit_cell, space_group):
  from scitbx import matrix
  from cctbx import uctbx
  if not isinstance(unit_cell, uctbx.unit_cell):
    unit_cell = uctbx.unit_cell(unit_cell)
  from dxtbx.model.crystal import crystal_model_from_mosflm_matrix
  mosflm_matrix = matrix.sqr([float(i) for line in mosflm_mat_lines[:3]
                              for i in line.split()][:9])
  crystal_model = crystal_model_from_mosflm_matrix(
    mosflm_matrix,
    unit_cell=unit_cell,
    space_group=space_group)
  return crystal_model
