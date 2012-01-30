import os
import sys
import math
from cctbx import uctbx
from cctbx.sgtbx import space_group, change_of_basis_op
from cctbx.sgtbx import space_group_symbols
from cctbx import crystal
from scitbx import matrix

def reflection_list(unit_cell_constants, high_resolution_limit):

    uc = uctbx.unit_cell(unit_cell_constants)
    maxh, maxk, maxl = uc.max_miller_indices(high_resolution_limit)

    indices = []

    for h in range(-maxh, maxh + 1):
        for k in range(-maxk, maxk + 1):
            for l in range(-maxl, maxl + 1):

                # ignore reflection (0, 0, 0)
                if h == 0 and k == 0 and l == 0:
                    continue

                # and test the resolution limit
                if uc.d((h, k, l)) < high_resolution_limit:
                    continue

                # ok, then store
                indices.append((h, k, l))

    return indices

def remove_sys_absences(reflection_list, space_group_name):

    sg = space_group(space_group_symbols(space_group_name).hall())

    present_reflections = []

    for hkl in reflection_list:
        if not sg.is_sys_absent(hkl):
            present_reflections.append(hkl)

    return present_reflections

def read_integrate_hkl_header(integrate_hkl):

    unit_cell = None

    for record in open(integrate_hkl):
        if not '!' in record[:1]:
            break

        if 'UNIT_CELL_CONSTANTS=' in record:
            unit_cell = map(float, record.split()[-6:])

    return unit_cell

def read_integrate_hkl(integrate_hkl):

    reflections = []

    for record in open(integrate_hkl):
        if not '!' in record[:1]:
            values = record.split()
            hkl = tuple(map(int, values[:3]))
            isigi = tuple(map(float, values[3:5]))
            reflections.append((hkl, isigi))

    return reflections

def mean_variance(values):
    mean = sum(values) / len(values)
    variance = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, variance, math.sqrt(variance)

def quartiles(values):
    values.sort()
    return tuple([values[i] for i in
            [len(values) // 4, len(values) // 2, 3 * len(values) // 4]])

def doohicky(integrate_hkl, space_group_name, symop):

    present = []
    absent = []

    sg = space_group(space_group_symbols(space_group_name).hall())

    r = change_of_basis_op(symop)

    for hkl, isig in read_integrate_hkl(integrate_hkl):
        rhkl = tuple(map(int, r.c() * hkl))
        if sg.is_sys_absent(rhkl):
            absent.append(isig[0])
        else:
            present.append(isig[0])

    print 'Present: %.2e %.2e %.2e' % mean_variance(present), \
          '%.2e %.2e %.2e' % quartiles(present)
    print 'Absent:  %.2e %.2e %.2e' % mean_variance(absent), \
          '%.2e %.2e %.2e' % quartiles(absent)


if __name__ == '__main__':

    doohicky(sys.argv[1], sys.argv[2], sys.argv[3])
