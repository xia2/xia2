from cctbx import sgtbx
for space_group_number in range(1, 231):
  spacegroup = sgtbx.space_group_symbols(space_group_number).hall()
  sg = sgtbx.space_group(spacegroup)
  print '%3d %3d %3d %3d %3d' % (space_group_number, sg.f_inv(), sg.n_smx(),
                                 sg.n_ltr(), len(sg.all_ops()))
