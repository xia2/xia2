#!/usr/bin/env python
# Phil.py
#   Copyright (C) 2012 Diamond Light Source, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# Phil parameter setting - to get a single place where complex parameters to
# set for individual programs can be found. Initially this will be just a
# couple for XDS.

import os

from libtbx.phil import parse

from libtbx.phil import interface

master_phil = parse("""
xds {
  integrate {
    include scope Wrappers.XDS.XDSIntegrate.master_params
  }
  init {
    include scope Wrappers.XDS.XDSInit.master_params
  }
  index {
    include scope Wrappers.XDS.XDSIdxref.master_params
  }
  merge2cbf {
    include scope Wrappers.XDS.Merge2cbf.master_params
  }
}
dials {
  include scope Wrappers.Dials.Spotfinder.master_phil
}
deprecated_xds.parameter {
  delphi = 5
    .type = float
  delphi_small = 30
    .type = float
  untrusted_ellipse = None
    .type = ints(size = 4)
  untrusted_rectangle = None
    .type = ints(size = 4)
  xscale_min_isigma = 3.0
    .type = float
  trusted_region = None
    .type = floats(size = 2)
  profile_grid_size = None
    .type = ints(size = 2)
}
ccp4.reindex {
  program = 'pointless'
    .type = str
}
ccp4.truncate {
  program = 'ctruncate'
    .type = str
}
xia2.settings {
  show_template = False
    .type = bool
  untrusted_rectangle_indexing = None
    .type = ints(size = 4)
  xds_cell_deviation = 0.05, 5.0
    .type = floats(size = 2)
  developmental {
    use_dials_spotfinder = False
      .type = bool
      .help = "This feature requires the dials project to be installed, and"
              "is not currently intended for general use. Use at your peril!"
  }
}
""", process_includes=True)

PhilIndex = interface.index(master_phil=master_phil)

if __name__ == '__main__':
    PhilIndex.working_phil.show()
