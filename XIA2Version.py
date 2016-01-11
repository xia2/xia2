#!/usr/bin/env python
# XIA2Version.py
#   Copyright (C) 2006 CCLRC, Graeme Winter
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
#
# 6th June 2006
#
# A file containing the version number of the current xia2. Generally useful.
#

VersionNumber = "0.4.0.0"
Version = "XIA2 %s" % VersionNumber
CVSTag = "xia2-%s" % VersionNumber.replace('.', '_')
Directory = "xia2-%s" % VersionNumber

def get_git_revision():
  '''Try to obtain the current git revision number
     and store a copy in .gitversion'''
  version = None

  try:
    import libtbx.load_env
    import os
    xia2_path = libtbx.env.dist_path('xia2')
    version_file = os.path.join(xia2_path, '.gitversion')

    # 1. Try to access information in .git directory
    #    Regenerate .gitversion if possible
    if os.path.exists(os.path.join(xia2_path, '.git')):
      try:
        import subprocess
        with open(os.devnull, 'w') as devnull:
          version = subprocess.check_output(["git", "describe", "--long"], cwd=xia2_path, stderr=devnull).rstrip()
        with open(version_file, 'w') as gv:
          gv.write(version)
      except Exception:
        if version == "": version = None

    # 2. If .git directory or git executable missing, read .gitversion
    if (version is None) and os.path.exists(version_file):
      with open(version_file, 'r') as gv:
        version = gv.read().rstrip()
  except Exception:
    pass

  if version is None:
    version = 'not set'

  return version

if __name__ == '__main__':
  print 'This is XIA 2 version %s' % VersionNumber
  print 'This should be in a directory called "%s"' % Directory
  print 'And should be CVS tagged as "%s"' % CVSTag
