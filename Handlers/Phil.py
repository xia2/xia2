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

from libtbx.phil import interface
from iotbx.phil import parse

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
  colspot {
    include scope Wrappers.XDS.XDSColspot.master_params
  }
  merge2cbf {
    include scope Wrappers.XDS.Merge2cbf.master_params
  }
}
dials {
  phil_file = None
    .type = path
  # FIXME all of these should go away - until we put things back in
  # explicitly
  # include scope Wrappers.Dials.Spotfinder.master_phil
  spotfinder {
    phil_file = None
      .type = path
  }
  index {
    method = fft1d fft3d real_space_grid_search
      .type = choice
    phil_file = None
      .type = path
  }
  # FIXME to here
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
  unit_cell = None
    .type = unit_cell
    .help = "Provide a target unit cell to the indexing program"
  space_group = None
    .type = space_group
    .help = "Provide a target space group to the indexing program"
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
  multiprocessing {
    mode = *serial parallel
      .type = choice
      .help = "Whether to process each sweep in serial (using n processes per"
              " sweep) or to process sweeps in parallale (using 1 process per"
              " sweep)."
    nproc = Auto
      .type = int(value_min=1)
  }
}
""", process_includes=True)

PhilIndex = interface.index(master_phil=master_phil)

if __name__ == '__main__':
  PhilIndex.working_phil.show()
