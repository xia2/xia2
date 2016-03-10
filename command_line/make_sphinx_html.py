# LIBTBX_SET_DISPATCHER_NAME dev.xia2.make_sphinx_html

from __future__ import division
from libtbx import easy_run
import libtbx.load_env
import os.path as op
import shutil
import os
import sys

if (__name__ == "__main__") :
  xia2_dir = libtbx.env.find_in_repositories("xia2", optional=False)
  assert (xia2_dir is not None)
  dest_dir = op.join(xia2_dir, "html")
  if op.exists(dest_dir):
    shutil.rmtree(dest_dir)
  os.chdir(op.join(xia2_dir, "doc", "sphinx"))
  easy_run.call("make clean")
  easy_run.call("make html")
  print "Moving HTML pages to", dest_dir
  shutil.move("build/html", dest_dir)
