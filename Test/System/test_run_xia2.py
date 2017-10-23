# System testing: run xia2 and check for zero exit code

from __future__ import absolute_import, division, print_function

def test_start_xia2():
  from subprocess import Popen, PIPE

  process = Popen(["xia2"], stdout=PIPE)
  (output, err) = process.communicate()
  exit_code = process.wait()
  if (exit_code != 0):
    exit(exit_code)
