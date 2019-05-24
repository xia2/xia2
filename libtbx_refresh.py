from __future__ import absolute_import, division, print_function

import dials.precommitbx.nagger
from xia2.XIA2Version import Version

dials.precommitbx.nagger.nag()

# the import implicitly updates the .gitversion file
print(Version)
