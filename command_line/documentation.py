import sys
import os
import math
import time
import exceptions
import traceback

# Needed to make xia2 imports work correctly
import libtbx.load_env
xia2_root_dir = libtbx.env.find_in_repositories("xia2", optional=False)
sys.path.insert(0, xia2_root_dir)
os.environ['XIA2_ROOT'] = xia2_root_dir
os.environ['XIA2CORE_ROOT'] = os.path.join(xia2_root_dir, "core")

def run():
  html_path = libtbx.env.find_in_repositories(
    "xia2/html/index.html", test=os.path.isfile)
  assert html_path is not None
  import webbrowser
  webbrowser.open_new_tab('file://' + html_path)

if __name__ == '__main__':
  run()
