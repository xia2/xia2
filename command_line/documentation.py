from __future__ import absolute_import, division, print_function

import os

import libtbx.load_env

def run():
  html_path = libtbx.env.find_in_repositories(
    "xia2/html/index.html", test=os.path.isfile)
  assert html_path is not None
  import webbrowser
  webbrowser.open_new_tab('file://' + html_path)

if __name__ == '__main__':
  run()
