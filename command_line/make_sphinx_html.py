# LIBTBX_SET_DISPATCHER_NAME dev.xia2.make_sphinx_html

from __future__ import absolute_import, division

import os
import shutil

import libtbx.load_env
from dials.util.procrunner import run_process

if (__name__ == "__main__") :
  xia2_dir = libtbx.env.find_in_repositories("xia2", optional=False)
  assert (xia2_dir is not None)
  dest_dir = os.path.join(xia2_dir, "html")
  if os.path.exists(dest_dir):
    shutil.rmtree(dest_dir)
  os.chdir(os.path.join(xia2_dir, "doc", "sphinx"))
  result = run_process(["make", "clean"])
  assert result['exitcode'] == 0, \
      'make clean failed with exit code %d' % result['exitcode']
  result = run_process(["make", "html"])
  assert result['exitcode'] == 0, \
      'make html failed with exit code %d' % result['exitcode']
  print "Moving HTML pages to", dest_dir
  shutil.move("build/html", dest_dir)
