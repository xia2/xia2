# LIBTBX_SET_DISPATCHER_NAME xia2.setup
#
# see https://github.com/xia2/xia2/issues/172
# LIBTBX_PRE_DISPATCHER_INCLUDE_SH ulimit -n `ulimit -Hn 2>&1 |sed 's/unlimited/4096/'`

from __future__ import absolute_import, division, print_function

from xia2.Applications import xia2setup

if __name__ == "__main__":
    xia2setup.run()
