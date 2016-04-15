# LIBTBX_SET_DISPATCHER_NAME dev.xia2.aimless_absorption_map
from __future__ import division

def main(log, png):
  from xia2.Toolkit.AimlessSurface import generate_map, evaluate_1degree, scrape_coefficients
  absmap = evaluate_1degree(scrape_coefficients(log))
  assert absmap.max() - absmap.min() > 0.000001, "Cannot create absorption surface: map is too flat (min: %f, max: %f)" % (absmap.min(), absmap.max())
  generate_map(absmap, png)

if __name__ == '__main__':
  import sys
  main(sys.argv[1], sys.argv[2])
