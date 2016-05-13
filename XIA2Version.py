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

def get_git_revision(fallback='not set'):
  '''Try to obtain the current git revision number
     and store a copy in .gitversion'''
  version = None
  try:
    import os
    xia2_path = os.path.split(os.path.realpath(__file__))[0]
    version_file = os.path.join(xia2_path, '.gitversion')

    # 1. Try to access information in .git directory
    #    Regenerate .gitversion if possible
    if os.path.exists(os.path.join(xia2_path, '.git')):
      try:
        import subprocess
        with open(os.devnull, 'w') as devnull:
          version = subprocess.check_output(["git", "describe", "--long"], cwd=xia2_path, stderr=devnull).rstrip()
          if version[0] == 'v':
            version = version[1:].replace('.0-','.')
          try:
            branch = subprocess.check_output(["git", "describe", "--contains", "--all", "HEAD"], cwd=xia2_path, stderr=devnull).rstrip()
            if branch != '' and branch != 'master' and not branch.endswith('/master'):
              version = version + '-' + branch
          except Exception:
            pass
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
    version = fallback

  return version

VersionNumber = get_git_revision("0.4.0.0")
Version = "XIA2 %s" % VersionNumber
Directory = "xia2-%s" % VersionNumber

if __name__ == '__main__':
  print 'This is XIA 2 version %s' % VersionNumber
  print 'This should be in a directory called "%s"' % Directory
