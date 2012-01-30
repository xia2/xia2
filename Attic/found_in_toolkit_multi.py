from cctbx import uctbx
from cctbx import sgtbx
from cctbx import crystal
from cctbx.sgtbx import lattice_symmetry
from cctbx.sgtbx import subgroups

# first construct the input

uc = uctbx.unit_cell([102, 102, 102, 90, 90, 90])
sg = sgtbx.space_group_type('I 2 3').group()

correct_symops = list(sg.smx())

cs = crystal.symmetry(unit_cell = uc,
                      space_group = sg)

print '%.1f %.1f %.1f %.1f %.1f %.1f' % cs.unit_cell().parameters()

# then convert this to a primitive basis

cb_op = cs.change_of_basis_op_to_minimum_cell()
ms = cs.change_basis(cb_op)

print '%.1f %.1f %.1f %.1f %.1f %.1f' % ms.unit_cell().parameters()
print ms.space_group().type().universal_hermann_mauguin_symbol()
print cs.space_group().type().universal_hermann_mauguin_symbol()

# now generate a list of possible lattices / spacegroups

sgi = sgtbx.space_group_info(group = lattice_symmetry.group(ms.unit_cell()))

sgs = subgroups.subgroups(sgi).groups_parent_setting()

# the question I am asking is: given the lattice symmetry, give me a list of
# symmetry operators which are possible, but are not in the correct spacegroup

spacegroups = []

for sg in sgs:
    sup = sgtbx.space_group_info(group = sg).type(
        ).expand_addl_generators_of_euclidean_normalizer(
        True,True).build_derived_acentric_group()

    spacegroups.append((sup.type().number(), sup))

spacegroups.sort()

cs2 = crystal.symmetry(unit_cell = ms.unit_cell(),
                       space_group = spacegroups[-1][1])

cs3 = cs2.change_basis(cs2.space_group().type().cb_op())

print cs3.unit_cell(), cs3.space_group().type().universal_hermann_mauguin_symbol()

all_symops = list(cs3.space_group().smx())

for symop in all_symops:

    print symop, (symop in correct_symops)
