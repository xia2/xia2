from __future__ import absolute_import, division, print_function

def test_find_python3_violations():
  import xia2
  import pytest
  import dials.test.python3_regression as py3test
  result = py3test.find_new_python3_incompatible_code(xia2)
  if result is None:
    pytest.skip('No python3 interpreter available')
  elif result:
    pytest.fail(result)
