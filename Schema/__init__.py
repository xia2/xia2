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

    from dxtbx.imageset import ImageSetFactory
    imagesets = ImageSetFactory.from_template(
      full_template_path, check_headers=False)

    imageset_cache[full_template_path] = OrderedDict()

    for imageset in imagesets:
      scan = imageset.get_scan()
      id_image = scan.get_image_range()[0]
      imageset_cache[full_template_path][id_image] = imageset

  if id_image is not None:
    return [imageset_cache[full_template_path][id_image]]
  elif image_range is not None:
    for imageset in imageset_cache[full_template_path].values():
      scan = imageset.get_scan()
      scan_image_range = scan.get_image_range()
      if (image_range[0] >= scan_image_range[0] and
          image_range[1] <= scan_image_range[1]):
        return [imageset[
          scan_image_range[0]-image_range[0]:image_range[1]]]
  return imageset_cache[full_template_path].values()
