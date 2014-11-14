# LIBTBX_SET_DISPATCHER_NAME xia2.new

import sys

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2")
sys.path.insert(0, xia2_root_dir)

from xia2.Applications import xia2

if __name__ == '__main__':
  xia2.run()
