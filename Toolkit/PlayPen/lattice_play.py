from cctbx.sgtbx.lattice_symmetry import metric_subgroups
from cctbx import crystal
input_symmetry = crystal.symmetry(
    unit_cell=(20, 20, 20, 90, 90, 90),
    space_group_symbol = "P23")
groups = metric_subgroups(input_symmetry=input_symmetry, max_delta = 0.0)
for item in groups.result_groups:
    cell = item['ref_subsym'].unit_cell().parameters()
    spacegroup_name = item['ref_subsym'].space_group().type(
        ).universal_hermann_mauguin_symbol()
    reindex = item['cb_op_inp_best'].as_hkl()

    print '%20s' % spacegroup_name, '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
          cell, reindex

    print '%6.3f %6.3f %6.3f\n%6.3f %6.3f %6.3f\n%6.3f %6.3f %6.3f' % \
          item['cb_op_inp_best'].c().r().as_double()

