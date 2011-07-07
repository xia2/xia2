#!/usr/bin/env cctbx.python
# 
# Tests for SymmetryExpert.py
# 
# 7/JUL/2011
# 

from SymmetryExpert import mat_to_symop, symop_to_mat

import os
import math
from scitbx import matrix
from cctbx import sgtbx

def compare_matrices(a, b):
    assert(len(a) == len(b))

    for j in range(len(a)):
        assert(math.fabs(a[j] - b[j]) < 0.001)

    return

def get_list_of_symops():

    symops = []

    for record in open(os.path.join(os.environ['CLIBD'], 'symop.lib')):
        if not ' ' in record[:1]:
            continue
        symops.append(record.strip())

    return set(symops)

def new_symop_to_mat(symop):
    return matrix.sqr(sgtbx.rt_mx(
        sgtbx.parse_string(symop)).as_double_array()[:9]).transpose().elems

def new_mat_to_symop(mat):
    return sgtbx.rt_mx(matrix.sqr(mat).transpose(), (0, 0, 0)).as_xyz()

def work_mat_symop():

    for symop in get_list_of_symops():

        mat = symop_to_mat(symop)
        symop2 = mat_to_symop(mat)
        mat2 = symop_to_mat(symop2)
        mat3 = new_symop_to_mat(symop2)

        compare_matrices(mat, mat2)
        compare_matrices(mat, mat3)

        symop3 = new_mat_to_symop(mat)
        mat4 = new_symop_to_mat(symop3)
        compare_matrices(mat, mat4)


    return

if __name__ == '__main__':

    work_mat_symop()
