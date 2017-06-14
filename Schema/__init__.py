from __future__ import absolute_import, division

import os

from libtbx.containers import OrderedDict
from xia2.Handlers.Phil import PhilIndex

class _ImagesetCache(dict):
  pass

imageset_cache = _ImagesetCache()


def longest_common_substring(s1, s2):
  m = [[0] * (1 + len(s2)) for i in xrange(1 + len(s1))]
  longest, x_longest = 0, 0
  for x in xrange(1, 1 + len(s1)):
    for y in xrange(1, 1 + len(s2)):
      if s1[x - 1] == s2[y - 1]:
        m[x][y] = m[x - 1][y - 1] + 1
        if m[x][y] > longest:
          longest = m[x][y]
          x_longest = x
      else:
        m[x][y] = 0
  return s1[x_longest - longest: x_longest]


def load_imagesets(template, directory, id_image=None, image_range=None,
                   use_cache=True, reversephi=False):
  global imageset_cache
  from dxtbx.datablock import DataBlockFactory
  from xia2.Applications.xia2setup import known_hdf5_extensions

  full_template_path = os.path.join(directory, template)
  if full_template_path not in imageset_cache or not use_cache:

    from dxtbx.datablock import BeamComparison
    from dxtbx.datablock import DetectorComparison
    from dxtbx.datablock import GoniometerComparison

    params = PhilIndex.params.xia2.settings
    compare_beam = BeamComparison(
      wavelength_tolerance=params.input.tolerance.beam.wavelength,
      direction_tolerance=params.input.tolerance.beam.direction,
      polarization_normal_tolerance=params.input.tolerance.beam.polarization_normal,
      polarization_fraction_tolerance=params.input.tolerance.beam.polarization_fraction)
    compare_detector = DetectorComparison(
      fast_axis_tolerance=params.input.tolerance.detector.fast_axis,
      slow_axis_tolerance=params.input.tolerance.detector.slow_axis,
      origin_tolerance=params.input.tolerance.detector.origin)
    compare_goniometer = GoniometerComparison(
      rotation_axis_tolerance=params.input.tolerance.goniometer.rotation_axis,
      fixed_rotation_tolerance=params.input.tolerance.goniometer.fixed_rotation,
      setting_rotation_tolerance=params.input.tolerance.goniometer.setting_rotation)
    scan_tolerance = params.input.tolerance.scan.oscillation

    format_kwargs = {
      'dynamic_shadowing' : params.input.format.dynamic_shadowing,
      'multi_panel' : params.input.format.multi_panel,
    }

    if os.path.splitext(full_template_path)[-1] in known_hdf5_extensions:
      import glob
      g = glob.glob(os.path.join(directory, '*_master.h5'))
      master_file = None
      for p in g:
        substr = longest_common_substring(template, p)
        if substr:
          if (master_file is None or
              (len(substr) > len(longest_common_substring(template, master_file)))):
            master_file = p

      if master_file is None:
        raise RuntimeError("Can't find master file for %s" % full_template_path)

      unhandled = []
      datablocks = DataBlockFactory.from_filenames(
        [master_file], verbose=False, unhandled=unhandled,
        compare_beam=compare_beam,
        compare_detector=compare_detector,
        compare_goniometer=compare_goniometer,
        scan_tolerance=scan_tolerance,
        format_kwargs=format_kwargs)

      assert len(unhandled) == 0, "unhandled image files identified: %s" % \
          unhandled
      assert len(datablocks) == 1, "1 datablock expected, %d found" % \
          len(datablocks)

    else:

      from dxtbx.sweep_filenames import locate_files_matching_template_string

      params = PhilIndex.get_python_object()
      read_all_image_headers = params.xia2.settings.read_all_image_headers

      if read_all_image_headers:
        paths = sorted(locate_files_matching_template_string(full_template_path))
        unhandled = []
        datablocks = DataBlockFactory.from_filenames(
          paths, verbose=False, unhandled=unhandled,
          compare_beam=compare_beam,
          compare_detector=compare_detector,
          compare_goniometer=compare_goniometer,
          scan_tolerance=scan_tolerance,
          format_kwargs=format_kwargs)
        assert len(unhandled) == 0, "unhandled image files identified: %s" % \
            unhandled
        assert len(datablocks) == 1, "1 datablock expected, %d found" % \
            len(datablocks)

      else:
        from dxtbx.datablock import DataBlockTemplateImporter
        importer = DataBlockTemplateImporter(
          [full_template_path], format_kwargs=format_kwargs)
        datablocks = importer.datablocks

    imagesets = datablocks[0].extract_sweeps()
    assert len(imagesets) > 0, "no imageset found"

    imageset_cache[full_template_path] = OrderedDict()
    if reversephi:
      for imageset in imagesets:
        goniometer = imageset.get_goniometer()
        goniometer.set_rotation_axis(
          tuple((-g for g in goniometer.get_rotation_axis())))

    reference_geometry = PhilIndex.params.xia2.settings.input.reference_geometry
    if reference_geometry is not None and len(reference_geometry) > 0:
      update_with_reference_geometry(imagesets, reference_geometry)

    # Update the geometry
    params = PhilIndex.params.xia2.settings
    update_geometry = []

    from dials.command_line.dials_import import ManualGeometryUpdater
    from dials.util.options import geometry_phil_scope
    # Then add manual geometry
    work_phil = geometry_phil_scope.format(params.input)
    diff_phil = geometry_phil_scope.fetch_diff(source=work_phil)
    if diff_phil.as_str() != "":
      update_geometry.append(ManualGeometryUpdater(params.input))

    imageset_list = []
    for imageset in imagesets:
      for updater in update_geometry:
        imageset = updater(imageset)
      imageset_list.append(imageset)
    imagesets = imageset_list

    from scitbx.array_family import flex
    for imageset in imagesets:
      scan = imageset.get_scan()
      exposure_times = scan.get_exposure_times()
      epochs = scan.get_epochs()
      if exposure_times.all_eq(0) or exposure_times[0] == 0:
        exposure_times = flex.double(exposure_times.size(), 1)
        scan.set_exposure_times(exposure_times)
      elif not exposure_times.all_gt(0):
        exposure_times = flex.double(exposure_times.size(), exposure_times[0])
        scan.set_exposure_times(exposure_times)
      if epochs.size() > 1 and not epochs.all_gt(0):
        if epochs[0] == 0:
          epochs[0] = 1
        for i in range(1, epochs.size()):
          epochs[i] = epochs[i-1] + exposure_times[i-1]
        scan.set_epochs(epochs)
      _id_image = scan.get_image_range()[0]
      imageset_cache[full_template_path][_id_image] = imageset

  if id_image is not None:
    return [imageset_cache[full_template_path][id_image]]
  elif image_range is not None:
    for imageset in imageset_cache[full_template_path].values():
      scan = imageset.get_scan()
      scan_image_range = scan.get_image_range()
      if (image_range[0] >= scan_image_range[0] and
          image_range[1] <= scan_image_range[1]):
        imagesets = [imageset[
          image_range[0] - scan_image_range[0]:
          image_range[1] + 1 - scan_image_range[0]]]
        assert len(imagesets[0]) == image_range[1] - image_range[0] + 1, \
          len(imagesets[0])
        return imagesets
  return imageset_cache[full_template_path].values()

def update_with_reference_geometry(imagesets, reference_geometry_list):
  assert reference_geometry_list is not None
  assert len(reference_geometry_list) >= 1

  reference_components = load_reference_geometries(reference_geometry_list)

  for imageset in imagesets:
    reference_geometry = find_relevant_reference_geometry(imageset,
                                                          reference_components)
    imageset.set_beam(reference_geometry['beam'])
    imageset.set_detector(reference_geometry['detector'])

def load_reference_geometries(geometry_file_list):
  from dxtbx.serialize import load

  reference_components = []
  for file in geometry_file_list:
    try:
      experiments = load.experiment_list(file, check_format=False)
      assert len(experiments.detectors()) == 1
      assert len(experiments.beams()) == 1
      reference_detector = experiments.detectors()[0]
      reference_beam = experiments.beams()[0]
    except Exception, e:
      datablock = load.datablock(file)
      assert len(datablock) == 1
      imageset = datablock[0].extract_imagesets()[0]
      reference_detector = imageset.get_detector()
      reference_beam = imageset.get_beam()
    reference_components.append({'detector': reference_detector,
                                 'beam': reference_beam, 'file': file})

  import itertools
  for combination in itertools.combinations(reference_components, 2):
    if compare_geometries(combination[0]['detector'], combination[1]['detector']):
      from xia2.Handlers.Streams import Chatter
      Chatter.write('Reference geometries given in %s and %s are too similar' % (combination[0]['file'], combination[1]['file']))
      raise Exception('Reference geometries too similar')
  return reference_components

def compare_geometries(detectorA, detectorB):
  return detectorA.is_similar_to(detectorB,
             fast_axis_tolerance=0.1,
             slow_axis_tolerance=0.1,
             origin_tolerance=10)

def find_relevant_reference_geometry(imageset, geometry_list):
  for geometry in geometry_list:
    if compare_geometries(geometry['detector'], imageset.get_detector()):
      break
  else:
    raise Exception("No appropriate reference geometry found")
  return geometry
