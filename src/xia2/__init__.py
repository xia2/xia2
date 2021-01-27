import sys

if sys.version_info.major == 2:
    sys.exit("Python 2 is no longer supported")

import pathlib

_xia2 = pathlib.Path(__file__).parents[2]

exit(
    ("=" * 80)
    + """

Your xia2 repository is still tracking 'master',
but the main xia2 branch has been renamed to 'main'.

Please go into your xia2 repository at %s and run the following commands:
  git branch -m master main
  git fetch origin
  git branch -u origin/main main

For more information please see https://github.com/xia2/xia2/issues/557
"""
    % _xia2
)
