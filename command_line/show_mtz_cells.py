# LIBTBX_SET_DISPATCHER_NAME dev.xia2.show_mtz_cells

import sys
import os

# Needed to make xia2 imports work correctly
import libtbx.load_env
from iotbx import mtz

for f in os.listdir('DataFiles'):
  if f.endswith('.mtz'):
    print f
    for c in mtz.object(os.path.join('DataFiles', f)).crystals():
      print "%20s: %7.3f %7.3f %7.3f  %7.3f %7.3f %7.3f" % tuple([c.name()] + list(c.unit_cell_parameters()))
