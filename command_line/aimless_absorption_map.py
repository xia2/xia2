# LIBTBX_SET_DISPATCHER_NAME dev.xia2.aimless_absorption_map
from __future__ import division

def main(log, png):
  from xia2.Toolkit.AimlessSurface import evaluate_1degree, scrape_coefficients
  evaluate_1degree(scrape_coefficients(log), png)
  return


if __name__ == '__main__':
  import sys
  main(sys.argv[1], sys.argv[2])
