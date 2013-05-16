
def generate_asu(unit_cell_constants, space_group_number, dmin):
    
    from cctbx.uctbx import unit_cell
    from cctbx.crystal import symmetry
    from cctbx.sgtbx import space_group, space_group_symbols, rt_mx, \
         change_of_basis_op
    from cctbx.array_family import flex
    from cctbx import miller
    
    uc = unit_cell(unit_cell_constants)
    sg = space_group(space_group_symbols(space_group_number).hall())
    xs = symmetry(unit_cell = uc, space_group = sg)

    maxh, maxk, maxl = uc.max_miller_indices(dmin)

    indices = flex.miller_index()

    for h in range(-maxh, maxh + 1):
        for k in range(-maxk, maxk + 1):
            for l in range(-maxl, maxl + 1):
                
                if h == 0 and k == 0 and l == 0:
                    continue
                
                if uc.d((h, k, l)) < dmin:
                    continue

                if not sg.is_sys_absent((h, k, l)):
                    indices.append((h, k, l))

    ms = miller.set(xs, indices, False).map_to_asu()

    indices = set(ms.indices())

    from scitbx import matrix

    other_hand = change_of_basis_op(rt_mx('-k,-h,l'))
    # other_hand = change_of_basis_op(rt_mx('-h,-k,l'))

    from collections import defaultdict

    mappings = defaultdict(int)

    for i in indices:
        if i[0] == i[1] or i[1] == i[2] or i[2] == i[0]:
            continue

        found = False

        for smx in sg.smx():
            op = change_of_basis_op(smx) * other_hand
            j = op.apply(i)
            if j in indices:
                mappings[op.as_hkl()] += 1
                found = True

        if not found:
            print i
            print 1/0

    for m in mappings:
        print m, mappings[m]

    return


generate_asu((106,106,106,90,90,90), 197, 3.0)    
