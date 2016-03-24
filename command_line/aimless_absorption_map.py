# LIBTBX_SET_DISPATCHER_NAME dev.xia2.aimless_absorption_map
from __future__ import division

def main(log, png):
  from xia2.Toolkit.AimlessSurface import generate_map, evaluate_1degree, scrape_coefficients
  generate_map(evaluate_1degree(scrape_coefficients(log)), png)

if __name__ == '__main__':
  import sys
  main(sys.argv[1], sys.argv[2])
