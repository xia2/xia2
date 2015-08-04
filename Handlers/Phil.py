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
    refine = *DISTANCE *BEAM *AXIS *ORIENTATION *CELL *POSITION
      .type = choice(multi = True)
      .help = 'what to refine in the CORRECT step'
  }
  integrate {
    refine = *ORIENTATION *CELL *BEAM *DISTANCE AXIS *POSITION
      .type = choice(multi = True)
      .help = 'what to refine in first pass of integration'
    refine_final = *ORIENTATION *CELL BEAM DISTANCE AXIS POSITION
      .type = choice(multi = True)
      .help = 'what to refine in final pass of integration'
    fix_scale = False
      .type = bool
    delphi = 0
      .type = float
    reflecting_range = 0
      .type = float
    reflecting_range_esd = 0
      .type = float
    beam_divergence = 0
      .type = float
    beam_divergence_esd = 0
      .type = float
  }
  init {
    fix_scale = False
      .type = bool
  }
  index {
    refine = *ORIENTATION *CELL *BEAM *DISTANCE *AXIS *POSITION
      .type = choice(multi = True)
      .help = 'what to refine in autoindexing'
    debug = *OFF ON
      .type = choice(multi = False)
      .help = 'output enganced debugging for indexing'
  }
  colspot {
    minimum_pixels_per_spot = 1
      .type = int
  }
  xscale {
    min_isigma = 3.0
      .type = float
  }
  merge2cbf {
    merge_n_images = 2
      .type = int(value_min=1)
      .help = "Number of input images to average into a single output image"
    data_range = None
      .type = ints(size=2, value_min=0)
    moving_average = False
      .type = bool
      .help = "If true, then perform a moving average over the sweep, i.e. given"
              "images 1, 2, 3, 4, 5, 6, ..., with averaging over three images,"
              "the output frames would cover 1-3, 2-4, 3-5, 4-6, etc."
              "Otherwise, a straight summation is performed:"
              " 1-3, 4-6, 7-9, etc."
  }
}
dials {
  fix_geometry = False
    .type = bool
    .help = "Whether or not to refine geometry in dials.index and dials.refine."
            "Most useful when also providing a reference geometry to xia2."
  outlier_rejection = True
    .type = bool
    .help = "Whether to perform outlier rejection in dials.index and "
            "dials.refine (using Tukey method)."
  fast_mode = False
    .type = bool
  find_spots {
    min_spot_size = Auto
      .type = int
    min_local = 0
      .type = int
    phil_file = None
      .type = path
    sigma_strong = None
      .type = float
    filter_ice_rings = False
      .type = bool
    kernel_size = 3
      .type = int
    global_threshold = None
      .type = float
  }
  index {
    method = fft1d *fft3d real_space_grid_search
      .type = choice
    phil_file = None
      .type = path
    max_cell = 0.0
      .type = float
    use_all_reflections = False
      .type = bool
  }
  refine {
    scan_varying = True
      .type = bool
    interval_width_degrees = 36.0
      .help = "Width of scan between checkpoints in degrees"
      .type = float(value_min=0.)
    use_all_reflections = True
      .type = bool
    phil_file = None
      .type = path
    reflections_per_degree = 100
      .type = int
  }
  integrate {
    phil_file = None
      .type = path
    profile_fitting = True
      .type = bool
    background_outlier_algorithm = *null nsigma truncated normal tukey mosflm
      .type = choice
    background_algorithm = simple null *glm
      .type = choice
    use_threading = False
      .type = bool
    include_partials = True
      .type = bool
  }
}
ccp4 {
  truncate {
    program = 'ctruncate'
      .type = str
  }
  reindex {
    program = 'pointless'
      .type = str
  }
  aimless {
    intensities = summation profile *combine
      .type = choice
    surface_tie = 0.001
      .type = float
    surface_link = True
      .type = bool
  }
}
xia2.settings {
  input {
    image = None
      .type = path
      .multiple = True
      .help = "image=/path/to/an/image_001.img"
    json = None
      .type = path
      .help = "dxtbx-format datablock.json file which can be provided as an "
              "alternative source of images header information to avoid the "
              "need to read all the image headers on start-up."
    reference_geometry = None
      .type = path
      .multiple = True
      .help = "Experimental geometry from this datablock.json or "
              "experiments.json will override the geometry from the "
              "image headers."
    xinfo = None
      .type = path
      .help = "Provide an xinfo file as input as alternative to directory "
              "containing image files."
    min_images = 10
      .type = int(value_min=1)
      .help = "Minimum number of matching images to include a sweep in processing."
    min_oscillation_range = None
      .type = int(value_min=0)
      .help = "Minimum oscillation range of a sweep for inclusion in processing."
  }
  sweep
    .multiple = True
  {
    id = None
      .type = str
    range = None
      .type = ints(size=2)
    exclude = False
      .type = bool
  }
  scale {
    directory = Auto
      .type = str
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
  unify_setting = False
    .type = bool
    .help = "For one crystal, multiple orientations, unify U matrix"
  beam_centre = None
    .type = floats(size=2)
    .help = "Beam centre (x,y) coordinates (mm) using the Mosflm convention"
  trust_beam_centre = False
    .type = bool
    .help = "Whether or not to trust the beam centre in the image header."
            "If false, then labelit.index is used to determine a better beam "
            "centre during xia2 setup phase"
  wavelength_tolerance = 0.00001
    .type = float(value_min=0.0)
    .help = "Tolerance for accepting two different wavelengths as the same wavelength."
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
    pointless_tolerance = 0.0
      .type = float(value_min=0.0)
      .help = "Tolerance to use in POINTLESS for comparison of data sets"
  }
  xds {
    geometry_x = None
      .type = path
    geometry_y = None
      .type = path
  }
  indexer = mosflm labelit labelitii xds xdsii xdssum dials
    .type = choice
  refiner = mosflm xds dials
    .type = choice
  integrater = mosflmr xdsr mosflm xds dials
    .type = choice
  scaler = ccp4a xdsa
    .type = choice
  verbose = False
    .type = bool
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
