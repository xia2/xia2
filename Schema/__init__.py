import os
import sys

if not os.environ.has_key('XIA2_ROOT'):
  raise RuntimeError, 'XIA2_ROOT not defined'

if not os.environ['XIA2_ROOT'] in sys.path:
  sys.path.append(os.path.join(os.environ['XIA2_ROOT']))


from libtbx.containers import OrderedDict
from Handlers.Phil import PhilIndex

class _ImagesetCache(dict):
  pass


imageset_cache = _ImagesetCache()

def load_imagesets(template, directory, id_image=None, image_range=None,
                   use_cache=True, reversephi=False):
  global imageset_cache

  full_template_path = os.path.join(directory, template)
  if full_template_path not in imageset_cache or not use_cache:

    from dxtbx.datablock import DataBlockFactory
    from dxtbx.sweep_filenames import locate_files_matching_template_string

    params = PhilIndex.get_python_object()
    read_all_image_headers = params.xia2.settings.read_all_image_headers

    if read_all_image_headers:
      paths = sorted(locate_files_matching_template_string(full_template_path))
      unhandled = []
      datablocks = DataBlockFactory.from_filenames(
        paths, verbose=False, unhandled=unhandled)
      assert len(unhandled) == 0, "unhandled image files identified: %s" % \
          unhandled
      assert len(datablocks) == 1, "1 datablock expected, %d found" % \
          len(datablocks)

    else:
      from dxtbx.datablock import DataBlockTemplateImporter
      importer = DataBlockTemplateImporter([full_template_path])
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

    for imageset in imagesets:
      scan = imageset.get_scan()
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
    reference_geometry = find_relevant_reference_geometry(imageset, reference_components)
#   print "Appropriate set: ", reference_set
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
    reference_components.append({'detector': reference_detector, 'beam': reference_beam, 'file': file})

  import itertools
  for combination in itertools.combinations(reference_components, 2):
    if compare_geometries(combination[0]['detector'], combination[1]['detector']):
      from Handlers.Streams import Chatter
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
