# System testing: run xia2 and check for zero exit code

from __future__ import absolute_import, division, print_function

def test_start_xia2():
  import procrunner

  result = procrunner.run(['xia2'])
  assert result['exitcode'] == 0
