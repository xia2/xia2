import os
from libtbx.containers import OrderedDict

class _ImagesetCache(dict):
  pass

imageset_cache = _ImagesetCache()

def load_imagesets(template, directory, id_image=None, image_range=None,
                   use_cache=True):
  global imageset_cache

  full_template_path = os.path.join(directory, template)
  if full_template_path not in imageset_cache or not use_cache:

    from dxtbx.datablock import DataBlockFactory
    from dxtbx.sweep_filenames import locate_files_matching_template_string

    from Handlers.Phil import PhilIndex
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
        assert len(imagesets[0]) == image_range[1] - image_range[0] + 1, len(imagesets[0])
  return imageset_cache[full_template_path].values()
