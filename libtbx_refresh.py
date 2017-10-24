from __future__ import absolute_import, division, print_function

# implicitly update the .gitversion file
from xia2.XIA2Version import Version
print(Version)

import libtbx.pkg_utils
libtbx.pkg_utils.require('mock', '>=2.0')
libtbx.pkg_utils.require('pytest', '>=3.1')
