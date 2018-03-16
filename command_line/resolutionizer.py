# LIBTBX_PRE_DISPATCHER_INCLUDE_SH export BOOST_ADAPTBX_FPE_DEFAULT=1
from __future__ import absolute_import, division

import sys

if __name__ == '__main__':
  from dials.util.Resolutionizer import run
  run(sys.argv[1:])
