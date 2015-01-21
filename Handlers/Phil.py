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
import sys

if not os.environ.has_key('XIA2CORE_ROOT'):
  raise RuntimeError, 'XIA2CORE_ROOT not defined'

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.path.join(os.environ['XIA2CORE_ROOT'],
                    'Python') in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2CORE_ROOT'],
                               'Python'))

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.environ['XIA2_ROOT'])

from libtbx.phil import interface
from iotbx.phil import parse

master_phil = parse("""
general {
  check_image_files_readable = True
    .type = bool
}
xds {
  delphi = 5
    .type = float
  delphi_small = 30
    .type = float
  untrusted_ellipse = None
    .type = ints(size = 4)
  untrusted_rectangle = None
    .type = ints(size = 4)
  trusted_region = None
    .type = floats(size = 2)
  profile_grid_size = None
    .type = ints(size = 2)
  correct {
    include scope Wrappers.XDS.XDSCorrect.master_params
  }
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
  xscale {
    min_isigma = 3.0
      .type = float
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
    min_spot_size = Auto
      .type = int
    phil_file = None
      .type = path
  }
  index {
    method = fft1d *fft3d real_space_grid_search
      .type = choice
    phil_file = None
      .type = path
    max_cell = 0.0
      .type = float
  }
  refine {
    scan_varying = True
      .type = bool
    use_all_reflections = False
      .type = bool
    phil_file = None
      .type = path
    reflections_per_degree = 100
      .type = int
  }
  integrate {
    phil_file = None
      .type = path
    intensity_algorithm = sum3d sum2d *fitrs mosflm
      .type = choice
    background_outlier_algorithm = *null nsigma truncated normal
      .type = choice
    use_threading = False
      .type = bool
  }
  # FIXME to here
}
ccp4 {
  truncate {
    program = 'ctruncate'
      .type = str
  }
  aimless {
    intensities = summation profile *combine
      .type = choice
  }
}
xia2.settings {
  input {
    json = None
      .type = path
      .help = "dxtbx-format datablock.json file which can be provided as an "
              "alternative source of images header information to avoid the "
              "need to read all the image headers on start-up."
  }
  unit_cell = None
    .type = unit_cell
    .help = "Provide a target unit cell to the indexing program"
  space_group = None
    .type = space_group
    .help = "Provide a target space group to the indexing program"
  d_min = None
    .type = float(value_min=0.0)
    .help = "High resolution cutoff."
  d_max = None
    .type = float(value_min=0.0)
    .help = "Low resolution cutoff."
  optimize_scaling = False
    .type = bool
    .help = "Search for best scaling model"
  beam_centre = None
    .type = floats(size=2)
    .help = "Beam centre (x,y) coordinates (mm) using the Mosflm convention"
  trust_beam_centre = False
    .type = bool
    .help = "Whether or not to trust the beam centre in the image header."
            "If false, then labelit.index is used to determine a better beam "
            "centre during xia2 setup phase"
  read_all_image_headers = True
    .type = bool
  detector_distance = None
    .type = float(value_min=0.0)
    .help = "Distance between sample and detector (mm)"
  show_template = False
    .type = bool
  untrusted_rectangle_indexing = None
    .type = ints(size = 4)
  xds_cell_deviation = 0.05, 5.0
    .type = floats(size = 2)
  use_brehm_diederichs = False
    .type = bool
    .help = "Use the Brehm-Diederichs algorithm to resolve an indexing "
            "ambiguity."
            "See: W. Brehm and K. Diederichs, Acta Cryst. (2014). D70, 101-109."
  developmental {
    use_dials_spotfinder = False
      .type = bool
      .help = "This feature requires the dials project to be installed, and"
              "is not currently intended for general use. Use at your peril!"
  }
  xds {
    geometry_x = None
      .type = path
    geometry_y = None
      .type = path
  }
  indexer = mosflm labelit labelitii xds xdsii xdssum dials
    .type = choice
  integrater = mosflmr xdsr mosflm xds dials
    .type = choice
  scaler = ccp4a xdsa
    .type = choice
  multiprocessing {
    mode = *serial parallel
      .type = choice
      .help = "Whether to process each sweep in serial (using n processes per"
              " sweep) or to process sweeps in parallel (using 1 process per"
              " sweep)."
    nproc = Auto
      .type = int(value_min=1)
      .help = "The number of processors to use per job."
    njob = Auto
      .type = int(value_min=1)
      .help = "The number of sweeps to process simultaneously."
    type = *simple qsub
      .type = choice
      .help = "How to run the parallel processing jobs, e.g. over a cluster"
    qsub_command = ''
      .type = str
      .help = "The command to use to submit qsub jobs"
  }
}
""", process_includes=True)

PhilIndex = interface.index(master_phil=master_phil)

if __name__ == '__main__':
  PhilIndex.working_phil.show()
