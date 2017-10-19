from __future__ import absolute_import, division

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
      from xia2.Wrappers.Mosflm.Exceptions import AutoindexError
      raise AutoindexError('indexing failed')

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
        except (ValueError, IndexError):
          k += 1
          continue

  return solutions

def set_distance(detector, distance):
  from scitbx import matrix
  import math
  #assert len(detector) == 1, len(detector)
  panel = detector[0]
  d_normal = matrix.col(panel.get_normal())
  d_origin = matrix.col(panel.get_origin())
  d_distance = math.fabs(d_origin.dot(d_normal) - panel.get_directed_distance())
  assert d_distance < 0.001, d_distance
  translation = d_normal * (distance - panel.get_directed_distance())
  new_origin = d_origin + translation
  d_distance = math.fabs(new_origin.dot(d_normal) - distance)
  assert d_distance < 0.001, d_distance
  fast = panel.get_fast_axis()
  slow = panel.get_slow_axis()
  panel.set_frame(panel.get_fast_axis(), panel.get_slow_axis(), new_origin.elems)
  d_fast = matrix.col(panel.get_fast_axis()).angle(matrix.col(fast), deg=True)
  assert d_fast < 1e-6, d_fast
  d_slow = matrix.col(panel.get_slow_axis()).angle(matrix.col(slow), deg=True)
  assert d_slow < 1e-6, d_slow
  d_distance = math.fabs(panel.get_directed_distance() - distance)
  assert d_distance < 0.001, d_distance

def crystal_model_from_mosflm_mat(mosflm_mat_lines, unit_cell, space_group):
  from scitbx import matrix
  from cctbx import uctbx
  if not isinstance(unit_cell, uctbx.unit_cell):
    unit_cell = uctbx.unit_cell(unit_cell)
  from dxtbx.model import CrystalFactory
  mosflm_matrix = matrix.sqr([float(i) for line in mosflm_mat_lines[:3]
                              for i in line.split()][:9])
  crystal_model = CrystalFactory.from_mosflm_matrix(
    mosflm_matrix,
    unit_cell=unit_cell,
    space_group=space_group)
  return crystal_model
