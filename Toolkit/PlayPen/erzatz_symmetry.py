from cctbx import sgtbx
from cctbx.sgtbx import pointgroup_tools
from cctbx.sgtbx import sub_lattice_tools
from cctbx import crystal

def demo():
    cs = crystal.symmetry(
        unit_cell = "40, 50, 60, 90, 90, 90",
        space_group_symbol = "Hall: P 1")

    sg_explorer = pointgroup_tools.space_group_graph_from_cell_and_sg(
        cs.unit_cell(), cs.space_group(), 3.0)

    for sg, cell in sg_explorer.return_likely_sg_and_cell():
        print '%20s' % sg.build_derived_point_group().type( \
            ).universal_hermann_mauguin_symbol(), \
              '%7.2f %7.2f %7.2f %7.2f %7.2f %7.2f' % cell.parameters()

if __name__ == '__main__':

    demo()
