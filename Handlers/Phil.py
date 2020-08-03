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


from iotbx.phil import parse
from libtbx.phil import interface

master_phil = parse(
    """
general
  .short_caption = "General settings"
{
  check_image_files_readable = True
    .type = bool
    .expert_level = 2
}
xds
  .short_caption = "XDS settings"
{
  hdf5_plugin = "durin-plugin.so"
    .type = path
    .help = "HDF5 plugin file reader name, either filename or full path"
    .short_caption = "LIB=/path/to/(this)"
    .expert_level = 1
  z_min = 0.0
    .type = float
    .short_caption = "Mark Wilson outlier when Z-score greater than"
    .expert_level = 1
  delphi = 5
    .type = float
    .short_caption = "DELPHI ="
    .expert_level = 1
  delphi_small = 30
    .type = float
    .short_caption = "For small molecule mode, DELPHI ="
    .expert_level = 1
  untrusted_ellipse = None
    .type = ints(size = 4)
    .multiple = True
    .short_caption = "UNTRUSTED_ELLIPSE ="
    .expert_level = 1
  untrusted_rectangle = None
    .type = ints(size = 4)
    .multiple = True
    .short_caption = "UNTRUSTED_RECTANGLE ="
    .expert_level = 1
  trusted_region = None
    .type = floats(size = 2)
    .short_caption = "TRUSTED_REGION ="
    .expert_level = 1
  backstop_mask = None
    .type = path
    .short_caption = "Backstop mask"
    .expert_level = 1
  profile_grid_size = None
    .short_caption = "Number of profile grid points"
    .help = "Sets XDS parameters NUMBER_OF_PROFILE_GRID_POINTS_ALONG_ALPHA/BETA " \
            "and NUMBER_OF_PROFILE_GRID_POINTS_ALONG_GAMMA."
    .type = ints(size = 2)
    .expert_level = 1
  keep_outliers = True
    .type = bool
    .short_caption = "Keep outliers"
    .help = "Do not remove outliers in integration and scaling"
  correct {
    refine = *DISTANCE *BEAM *AXIS *ORIENTATION *CELL *POSITION
      .type = choice(multi = True)
      .short_caption = "REFINE(CORRECT) ="
      .help = 'what to refine in the CORRECT step'
      .expert_level = 1
    air = None
      .type = float(value_min=0)
      .short_caption = "AIR ="
      .expert_level = 1
  }
  integrate {
    refine = *ORIENTATION *CELL *BEAM *DISTANCE AXIS *POSITION
      .type = choice(multi = True)
      .short_caption = "First pass REFINE(INTEGRATE) ="
      .help = 'what to refine in first pass of integration'
      .expert_level = 1
    refine_final = *ORIENTATION *CELL BEAM *DISTANCE AXIS *POSITION
      .type = choice(multi = True)
      .short_caption = "Final pass REFINE(INTEGRATE) ="
      .help = 'What to refine in final pass of integration'
      .expert_level = 1
    fix_scale = False
      .type = bool
      .short_caption = "Fix scale factors"
      .expert_level = 1
    delphi = 0
      .type = float
      .short_caption = "DELPHI ="
      .expert_level = 1
    reflecting_range = 0
      .type = float
      .short_caption = "REFLECTING_RANGE ="
      .expert_level = 1
    reflecting_range_esd = 0
      .type = float
      .short_caption = "REFLECTING_RANGE_E.S.D. ="
      .expert_level = 1
    beam_divergence = 0
      .type = float
      .short_caption = "BEAM_DIVERGENCE ="
      .expert_level = 1
    beam_divergence_esd = 0
      .type = float
      .short_caption = "BEAM_DIVERGENCE_E.S.D. ="
      .expert_level = 1
    reintegrate = true
      .type = bool
      .short_caption = "Reintegrate after global refinement"
      .expert_level = 1
  }
  init {
    fix_scale = False
      .type = bool
      .short_caption = "Fix scale factors"
      .expert_level = 1
  }
  defpix {
    value_range_for_trusted_detector_pixels = None
      .type = ints(size=2)
      .short_caption = "VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS ="
      .expert_level = 1
  }
  index {
    refine = *ORIENTATION *CELL *BEAM *DISTANCE *AXIS *POSITION
      .type = choice(multi = True)
      .short_caption = "REFINE(IDXREF) ="
      .help = 'what to refine in autoindexing'
      .expert_level = 1
    debug = *OFF ON
      .type = choice(multi = False)
      .short_caption = "Debug"
      .help = 'output enhanced debugging for indexing'
      .expert_level = 1
    xparm = None
      .type = path
      .short_caption = "Use GXPARM.XDS geometry"
      .help = 'Use refined GXPARM.XDS geometry in indexing'
      .expert_level = 1
    xparm_ub = None
      .type = path
      .short_caption = "Use GXPARM.XDS UB matrix"
      .help = 'Use refined GXPARM.XDS orientation matrix in indexing'
      .expert_level = 1
    max_wedge_size = 5
      .type = int(value_min=1)
    max_wedge_size_degrees = None
      .type = float(value_min=0)
  }
  colspot {
    minimum_pixels_per_spot = 2
      .short_caption = "For PAD MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT ="
      .type = int
      .expert_level = 1
  }
  xscale {
    min_isigma = 3.0
      .type = float
      .short_caption = "MINIMUM_I/SIGMA ="
      .expert_level = 1
    zero_dose = False
      .type = bool
      .short_caption = "Zero dose extrapolation"
      .help = "Enable XSCALE zero dose extrapolation"
      .expert_level = 1
  }
  merge2cbf {
    merge_n_images = 2
      .type = int(value_min=1)
      .short_caption = "Number of images"
      .help = "Number of input images to average into a single output image"
      .expert_level = 1
    data_range = None
      .type = ints(size=2, value_min=0)
      .short_caption = "Data range"
      .expert_level = 1
    moving_average = False
      .type = bool
      .short_caption = "Moving average"
      .help = "If true, then perform a moving average over the sweep, i.e. given " \
              "images 1, 2, 3, 4, 5, 6, ..., with averaging over three images, " \
              "the output frames would cover 1-3, 2-4, 3-5, 4-6, etc. " \
              "Otherwise, a straight summation is performed: " \
              "1-3, 4-6, 7-9, etc."
      .expert_level = 1
  }
}
dials
  .short_caption = "DIALS settings"
{
  fix_geometry = False
    .type = bool
    .help = "Whether or not to refine geometry in dials.index and dials.refine. " \
            "Most useful when also providing a reference geometry to xia2."
    .short_caption = "Fix geometry"
    .expert_level = 1
  fix_distance = False
    .type = bool
    .help = "Do not refine the detector distance in dials.index and dials.refine."
    .short_caption = "Fix distance"
    .expert_level = 1
  outlier
    .short_caption = "Centroid outlier rejection"
  {
    algorithm = null *auto mcd tukey sauter_poon
      .type = choice
      .short_caption = "Outlier rejection algorithm"
      .expert_level = 1
  }
  check_indexing_symmetry = False
    .type = bool
    .expert_level = 2
  fast_mode = False
    .type = bool
    .help = "Set various parameters for rapid processing, compromising on quality"
    .short_caption = "Fast mode"
    .expert_level = 1
  close_to_spindle_cutoff = 0.02
    .type = float(value_min=0.0)
    .short_caption = "Closeness to the spindle cutoff for including " \
                     "reflections in refinement"
    .expert_level = 2

  detect_blanks {
    phi_step = 2
      .help = "Width of bins in degrees."
      .type = float(value_min=0, allow_none=True)
    counts_fractional_loss = 0.1
      .help = "Fractional loss (relative to the bin with the most counts) after " \
              "which a bin is flagged as potentially containing blank images."
      .type = float(value_min=0, value_max=1, allow_none=True)
    misigma_fractional_loss = 0.1
      .help = "Fractional loss (relative to the bin with the highest misigma) " \
              "after  which a bin is flagged as potentially containing blank " \
              "images."
      .type = float(value_min=0, value_max=1, allow_none=True)
  }

  masking
    .short_caption = "Masking"
    .expert_level = 1
  {
    include scope dials.util.masking.phil_scope
  }

  find_spots
    .short_caption = "Spot finding"
  {
    phil_file = None
      .type = path
      .short_caption = "phil file to pass to dials.find_spots"
      .expert_level = 1
    threshold.algorithm = dispersion dispersion_extended
      .type = choice
      .expert_level = 2
    min_spot_size = None
      .type = int
      .help = "The minimum number of contiguous pixels for a spot to be " \
              "accepted by the filtering algorithm."
      .short_caption = "Minimum spot size"
      .expert_level = 1
    min_local = 0
      .type = int
      .help = "The minimum number of pixels under the image processing " \
              "kernel that are need to do the thresholding operation. " \
              "Setting the value between 2 and the total number of pixels " \
              "under the kernel will force the algorithm to use that number " \
              "as the minimum. If the value is less than or equal to zero, " \
              "then the algorithm will use all pixels under the kernel. In " \
              "effect this will add a border of pixels which are always " \
              "classed as background around the edge of the image and around " \
              "any masked out pixels."
      .expert_level = 2
    sigma_strong = None
      .type = float
      .help = "The number of standard deviations above the mean in the local " \
              "area above which the pixel will be classified as strong."
      .short_caption = "Strong pixel sigma cutoff"
      .expert_level = 1
    filter_ice_rings = False
      .type = bool
      .short_caption = "Filter ice rings"
    kernel_size = 3
      .type = int
      .help = "The size of the local area around the spot in which to " \
              "calculate the mean and variance. The kernel is given as a box"
      .expert_level = 1
    global_threshold = None
      .type = float
      .help = "The global threshold value. Consider all pixels less than " \
              "this value to be part of the background."
      .short_caption = "Global threshold cutoff"
      .expert_level = 1
  }
  index
    .short_caption = "Indexing"
  {
    phil_file = None
      .type = path
      .short_caption = "phil file to pass to dials.index"
      .expert_level = 1
    method = fft1d *fft3d real_space_grid_search
      .type = choice
      .short_caption = "Indexing method"
    max_cell = 0.0
      .type = float
      .help = "Maximum length of candidate unit cell basis vectors (in Angstrom)."
      .short_caption = "Maximum cell length"
      .expert_level = 1
    #include scope dials.algorithms.indexing.indexer.max_cell_estimation
    max_cell_estimation {
      max_height_fraction = None
        .type = float(value_min=0, value_max=1)
        .expert_level = 2
    }
    fft3d.n_points = None
      .type = int(value_min=0)
      .short_caption = "Number of reciprocal space grid points"
      .expert_level = 2
    reflections_per_degree = 100
      .type = int
      .short_caption = "Number of reflections per degree for random subset"
      .expert_level = 1
    histogram_binning = linear log
      .type = choice
      .help = "Choose between linear or logarithmic bins for nearest neighbour"
              "histogram analysis."
      .expert_level = 2
    nearest_neighbor_percentile = None
      .type = float(value_min=0, value_max=1)
      .help = "Percentile of NN histogram to use for max cell determination."
      .expert_level = 2
  }
  refine
    .short_caption = "Refinement"
    .expert_level = 1
  {
    phil_file = None
      .type = path
      .short_caption = "phil file to pass to dials.refine"
    scan_static = True
      .expert_level = 2
      .type = bool
    scan_varying = True
      .type = bool
      .short_caption = "Fit a scan-varying model"
    interval_width_degrees = 36.0
      .type = float(value_min=0.)
      .help = "Width of scan between checkpoints in degrees"
      .short_caption = "Interval width between checkpoints (if scan-varying)"
    reflections_per_degree = 100
      .type = int
      .short_caption = "Number of reflections per degree for random subset"
    include scope dials.algorithms.refinement.restraints.restraints_parameterisation.uc_phil_scope
  }
  integrate
    .expert_level = 1
    .short_caption = "Integration"
  {
    phil_file = None
      .type = path
      .short_caption = "phil file to pass to dials.integrate"
    background_outlier_algorithm = *null nsigma truncated normal plane tukey
      .type = choice
      .help = "Outlier rejection performed prior to background fit"
      .short_caption = "Outlier rejection method"
    background_algorithm = simple null *glm
      .type = choice
      .short_caption = "Background fit method"
    combine_partials = True
      .type = bool
      .help = "Combine partial reflections for output"
    partiality_threshold = 0.99
      .type = float
      .help = "Minimum combined partiality for output"
    mosaic = *old new
      .type = choice
      .help = "Mosaicity determination method to use"
      .expert_level = 2
    scan_varying_profile = False
      .type = bool
      .help = "Use scan varying profile model in integration"
      .expert_level = 2
    d_min = None
      .type = float(value_min=0.0)
      .short_caption = "High resolution cutoff for integration"
      .expert_level = 1
    d_max = None
      .type = float(value_min=0.0)
      .short_caption = "Low resolution cutoff for integration"
      .expert_level = 1
    min_spots
      .short_caption = "Override default profile parameters of dials.integrate"
    {
      overall = None
        .type = int(value_min=1)
        .optional = True
        .help = "Minimum number of reflections required to perform profile "
                "modelling."

      per_degree = None
        .type = int(value_min=0)
        .optional = True
        .help = "Minimum number of reflections per degree of sweep required to perform "
                "profile modelling."
    }
  }

  high_pressure
    .expert_level = 1
    .short_caption = "Handle diamond anvil pressure cell data"
  {
    correction = False
      .type = bool
      .help = "Correct for attenuation by a diamond anvil cell"

    include scope dials.command_line.anvil_correction.phil_scope
  }

  scale
    .expert_level = 1
    .short_caption = "Scaling"
  {
    model = *auto physical dose_decay array KB
      .type = choice
      .help = "Choice of scaling model parameterisation to apply"
    rotation_spacing = None
      .type = float
      .help = "Parameter spacing for scale (rotation) term"
    Bfactor = True
      .type = bool
      .help = "Include decay component in scaling"
    absorption = True
      .type = bool
      .help = "Include an absorption correction in scaling"
    physical_model {
      Bfactor_spacing = None
        .type = float
        .help = "Parameter spacing for B-factor correction"
      lmax = 4
        .type = int(value_min=2)
        .help = "Order of spherical harmonics to use for absorption surface"
    }
    dose_decay_model {
      share.decay = True
        .type = bool
        .help = "Share the decay model between sweeps."
        .expert_level = 1
      resolution_dependence = *quadratic linear
        .type = choice
        .help = "Use a dose model that depends linearly or quadratically on 1/d"
        .expert_level = 1
      lmax = 4
        .type = int(value_min=2)
        .help = "Order of spherical harmonics to use for absorption surface"
    }
    array_model {
      resolution_bins = 10
        .type = int(value_min=1)
        .help = "Number of bins to parameterise decay component"
      absorption_bins = 5
        .type = int(value_min=1)
        .help = "Number of bins in each dimension (applied to both x and y) for " \
                "binning the detector position for the absorption term of the " \
                "array model."
    }
    intensity_choice = profile summation *combine
      .type = choice
      .help = "Choose from profile fitted or summation intensities, or " \
              "an optimised combination of profile/sum."
    error_model = *basic None
      .type = choice
      .help = "Choice of whether to refine an error model to adjust the" \
              "intensity sigmas using a two-parameter model."
    full_matrix = True
      .type = bool
      .help = "Option to turn off GN/LM refinement round used to determine " \
              "error estimates on scale factors."
    outlier_rejection = *standard simple
      .type = choice
      .help = "Choice of outlier rejection routine. Standard may take a " \
              "significant amount of time to run for large datasets or high " \
              "multiplicities, whereas simple should be quick for these datasets."
    outlier_zmax = 6.0
      .type = float(value_min=3.0)
      .help = "Cutoff z-score value for identifying outliers based on their " \
              "normalised deviation within the group of equivalent reflections"
    partiality_threshold = 0.4
      .type = float
      .help = "Minimum partiality to use for scaling and for post-scaling " \
              "exported output."
  }
}
ccp4
  .short_caption = "CCP4 data reduction options"
  .expert_level = 1
{
  reindex
    .short_caption = "reindex"
  {
    program = *pointless reindex cctbx
      .type = choice
  }
  aimless
    .short_caption = "aimless"
  {
    intensities = summation profile *combine
      .type = choice
    surface_tie = 0.001
      .type = float
      .short_caption = "Surface tie"
    surface_link = True
      .type = bool
      .short_caption = "Surface link"
    rotation.spacing = 5
      .type = int
      .expert_level = 2
      .short_caption = "Interval (in degrees) between scale factors on rotation axis"
    brotation.spacing = None
      .type = int
      .expert_level = 2
      .short_caption = "Interval (in degrees) between B-factors on rotation axis"
    secondary {
      frame = camera *crystal
        .type = choice
        .help = "Whether to do the secondary beam correction in the camera spindle " \
                "frame or the crystal frame"
      lmax = 6
        .type = int
        .expert_level = 2
        .short_caption = "Aimless # secondary harmonics"
    }

  }
  truncate
    .short_caption = "truncate"
  {
    program = ctruncate *cctbx
      .type = choice
  }
}
strategy
  .multiple = True
  .optional = True
  .short_caption = "Strategy"
  .expert_level = 1
{
  name = None
    .type = str
    .help = "A name for this strategy."
  description = None
    .type = str
    .help = "A description associated with this strategy."
  i_over_sigi = 2.0
    .type = float(value_min=0.0)
    .help = "Target <I/SigI> at highest resolution."
  minimize_total_time = False
    .type = bool
  target_resolution = None
    .type = float(value_min=0.0)
  max_total_exposure = None
    .type = float(value_min=0.0)
    .help = "maximum total exposure/measurement time, sec, default unlimited"
  anomalous = False
    .type = bool
  dose_rate = 0.0
    .type = float(value_min=0.0)
    .help = "dose rate, Gray per Second, default 0.0 - radiation damage neglected"
  shape = 1.0
    .type = float(value_min=0.0)
    .help = "shape factor, default 1, - increase for large crystal in a small beam"
  susceptibility = 1.0
    .type = float(value_min=0.0)
    .help = "increase for radiation-sensitive crystals"
  completeness = 0.99
    .type = float(value_min=0.0, value_max=1.0)
    .help = "Target completeness"
  multiplicity = None
    .type = float(value_min=0.0)
    .help = "Target multiplicity"
  phi_range = None
    .type = floats(size=2)
    .help = "Starting phi angle and total phi rotation range"
  min_oscillation_width = 0.05
    .type = float(value_min=0.0)
    .help = "Minimum rotation width per frame (degrees)"
  xml_out = None
    .type = path
    .help = "XML-formatted data stored in file"
  max_rotation_speed = None
    .type = float(value_min=0.0)
    .help = "Maximum rotation speed (deg/sec)"
  min_exposure = None
    .type = float(value_min=0.0)
    .help = "Minimum exposure per frame (sec)"
}
xia2.settings
  .short_caption = "xia2 settings"
{
  pipeline = 3d 3dd 3di 3dii *dials dials-aimless
    .short_caption = "main processing pipeline"
    .help = "Select the xia2 main processing pipeline\n" \
            "   3d: XDS, XSCALE\n" \
            "  3di: as 3d, but use 3 wedges for indexing\n" \
            " 3dii: XDS, XSCALE, using all images for autoindexing\n" \
            "  3dd: as 3d, but use DIALS for indexing\n" \
            "dials: DIALS, including scaling\n" \
            "dials-aimless: DIALS, scaling with AIMLESS\n"
    .type = choice
  small_molecule = False
    .type = bool
    .short_caption = "Use small molecule settings"
    .help = "Assume that the dataset comes from a " \
            "chemical crystallography experiment"
    .expert_level = 1
  small_molecule_bfactor = True
    .type = bool
    .short_caption = "B factor scaling for small molecule sets"
    .help = "Use B factor scaling for small molecule sets"
    .expert_level = 2
  failover = False
    .type = bool
    .short_caption = 'Fail over gracefully'
    .help = 'If processing a sweep fails, keep going'
    .expert_level = 1
  multi_crystal = False
    .type = bool
    .short_caption = 'Settings for working with multiple crystals'
    .help = 'Settings for working with multiple crystals'
    .expert_level = 1
  interactive = False
    .type = bool
    .short_caption = 'Interactive indexing'
    .expert_level = 1
  project = 'AUTOMATIC'
    .type = str
    .help = "A name for the data processing project"
  crystal = 'DEFAULT'
    .type = str
    .help = "A name for the crystal"
  input
    .short_caption = "xia2 input settings"
  {
    atom = None
      .type = str
      .short_caption = "Heavy atom name, optional"
      .help = "Set the heavy atom name, if appropriate"
    anomalous = Auto
      .type = bool
      .short_caption = "Separate anomalous pairs in merging"
    working_directory = None
      .type = path
      .short_caption = "Working directory (i.e. not $CWD)"
      .expert_level = 1
    image = None
      .type = path
      .multiple = True
      .help = "image=/path/to/an/image_001.img"
      .short_caption = "Path to an image file"
      .expert_level = 1
    json = None
      .type = path
      .multiple = True
      .help = "dxtbx-format models.expt file which can be provided as an " \
              "alternative source of images header information to avoid the " \
              "need to read all the image headers on start-up."
      .short_caption = "Take headers from json file"
      .expert_level = 1
    reference_geometry = None
      .type = path
      .multiple = True
      .help = "Experimental geometry from this models.expt will " \
              "override the geometry from the image headers."
      .short_caption = "Take experimental geometry from json file"
      .expert_level = 1
    xinfo = None
      .type = path
      .help = "Provide an xinfo file as input as alternative to directory " \
              "containing image files."
      .short_caption = "Use xinfo instead of image directory"
      .expert_level = 1
    reverse_phi = False
      .type = bool
      .help = "Reverse the direction of the phi axis rotation."
      .short_caption = "Reverse rotation axis"
      .expert_level = 1
    gain = None
      .type = float
      .help = "Detector gain if using DIALS"
      .short_caption = "Detector gain"
      .expert_level = 1
    min_images = 10
      .type = int(value_min=1)
      .help = "Minimum number of matching images to include a sweep in processing."
      .short_caption = "Minimum number of matching images"
      .expert_level = 1
    min_oscillation_range = None
      .type = int(value_min=0)
      .help = "Minimum oscillation range of a sweep for inclusion in processing."
      .short_caption = "Minimum oscillation range"
      .expert_level = 1
    include scope dials.util.options.tolerance_phil_scope
    include scope dials.util.options.geometry_phil_scope
    include scope dials.util.options.format_phil_scope

  }
  sweep
    .multiple = True
    .expert_level = 2
    .short_caption = "xia2 sweep"
  {
    id = None
      .type = str
    range = None
      .type = ints(size=2)
    exclude = False
      .type = bool
  }
  scale
    .expert_level = 1
    .short_caption = "Scaling"
  {
    directory = Auto
      .type = str
      .short_caption = "xia2 scale directory"
    free_fraction = 0.05
      .type = float(value_min=0.0, value_max=1.0)
      .help = "Fraction of free reflections"
    free_total = None
      .type = int(value_min=0)
      .help = "Total number of free reflections"
    freer_file = None
      .type = path
      .help = "Copy freer flags from this file"
    reference_reflection_file = None
      .type = path
      .help = "Reference file for testing of alternative indexing schemes"
    reference_experiment_file = None
      .type = path
      .help = "Reference models.expt for testing of alternative indexing schemes"
    model = *decay *modulation *absorption partiality
      .type = choice(multi=True)
      .short_caption = "Scaling models to apply"
    scales = *rotation batch
      .type = choice
      .short_caption = "Smoothed or batch scaling"
    two_theta_refine = True
      .type = bool
      .short_caption = "Run dials.two_theta_refine"
      .help = "Run dials.two_theta_refine to refine the unit cell and obtain " \
              "estimated standard uncertainties on the cell parameters. " \
              "Only relevant to DIALS pipeline."
  }
  space_group = None
    .type = space_group
    .help = "Provide a target space group to the indexing program"
    .short_caption = "Space group"
  unit_cell = None
    .type = unit_cell
    .help = "Provide a target unit cell to the indexing program"
    .short_caption = "Unit cell (requires the space group to be set)"
  resolution
    .short_caption = "Resolution"
  {
    keep_all_reflections = Auto
      .type = bool
      .help = "Keep all data regardless of resolution criteria"
      .short_caption = "Keep all data (default for small molecule mode)"
    d_max = None
      .type = float(value_min=0.0)
      .help = "Low resolution cutoff."
      .short_caption = "Low resolution cutoff"
    d_min = None
      .type = float(value_min=0.0)
      .help = "High resolution cutoff."
      .short_caption = "High resolution cutoff"
    include scope dials.util.resolution_analysis.phil_str
  }
  unify_setting = False
    .type = bool
    .help = "For one crystal, multiple orientations, unify U matrix"
    .short_caption = "Unify crystal orientations"
    .expert_level = 1
  trust_beam_centre = False
    .type = bool
    .help = "Whether or not to trust the beam centre in the image header. " \
            "If false, then the DIALS indexer will attempt to find a better beam " \
            "centre during indexing."
    .short_caption = "Trust beam centre"
    .expert_level = 1
  wavelength_tolerance = 0.00005
    .type = float(value_min=0.0)
    .help = "Tolerance for accepting two different wavelengths as the same wavelength."
    .short_caption = "Wavelength tolerance"
    .expert_level = 1
  read_all_image_headers = True
    .type = bool
    .short_caption = "Read all image headers"
    .expert_level = 1
  detector_distance = None
    .type = float(value_min=0.0)
    .help = "Distance between sample and detector (mm)"
    .short_caption = "Detector distance"
    .expert_level = 1
  show_template = False
    .type = bool
    .short_caption = "Show template"
    .expert_level = 1
  untrusted_rectangle_indexing = None
    .type = ints(size = 4)
    .multiple = True
    .short_caption = "Untrusted rectangle for indexing"
    .expert_level = 1
  xds_cell_deviation = 0.05, 5.0
    .type = floats(size = 2)
    .short_caption = "XDS cell deviation"
    .expert_level = 1
  xds_check_cell_deviation = False
    .type = bool
    .short_caption = "Check cell deviation in XDS IDXREF"
    .expert_level = 1
  use_brehm_diederichs = False
    .type = bool
    .help = "Use the Brehm-Diederichs algorithm to resolve an indexing " \
            "ambiguity. " \
            "See: W. Brehm and K. Diederichs, Acta Cryst. (2014). D70, 101-109.")
    .short_caption = "Brehm-Diederichs"
    .expert_level = 1
  integration
    .short_caption = "Integration"
    .expert_level = 1
  {
    profile_fitting = True
      .type = bool
      .help = "Use profile fitting not summation integration, default yes"
      .short_caption = "Use profile fitting"
    exclude_ice_regions = False
      .type = bool
      .help = "Exclude measurements from regions which are typically where " \
              "ice rings land"
      .short_caption = "Exclude ice regions"
  }
  developmental
    .expert_level = 2
  {
    continue_from_previous_job = False
      .type = bool
      .help = "If xia2.json file is present from a previous xia2 job then "
              "continue scaling from the previous integration results."
    use_dials_spotfinder = False
      .type = bool
      .help = "This feature requires the dials project to be installed, and " \
              "is not currently intended for general use. Use at your peril!"
    pointless_tolerance = 0.0
      .type = float(value_min=0.0)
      .help = "Tolerance to use in POINTLESS for comparison of data sets"
    detector_id = None
      .type = str
      .help = "Override detector serial number information"
  }
  multi_sweep_indexing = Auto
    .type = bool
    .help = "Index all sweeps together rather than combining individual results " \
            "(requires dials indexer)"
    .expert_level = 2
  multi_sweep_refinement = Auto
    .type = bool
    .help = "Refine all sweeps together, restraining unit cell parameters to their " \
            "median, rather than refining sweeps individually (requires dials " \
            "refiner).  If this is set to True, multi_sweep_indexing will also be " \
            "set to True."
    .expert_level = 2
  remove_blanks = False
    .expert_level = 2
    .type = bool
  integrate_p1 = False
    .type = bool
    .short_caption = "Integrate in P1"
    .expert_level = 1
  reintegrate_correct_lattice = True
    .type = bool
    .short_caption = "Reintegrate using a corrected lattice"
    .expert_level = 1
  lattice_rejection = True
    .type = bool
    .short_caption = "Reject lattice if constraints increase RMSD"
    .expert_level = 2
  lattice_rejection_threshold = 1.5
    .type = float
    .short_caption = "Threshold for lattice rejection"
    .expert_level = 2
  xds
    .expert_level = 1
    .short_caption = "xia2 XDS settings"
  {
    geometry_x = None
      .type = path
    geometry_y = None
      .type = path
  }
  indexer = xds xdsii dials
    .type = choice
    .expert_level = 2
  refiner = xds dials
    .type = choice
    .expert_level = 2
  integrater = xdsr xds dials
    .type = choice
    .expert_level = 2
  scaler = ccp4a xdsa dials
    .type = choice
    .expert_level = 2
  merging_statistics
    .short_caption = "Merging statistics"
    .expert_level = 1
  {
    source = aimless *cctbx
      .type = choice
      .help = "Use AIMLESS or cctbx for calculation of merging statistics"
      .short_caption = "Software to calculate merging statistics"
    n_bins = 20
      .type = int(value_min=1)
      .short_caption = "Number of bins"
    use_internal_variance = False
      .type = bool
      .help = "Use internal variance of the data in the calculation of the " \
              "merged sigmas."
      .short_caption = "Use internal variance"
    eliminate_sys_absent = False
      .type = bool
      .help = "Eliminate systematically absent reflections before computation " \
              "of merging statistics."
      .short_caption = "Eliminate systematic absences before calculation"
  }
  verbose = False
    .type = bool
    .expert_level = 1
  multiprocessing
    .short_caption = "Multiprocessing"
  {
    mode = *serial parallel
      .type = choice
      .help = "Whether to process each sweep in serial (using n processes per" \
              " sweep) or to process sweeps in parallel (using 1 process per" \
              " sweep)."
      .expert_level = 1
    nproc = Auto
      .type = int(value_min=1)
      .help = "The number of processors to use per job."
      .expert_level = 0
    njob = Auto
      .type = int(value_min=1)
      .help = "The number of sweeps to process simultaneously."
      .expert_level = 1
    type = *simple qsub
      .type = choice
      .help = "How to run the parallel processing jobs, e.g. over a cluster"
      .expert_level = 1
    qsub_command = ''
      .type = str
      .help = "The command to use to submit qsub jobs"
      .expert_level = 1
  }
  report
    .expert_level = 1
  {
    include scope xia2.Modules.Analysis.phil_scope
  }
  symmetry
    .short_caption = "symmetry"
  {
    chirality = chiral nonchiral centrosymmetric
      .type = choice
    program = *pointless dials
      .type = choice
  }
}
""",
    process_includes=True,
)

# override default resolution parameters
master_phil = master_phil.fetch(
    source=parse(
        """\
xia2.settings {
  resolution {
    isigma = None
    misigma = None
  }
}
"""
    )
)

PhilIndex = interface.index(master_phil=master_phil)

if __name__ == "__main__":
    PhilIndex.working_phil.show()
