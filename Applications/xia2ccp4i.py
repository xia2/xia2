#!/usr/bin/env python
# xia2ccp4i.py
#   Copyright (C) (2013) STFC Rutherford Appleton Laboratory, UK.
#
#   Author: David Waterman.
#
#   This code is distributed under the BSD license, a copy of which is
#   included in the root directory of this package.
"""
xia2ccp4i.py:

A demonstration for a user friendly way to link data processing with downstream
analysis. This script finds data processed by xia2, creates a standalone CCP4
project and starts ccp4i with it.
"""

from __future__ import absolute_import, division

import datetime
import getopt
import os
import re
import shutil
import string
import subprocess
import sys

__author__ = "David Waterman"
__credits__ = "Andrey Lebedev"
__email__ = "david.waterman@stfc.ac.uk"

class ProjectMaker(object):
  """A function object to make a new CCP4 project directory"""

  _database_template = string.Template(
'''#CCP4I VERSION CCP4Interface 2.2.0
#CCP4I SCRIPT DEF CCP4_Project_Database
#CCP4I $TIME
#CCP4I USER $USER
#CCP4I PROJECT $PROJ_NAME $PROJ_DIR
NJOBS 0
''')

  _directories_template = string.Template(
'''#CCP4I VERSION CCP4Interface 2.2.0
#CCP4I SCRIPT DEF directories
#CCP4I $TIME
#CCP4I USER $USER
DEF_DIR_ALIAS,0           _text                     ""
DEF_DIR_ALIAS,1           _text                     TEMPORARY
DEF_DIR_PATH,0            _dir                      ""
DEF_DIR_PATH,1            _dir                      /tmp/$USER
LOG_DIRECTORY             _log_directory            PROJECT
N_DEF_DIRS                _positiveint1             1
N_PROJECTS                _positiveint1             1
PROJECT_ALIAS,0           _text                     ""
PROJECT_ALIAS,1           _text                     $PROJ_NAME
PROJECT_DATABASE          _dir                      ""
PROJECT_DB,0              _dir                      ""
PROJECT_DB,1              _dir                      $PROJ_DIR/CCP4_DATABASE
PROJECT_MENU              _menu                     ""
PROJECT_PATH,1            _dir                      $PROJ_DIR
PROJECT_PATH,0            _dir                      ""
''')

  _status_template = string.Template(
'''#CCP4I VERSION CCP4Interface 2.2.0
#CCP4I SCRIPT DEF status
#CCP4I $TIME
#CCP4I USER $USER
CURRENT_MODULE            _text                     automation
CURRENT_PROJECT           _default_project          $PROJ_NAME
MG_CURRENT_PROJECT        _default_project          $PROJ_NAME
''')

  _reason_for_failure = None

  def __call__(self, project_name, directory="."):
    """Test whether making a project in the specified directory is
    possible, and if so make it and return True. If not possible,
    return False and cache the reason for failure"""

    proj_dir = os.path.realpath(directory)
    db_dir = os.path.join(proj_dir, "CCP4_DATABASE")
    proj_name = project_name.strip().replace(" ", "_")

    # Does CCP4_PROJECT already exist here?
    if os.path.exists(db_dir):
      self._reason_for_failure = ("ERROR: Directory '%s' already "
                                  "contains CCP4_DATABASE") % directory
      return False

    # Is the project_name valid?
    if not re.match("[_\-a-zA-Z0-9]+$", proj_name):
      self._reason_for_failure = "ERROR: " + proj_name + \
          " is not a valid CCP4 Project name"
      return False

    # Go ahead and make CCP4_DATABASE if we have write access
    try:
      os.mkdir(db_dir)
    except OSError:
      self._reason_for_failure = ("ERROR: Problem encountered while "
          "creating CCP4_DATABASE in " + proj_dir)
      return False

    # Create strings for .def files
    mapping = {'TIME':datetime.datetime.now().strftime("DATE %d %b %Y  %T"),
               'USER':os.environ["USER"],
               'PROJ_NAME':proj_name,
               'PROJ_DIR':proj_dir}
    database_txt = self._database_template.substitute(mapping)
    directories_txt = self._directories_template.substitute(mapping)
    status_txt = self._status_template.substitute(mapping)

    # Now create files in the project directory
    try:
      database = open(os.path.join(db_dir, "database.def"), 'w')
    except OSError as err:
      self._reason_for_failure = ("ERROR: Problem encountered while "
                                  "writing database.def")
      return False

    database.write(database_txt)
    database.close()

    try:
      directories = open(os.path.join(db_dir, "directories.def"), 'w')
    except OSError as err:
      self._reason_for_failure = ("ERROR: Problem encountered while "
                                  "writing directories.def")
      return False

    directories.write(directories_txt)
    directories.close()

    try:
      status = open(os.path.join(db_dir, "status.def"), 'w')
    except OSError as err:
      self._reason_for_failure = ("ERROR: Problem encountered while "
                                  "writing status.def")
      return False

    status.write(status_txt)
    status.close()

    # All jobs done, return True
    return True

  def reason_for_failure(self):
    return self._reason_for_failure

class Xia2Info(object):
  """Check a xia2 processing directory exists and contains what is needed.
  Provide access to those things."""

  def __init__(self, xia2dir):

    self._problems = []
    self._proj_name = None
    self._data_files = []

    # check the processing directory exists
    if not os.path.exists(xia2dir):
      self._problems.append("Directory %s is not accessible" % xia2dir)
      return

    # check we can read the xia2-summary.dat file
    try:
      f = open(os.path.join(xia2dir, "xia2-summary.dat"))
      summary = f.readlines()
      f.close()
    except IOError as err:
      self._problems.append("Unable to read xia2-summary.dat "
                            "inside %s" % xia2dir)
      return

    # attempt to extract the project name
    for line in summary:
      if line.startswith("Project:"):
        self._proj_name = (line.partition("Project:")[2]).strip()

    if not self._proj_name:
      self._problems.append("Unable to find a project name in "
                            "xia2-summary.dat")
    else:
      # check the project name is sensible
      if self._proj_name.lower() in ["automatic", "default"]:
        self._problems.append("The project name '%s' read from "
                              "xia2-summary.dat is probably not "
                              "desirable" % self._proj_name)
        self._proj_name = None

    # make a list of the data files
    datadir = os.path.join(xia2dir, "DataFiles")
    if not os.path.exists(datadir):
      self._problems.append("Directory %s is not accessible" % datadir)
      return

    self._data_files = [os.path.join(datadir, e) \
                        for e in os.listdir(datadir)]

    return

  def list_problems(self):
    return self._problems

  def get_project_name(self):
    return self._proj_name

  def get_data_files(self):
    if self._data_files:
      return self._data_files
    return None

def usage(myname="xia2ccp4i.py"):
  """return a usage string"""

  msg = """%s [options]

Options:
-h, --help               show this help message and exit
-p FOO, --project=FOO    override the project name taken from xia2, and call
                         the CCP4 project FOO
-x BAR, --xia2dir=BAR    specify the location of the top-level xia2 processing
                         directory (omission implies BAR=".")

Extract project name and data from a xia2 processing run, create a standalone
ccp4i project and start ccp4i with that project.

Please note that this standalone ccp4i project will not be in the global
projects database of ccp4i. However it may be added later using the
'Directories&ProjectDir' button in ccp4i. The list of jobs performed in the
standalone project will remain intact after the import.
"""
  return msg % myname

if __name__ == '__main__':

  # Use getopt rather than argparse for python < 2.7 compatibility
  try:
    opts, args = getopt.getopt(sys.argv[1:],
                             "hp:x:",
                             ["help", "project=", "xia2dir="])
  except getopt.GetoptError as err:
    # Exit with a useful message:
    print str(err)
    sys.exit(usage())

  proj_name = None
  xia2dir = "."
  for o, a in opts:
    if o in ("-h", "--help"):
      print usage()
      sys.exit()
    elif o in ("-p", "--project"):
      proj_name = a
    elif o in ("-x", "--xia2dir"):
      xia2dir = os.path.realpath(a)

  # Check the xia2 processing output
  process_info = Xia2Info(xia2dir)

  # If proj_name has not been specified, attempt to get it from the xia2 info
  if proj_name is None:
    proj_name = process_info.get_project_name()
  if proj_name is None:
    msg = "\n".join(process_info.list_problems())
    msg += ("\nNothing has been done. To force a project name, re-run "
            "using the --project=FOO option")
    sys.exit(msg)

  # Copy the data into a new CCP4 Project directory
  proj_dir = os.path.join(xia2dir, "CCP4Project")
  try:
    os.mkdir(proj_dir)
  except OSError as err:
    msg = "Unable to create a CCP4Project directory. Does it already exist?"
    sys.exit(msg)
  try:
    for f in process_info.get_data_files():
      shutil.copy2(f, proj_dir)
  except IOError as err:
    msg = "Unable to copy data files to " + proj_dir
    sys.exit(msg)

  # Make the project, or exit with a failure message
  project_maker = ProjectMaker()
  if not project_maker(proj_name, directory=proj_dir):
    sys.exit(project_maker.reason_for_failure())

  # Now start ccp4i and exit with its call value
  db_dir = os.path.join(proj_dir, "CCP4_DATABASE")
  try:
    val = subprocess.call("ccp4i", cwd=db_dir)
    sys.exit(val)
  except OSError as err:
    print("It seems that ccp4i is not currently available. To start ccp4i "
          "with the isolated project %s, please set up the CCP4 "
          "environment and type:\n\n"
          "cd %s\n"
          "ccp4i") % (proj_name, db_dir)
