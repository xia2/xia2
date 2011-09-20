import os
import sys
import math

from cctbx import sgtbx
from cctbx import crystal
from cctbx import uctbx
from scitbx import matrix
from cctbx.sgtbx.lattice_symmetry import metric_subgroups

def parse_matrix(matrix_text):

    tokens = map(float, matrix_text.replace('-', ' -').split())

    cell = tokens[21:27]
    a = tokens[0:9]
    u = tokens[12:21]

    return cell, a, u

def format_matrix(cell, a, u):

    matrix_format = ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n'
    
    cell_format = ' %11.4f %11.4f %11.4f %11.4f %11.4f %11.4f\n'
    
    misset = '       0.000       0.000       0.000\n'

    return matrix_format % tuple(a) + misset + matrix_format % tuple(u) + \
           cell_format % tuple(cell) + misset

def mosflm_a_to_cell(mosflm_a_matrix, wavelength):
    real_a = matrix.sqr(mosflm_a_matrix).inverse()

    a = wavelength * matrix.col(real_a.elems[0:3])
    b = wavelength * matrix.col(real_a.elems[3:6])
    c = wavelength * matrix.col(real_a.elems[6:9])

    r2d = 180.0 / math.pi

    return math.sqrt(a.dot()), math.sqrt(b.dot()), math.sqrt(c.dot()), \
           b.angle(c) * r2d, c.angle(a) * r2d, a.angle(b) * r2d

def calculate_wavelength(unit_cell, mosflm_a_matrix):
    real_a = matrix.sqr(mosflm_a_matrix).inverse()

    a = matrix.col(real_a.elems[0:3])
    b = matrix.col(real_a.elems[3:6])
    c = matrix.col(real_a.elems[6:9])

    r2d = 180.0 / math.pi

    assert(math.fabs(a.angle(b) * r2d - unit_cell[5]) < 0.1)
    assert(math.fabs(b.angle(c) * r2d - unit_cell[3]) < 0.1)
    assert(math.fabs(c.angle(a) * r2d - unit_cell[4]) < 0.1)

    wavelength = (unit_cell[0] / math.sqrt(a.dot()) + \
                  unit_cell[1] / math.sqrt(b.dot()) + \
                  unit_cell[2] / math.sqrt(c.dot())) / 3.0

    return wavelength
                  
def generate_lattice_options(unit_cell, space_group_name):
    cs = crystal.symmetry(
        unit_cell = unit_cell,
        space_group_symbol = space_group_name)

    original_reindex = cs.change_of_basis_op_to_minimum_cell()

    groups = metric_subgroups(input_symmetry = cs, max_delta = 0.0)

    result = []

    for item in groups.result_groups:        
        o_unit_cell = item['ref_subsym'].unit_cell().parameters()
        o_space_group_name = item['ref_subsym'].space_group().type(
            ).universal_hermann_mauguin_symbol()
        reindex = (item['subsym'].space_group_info().type().cb_op(
            ) * original_reindex).c().r().as_double()

        result.append((o_space_group_name, o_unit_cell, reindex))

    return result

def apply_reindex_operation(mosflm_a_matrix, mosflm_u_matrix, reindex):
    
    a = matrix.sqr(mosflm_a_matrix)
    u = matrix.sqr(mosflm_u_matrix)
    r = matrix.sqr(reindex).transpose()

    return a * r, u * r

def print_cell(cell):
    print '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % cell
    return

def print_reindex(reindex):
    print '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f % 6.2f %6.2f %6.2f' % reindex
    return

def compute_u(mosflm_a_matrix, unit_cell, wavelength):

    uc = uctbx.unit_cell(unit_cell)
    A = (1.0 / wavelength) * matrix.sqr(mosflm_a_matrix)
    B = matrix.sqr(uc.orthogonalization_matrix()).inverse()

    return A * B.inverse()

def macguffin(mosflm_matrix, space_group_name):

    cell, a, u = parse_matrix(mosflm_matrix)

    wavelength = calculate_wavelength(cell, a)
    
    options = generate_lattice_options(cell, space_group_name)

    for o_space_group_name, o_unit_cell, reindex in options:
        o_a, o_u = apply_reindex_operation(a, u, reindex)

        print o_space_group_name
        print format_matrix(o_unit_cell, o_a, o_u)
        # print_cell(o_unit_cell)
        # print_cell(mosflm_a_to_cell(o_a, wavelength))


if __name__ == '__main__':

    macguffin(open(sys.argv[1]).read(), sys.argv[2])

    
